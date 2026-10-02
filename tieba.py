import hashlib
import logging
import time
import re
import requests

logger = logging.getLogger(__name__)

SCRIPT_NAME = "百度贴吧"
LIKE_URL = "http://c.tieba.baidu.com/c/f/forum/like"
TBS_URL = "http://tieba.baidu.com/dc/common/tbs"
SIGN_URL = "http://c.tieba.baidu.com/c/c/forum/sign"
INFO_URL = "http://c.tieba.baidu.com/mg/o/profile?format=json"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.124 Safari/537.36 Edg/102.0.1245.44"
REQUEST_TIMEOUT = 5
SIGN_KEY = "tiebaclient!!!"

sensitive_dict = {
    "禁书": "禁書",
}


def exchange_sensitive_stop_words(text):
    keys = sorted(sensitive_dict.keys(), key=len, reverse=True)
    pattern = re.compile("|".join(map(re.escape, keys)))

    def _replace(match):
        return sensitive_dict[match.group(0)]

    return pattern.sub(_replace, text)


def build_message(result, reason=""):
    if result["status"]:
        contents = []

        for item in result["result"]:
            if item["status"]:
                contents.append({"content": f"{exchange_sensitive_stop_words(item['title'])}: {item['exp']} 经验"})
            else:
                contents.append({"content": f"{exchange_sensitive_stop_words(item['title'])}: {item['msg']}"})

        return {
            "title": SCRIPT_NAME,
            "message": [
                {"h4": {"content": SCRIPT_NAME}},
                {"txt": {"content": " "}},
                {"unOrderedList": {"contents": contents}},
            ],
        }

    return {
        "title": SCRIPT_NAME,
        "message": [
            {"h3": {"content": SCRIPT_NAME}},
            {"txt": {"content": reason or "执行失败"}},
        ],
    }


class Tieba:
    timeout = REQUEST_TIMEOUT

    def __init__(self, bduss):
        self.bduss = bduss
        self.headers = {
            "Host": "tieba.baidu.com",
            "User-Agent": USER_AGENT,
            "Cookie": f"BDUSS={self.bduss}",
            "Connection": "keep-alive",
        }
        self.tbs = ""
        self.name = "未知"
        # 预置展示字段的默认值，保证部分接口失败时通知仍可渲染。
        self.message = {
            "status": False,
            "result": [],
        }
        self.reason = ""

    # ------------------------------------------------------------------ #
    # 入口
    # ------------------------------------------------------------------ #
    def start(self):
        try:
            self.get_user_info()

            if self.get_tbs():
                # 循环签到
                for favorite in self.get_favorite():
                    self.client_sign(favorite["id"], favorite["name"])
                    time.sleep(0.5)

                self.message["status"] = True
                logger.info("签到结束")
            else:
                self.reason = "获取 tbs 失败"
        except requests.exceptions.Timeout:
            self.reason = "请求超时"
        except requests.exceptions.RequestException as exc:
            self.reason = str(exc)

        if self.message["status"]:
            return build_message(self.message)
        return build_message(self.message, self.reason)

    # ------------------------------------------------------------------ #
    # HTTP 封装
    # ------------------------------------------------------------------ #
    def _get(self, url, params=None):
        return requests.get(url, headers=self.headers, params=params, timeout=self.timeout).json()

    def _post(self, url, data=None):
        return requests.post(url, headers=self.headers, data=data, timeout=self.timeout).json()

    @staticmethod
    def _encode_data(data):
        """按 key 字典序拼接参数，追加签名密钥后计算 MD5 并写回 data["sign"]。"""
        s = "".join(f"{key}={data[key]}" for key in sorted(data))
        data["sign"] = hashlib.md5((s + SIGN_KEY).encode("utf-8")).hexdigest().upper()
        return data

    # ------------------------------------------------------------------ #
    # 业务接口
    # ------------------------------------------------------------------ #
    def get_user_info(self):
        try:
            res = self._get(INFO_URL)

            self.name = res["data"]["user"]["name"]
            logger.info(f"获取用户名成功, username={self.name}")
        except Exception as exc:
            logger.warning(f"获取用户信息时出错, 原因: {exc}")

    def get_tbs(self):
        try:
            res = self._get(TBS_URL)

            self.tbs = res["tbs"]
            logger.info(f"获取 tbs 成功: {self.tbs}")
            return True
        except Exception as exc:
            logger.warning(f"获取 tbs 失败: {exc}")
            return False

    def get_favorite(self):
        """获取关注的贴吧列表, 自动翻页。

        Returns:
            list: 贴吧信息列表, 例如 [{
                "id": "18692060",
                "name": "龙珠超",
                "level_id": "12",
                "level_name": "舞步融合",
                "cur_score": "8051",
            }, {...}]
        """
        data = {
            "BDUSS": self.bduss,
            "_client_type": "2",
            "_client_id": "wappc_1534235498291_488",
            "_client_version": "9.7.8.0",
            "_phone_imei": "000000000000000",
            "from": "1008621y",
            "page_no": "1",
            "page_size": "200",
            "model": "MI+5",
            "net_type": "1",
            "timestamp": str(int(time.time())),
            "vcode_tag": "11",
        }

        data = self._encode_data(data)
        forums = []
        page = 1

        while True:
            try:
                res = self._post(LIKE_URL, data)
            except Exception as exc:
                logger.warning(f"获取贴吧列表第 {page} 页失败: {exc}")
                break

            forum_list = res.get("forum_list") or {}

            # non-gconforum / gconforum 可能是列表或单个 dict
            for key in ("non-gconforum", "gconforum"):
                value = forum_list.get(key)

                if isinstance(value, list):
                    forums.extend(value)
                elif value:
                    forums.append(value)

            if res.get("has_more") != "1":
                break

            page += 1
            data.update(
                {
                    "page_no": str(page),
                    "timestamp": str(int(time.time())),
                }
            )
            data = self._encode_data(data)

        logger.info(f"获取贴吧列表成功, 共 {len(forums)} 个吧")
        return forums

    def client_sign(self, fid, kw):
        logger.info(f"开始签到贴吧 {kw}")

        data = {
            "_client_type": "2",
            "_client_version": "9.7.8.0",
            "_phone_imei": "000000000000000",
            "model": "MI+5",
            "net_type": "1",
            "BDUSS": self.bduss,
            "fid": fid,
            "kw": kw,
            "tbs": self.tbs,
            "timestamp": str(int(time.time())),
        }

        data = self._encode_data(data)

        res = self._post(SIGN_URL, data)

        user_info = res.get("user_info")

        if user_info:
            exp = int(user_info.get("sign_bonus_point") or 0)
            logger.info(f"{kw} 签到成功, 获得 {exp} 经验")
            item = {"status": True, "exp": exp, "msg": "签到成功", "title": kw}
        else:
            logger.warning(f"{kw} 签到失败: {res.get('error_msg')}")
            item = {"status": False, "exp": 0, "msg": res.get("error_msg"), "title": kw}

        self.message["result"].append(item)
