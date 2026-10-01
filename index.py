import logging

from dict2str import dict2str
from tieba import Tieba
from config import config
from push_tools import create_channel
from push_tools.errors import UnknownChannelError

logger = logging.getLogger(__name__)


def setup_logging(level=logging.INFO):
    """配置根 logger：本项目与 push_tools 的日志统一走该格式输出。"""
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_message(message, msg_type):
    rendered = str(dict2str(message, type=msg_type)).rstrip("\n")
    logger.info(f"推送内容\n{rendered}")
    return rendered


def push_one(message, push_config):
    kind = push_config.get("type")

    try:
        pusher = create_channel(kind, push_config.get("key"))
    except UnknownChannelError:
        logger.warning(f"不支持的推送类型: {kind}")
        return

    msg_type = push_config.get("msgtype") or push_config.get("template", "markdown")
    content = parse_message(message["message"], msg_type)

    options = {k: v for k, v in push_config.items() if k not in ("type", "key")}
    return pusher.send(content, title=message["title"], **options)


def push_message(message, push_config):
    if isinstance(push_config, list):
        items = push_config
    else:
        items = [push_config]

    for item in items:
        push_one(message, item)


def main():
    setup_logging()

    configs = config.get("multi", [])
    push_together = config.get("push")

    messages = []

    for conf in configs:
        obj = Tieba(conf["bduss"])

        res = obj.start()

        push = conf.get("push")

        if push is None:
            if push_together is not None:
                messages.append(res)
        else:
            push_message(res, push)

    if messages and push_together is not None:
        m = []
        for msg in messages:
            m.extend(msg["message"])

        msg = {"title": messages[0]["title"], "message": m}
        push_message(msg, push_together)


if __name__ == "__main__":
    main()
