"""Find which line of a Qmsg message triggers a content violation.

Background
----------
Qmsg accepts every request synchronously (``success: true`` + message id),
but the real moderation result is reported *asynchronously*. Polling
``/v3/msg/status/{key}`` returns one of:

    0 = pending, 1 = sent, 2 = **violation**, -1 = failed

So "it was rejected for violation" can only be confirmed by polling the
status until it leaves the pending state.

What this script does
---------------------
1. ``send-full``  - send the whole message once to reproduce the violation.
2. ``bisect`` (default) - repeatedly send shrinking subsets and locate the
   offending line(s) with a binary search:

   * send the whole remaining set; if it violates, binary-search its
     prefixes for the first prefix that violates -> that prefix's last line
     is a culprit;
   * remove that line and repeat, until the remaining set passes;
   * finally send every culprit line alone to double-check it.

   With ~75 lines a single culprit needs about 8-12 real pushes
   (~45-70 seconds at the documented 5s/key rate limit).
3. ``scan`` - send every single line individually (slow: ~lines x 5s) and
   print the verdict of each; use it as a definitive fallback when the
   moderation result is flaky or multiple lines interact.

All parameters are HARD-CODED in the ``CONFIG`` block below - just edit
those constants and run ``python test_qmsg_violation.py`` (no command-line
arguments). The API key can be filled into ``QMSG_KEY`` directly; when left
empty it falls back to ``QMSG_KEY`` in ``example.py`` in this directory.

Every probe is a REAL push delivered to the bound QQ account (or group);
set ``DRY_RUN = True`` to preview the parsed message without any network
call. Typical workflow::

    1. DRY_RUN = True        -> run once, check line parsing and length
    2. MODE = "send-full"    -> run, confirm the whole message really violates
    3. MODE = "bisect"       -> run, locate the offending line(s)
    4. MODE = "scan"         -> only if bisect is inconclusive (flaky audit)
"""

from __future__ import annotations

import time
from typing import List, Optional, Sequence, Tuple

from push_tools import Qmsg
from push_tools.channels.qmsg import (
    STATUS_FAILED,
    STATUS_SENT,
    STATUS_VIOLATION,
)

# ====================================================================== #
# CONFIG - all run parameters are hard-coded here. Edit and run the file.
# ====================================================================== #
# "send-full": reproduce with the whole message (1 push)
# "bisect":    binary-search the offending line(s) (~10 pushes per culprit)
# "scan":      send every line one by one (77 pushes, slow but definitive)
MODE = "bisect"

# Qmsg API key. Fill in directly, or leave "" to reuse QMSG_KEY from
# example.py in this directory.
QMSG_KEY = ""

# Bound QQ group number as a string; "" pushes to the bound QQ single chat.
QMSG_GROUP = ""

# Preview line parsing / length without sending anything.
DRY_RUN = False

# Ask for y/N on the console before the first real push.
CONFIRM_BEFORE_SEND = True

# Minimum seconds between two submissions (documented limit: 5 s/key).
SUBMIT_INTERVAL = 5.5
# Seconds to wait for an async moderation verdict to leave "pending".
POLL_TIMEOUT = 40.0
POLL_INTERVAL = 2.0

# Append "[probe N]" to each probe so repeated pushes are never identical
# (also lets you correlate debug pushes in QQ).
USE_MARKER = True

# ---------------------------------------------------------------------- #
# The exact message that was reported as violating. Rebuilt from the forum
# names plus the fixed sign-in suffix; lines are joined with "\n" (blank
# separator lines in the original chat rendering carry no content and are
# irrelevant to the moderation check).
# ---------------------------------------------------------------------- #

LINE_SUFFIX = "亲，你之前已经签过了"

FORUM_NAMES = [
    "魔法禁书目录",
]


def build_lines() -> List[str]:
    """Return every non-empty line of the reproduced message in order."""

    return [f"- {name}: {LINE_SUFFIX}" for name in FORUM_NAMES]


def build_message(lines: Sequence[str], probe_no: Optional[int] = None) -> str:
    """Join selected lines; append a unique marker for real probes.

    The marker (``[probe N]``) keeps consecutive probes from being byte-for-byte
    identical so no client/server de-duplication can skew the result, and
    lets the user correlate the debug pushes arriving in QQ.
    """

    text = "\n".join(lines)
    if probe_no is not None:
        text += f"\n[probe {probe_no}]"
    return text


# Verdict constants returned by QmsgProber.judge().
VERDICT_VIOLATION = "violation"
VERDICT_SENT = "sent"
VERDICT_UNKNOWN = "unknown"

_STATUS_TO_VERDICT = {
    STATUS_SENT: VERDICT_SENT,
    STATUS_VIOLATION: VERDICT_VIOLATION,
    STATUS_FAILED: VERDICT_UNKNOWN,  # delivery failure != moderation result
}


class QmsgProber:
    """Submit probe messages and poll them until the moderation verdict is in."""

    def __init__(
        self,
        qmsg: Qmsg,
        group: Optional[str] = None,
        submit_interval: float = 5.5,
        poll_timeout: float = 40.0,
        poll_interval: float = 2.0,
        use_marker: bool = True,
    ):
        self.qmsg = qmsg
        self.group = group
        # Minimum seconds between two submissions (documented limit: 5s/key).
        self.submit_interval = submit_interval
        # How long to wait for an async status to leave "pending".
        self.poll_timeout = poll_timeout
        self.poll_interval = poll_interval
        self.use_marker = use_marker
        self._last_submit_at = 0.0
        self.probe_count = 0

    def _wait_throttle(self) -> None:
        """Sleep until the per-key submission rate limit allows another send."""

        elapsed = time.monotonic() - self._last_submit_at
        if self._last_submit_at and elapsed < self.submit_interval:
            time.sleep(self.submit_interval - elapsed)

    def _submit_once(self, text: str) -> Tuple[str, Optional[object]]:
        """Submit one message and poll its status once (no retry, no throttle).

        Returns a ``(verdict, status)`` tuple where verdict is one of
        ``sent`` / ``violation`` / ``unknown``; ``unknown`` covers submit
        failure, delivery failure and a status stuck in pending.
        """

        options = {"group": self.group} if self.group else {}
        result = self.qmsg.send(text, **options)
        if result is None:
            print("    submit failed (check the logged error / rate limit)")
            return VERDICT_UNKNOWN, None

        msg_id = result.raw.get("data")
        deadline = time.monotonic() + self.poll_timeout
        while time.monotonic() < deadline:
            status = self.qmsg.query_status(msg_id)
            if status is not None and status.code != 0:
                return _STATUS_TO_VERDICT.get(status.code, VERDICT_UNKNOWN), status
            time.sleep(self.poll_interval)
        print(f"    status of msg {msg_id} stayed pending for {self.poll_timeout:.0f}s")
        return VERDICT_UNKNOWN, None

    def judge(self, lines: Sequence[str], tag: str = "", retries: int = 1) -> str:
        """Submit a subset of lines, retrying once on an inconclusive result.

        Prints one progress line per real push and returns the final verdict.
        """

        self.probe_count += 1
        probe_no = self.probe_count if self.use_marker else None
        text = build_message(lines, probe_no)

        for attempt in range(retries + 1):
            self._wait_throttle()
            started = time.monotonic()
            verdict, _ = self._submit_once(text)
            self._last_submit_at = started
            suffix = f" (retry {attempt})" if attempt else ""
            print(f"[probe {self.probe_count}]{suffix} {tag} " f"-> {verdict.upper()}")
            if verdict in (VERDICT_VIOLATION, VERDICT_SENT):
                return verdict
            time.sleep(self.submit_interval)
        return VERDICT_UNKNOWN

    def violates(self, lines: Sequence[str], tag: str = "") -> bool:
        """Return True only when the subset is confirmed violating."""

        return self.judge(lines, tag) == VERDICT_VIOLATION

    # ------------------------------------------------------------------ #
    # Search strategies
    # ------------------------------------------------------------------ #
    def locate_all(self, lines: Sequence[str]) -> List[str]:
        """Iteratively binary-search every line required for a violation.

        Each round: if the remaining set violates, binary-search its
        prefixes for the smallest violating prefix; its last line is the
        next culprit. Culprits are removed until the remainder passes.
        """

        remaining = list(lines)
        culprits: List[str] = []

        while remaining and self.violates(remaining, f"full set of {len(remaining)} line(s)"):
            # Smallest k (1..len) for which the prefix remaining[:k] violates.
            lo, hi = 1, len(remaining)
            while lo < hi:
                mid = (lo + hi) // 2
                if self.violates(remaining[:mid], f"prefix {mid}/{len(remaining)}"):
                    hi = mid
                else:
                    lo = mid + 1
            culprit = remaining[lo - 1]
            culprits.append(culprit)
            print(f"  >> culprit #{len(culprits)}: {culprit!r}")
            remaining.pop(lo - 1)

        # Individual double-check: each culprit must violate on its own.
        confirmed: List[str] = []
        for culprit in culprits:
            if self.violates([culprit], "single-line verification"):
                confirmed.append(culprit)
            else:
                print(f"  !! {culprit!r} passes alone - it only violates in " f"combination with other content")
        return confirmed

    def scan(self, lines: Sequence[str]) -> List[Tuple[int, str, str]]:
        """Send every line individually; return ``(index, line, verdict)``."""

        report: List[Tuple[int, str, str]] = []
        for index, line in enumerate(lines, start=1):
            verdict = self.judge([line], f"line {index}/{len(lines)}")
            report.append((index, line, verdict))
        return report


def resolve_key() -> Optional[str]:
    """Return the hard-coded key, falling back to ``QMSG_KEY`` in example.py."""

    if QMSG_KEY:
        return QMSG_KEY
    try:
        import example  # type: ignore

        return getattr(example, "QMSG_KEY", "") or None
    except Exception:
        return None


def resolve_group() -> Optional[str]:
    """Return the hard-coded bound group, falling back to example.py."""

    if QMSG_GROUP:
        return QMSG_GROUP
    try:
        import example  # type: ignore

        return getattr(example, "QMSG_GROUP", "") or None
    except Exception:
        return None


def confirm(prompt: str) -> bool:
    try:
        return input(prompt).strip().lower() in ("y", "yes")
    except EOFError:
        return False


def print_config_summary(lines: List[str], key: Optional[str], group: Optional[str]) -> None:
    """Print the hard-coded configuration actually in effect."""

    full_text = build_message(lines)
    print("===== run configuration (hard-coded CONFIG block) =====")
    print(f"  MODE              : {MODE}")
    print(f"  QMSG_KEY          : {(key[:4] + '...') if key else '(none!)'}")
    print(f"  QMSG_GROUP        : {group or '(single chat)'}")
    print(f"  DRY_RUN           : {DRY_RUN}")
    print(f"  SUBMIT_INTERVAL   : {SUBMIT_INTERVAL}s")
    print(f"  POLL_TIMEOUT      : {POLL_TIMEOUT}s")
    print(f"  USE_MARKER        : {USE_MARKER}")
    print(f"  message size      : {len(full_text)} chars, " f"{len(full_text.encode('utf-8'))} UTF-8 bytes (cap: 1800 chars)")
    print("=======================================================")


def print_dry_run(lines: List[str]) -> None:
    full_text = build_message(lines)
    print(f"Parsed {len(lines)} non-empty lines:")
    for index, line in enumerate(lines, start=1):
        print(f"  {index:3d}. {line}")
    print()
    print(f"Full message: {len(full_text)} chars, " f"{len(full_text.encode('utf-8'))} UTF-8 bytes " f"(Qmsg client cap: 1800 chars)")
    if MODE == "bisect":
        print("Mode: bisect - about 8-12 real pushes for one culprit " "(~50-70s), more if multiple culprits exist.")
    elif MODE == "scan":
        print(f"Mode: scan - exactly {len(lines)} real pushes " f"(~{len(lines) * SUBMIT_INTERVAL:.0f}s).")
    else:
        print("Mode: send-full - exactly 1 real push.")
    print("Dry run only; no request was sent.")


def main() -> int:
    lines = build_lines()
    key = resolve_key()
    group = resolve_group()
    print_config_summary(lines, key, group)

    if DRY_RUN:
        print_dry_run(lines)
        return 0

    if MODE not in ("bisect", "scan", "send-full"):
        print(f"ERROR: MODE must be 'bisect', 'scan' or 'send-full', got {MODE!r}")
        return 2
    if not key:
        print("ERROR: no Qmsg API key. Fill QMSG_KEY in the CONFIG block " "(or in example.py).")
        return 2
    if len(build_message(lines)) > Qmsg.max_message_length and MODE == "send-full":
        print(f"ERROR: full message exceeds {Qmsg.max_message_length} chars; " "the client refuses to send it. Use MODE='bisect'/'scan'.")
        return 2

    if CONFIRM_BEFORE_SEND:
        target = f"group {group}" if group else "the bound QQ account"
        if not confirm(f"MODE='{MODE}' sends REAL Qmsg pushes to {target}. " "Continue? [y/N] "):
            print("Aborted.")
            return 1

    prober = QmsgProber(
        Qmsg(key),
        group=group,
        submit_interval=SUBMIT_INTERVAL,
        poll_timeout=POLL_TIMEOUT,
        poll_interval=POLL_INTERVAL,
        use_marker=USE_MARKER,
    )

    if MODE == "send-full":
        verdict = prober.judge(lines, "original full message")
        print(f"\nFull message verdict: {verdict.upper()}")
        return 0 if verdict == VERDICT_VIOLATION else 1

    if MODE == "scan":
        report = prober.scan(lines)
        violating = [item for item in report if item[2] == VERDICT_VIOLATION]
        unknown = [item for item in report if item[2] == VERDICT_UNKNOWN]
        print("\n===== scan report =====")
        for index, line, verdict in report:
            if verdict != VERDICT_SENT:
                print(f"  line {index}: {verdict.upper():9s} {line}")
        print(f"\nViolating line(s): {len(violating)}, inconclusive: " f"{len(unknown)}, total pushes: {prober.probe_count}")
        return 0 if violating else 1

    # bisect
    culprits = prober.locate_all(lines)
    print("\n===== bisect report =====")
    if culprits:
        for culprit in culprits:
            index = lines.index(culprit) + 1
            print(f"  line {index}: {culprit}")
    else:
        print("  No violating line reproduced (moderation may be flaky; " "re-run or set MODE='scan').")
    print(f"Total pushes: {prober.probe_count}")
    return 0 if culprits else 1


if __name__ == "__main__":
    # Parameters come exclusively from the CONFIG block at the top.
    raise SystemExit(main())
