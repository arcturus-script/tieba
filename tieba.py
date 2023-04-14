from tools import handler
import requests as req
import hashlib
import time

LIKE_URL = "http://c.tieba.baidu.com/c/f/forum/like"

TBS_URL = "http://tieba.baidu.com/dc/common/tbs"

SIGN_URL = "http://c.tieba.baidu.com/c/c/forum/sign"

INFO_URL = "http://c.tieba.baidu.com/mg/o/profile?format=json"


def encodeData(data):
    s = ""
    sign_key = "tiebaclient!!!"
    keys = data.keys()

    for i in sorted(keys):
        s += f"{i}={data[i]}"

    sign = hashlib.md5((s + sign_key).encode("utf-8")).hexdigest().upper()

    data["sign"] = str(sign)

    return data


class Tieba:
    def __init__(self, **config) -> None:
        self.bduss = config.get("bduss")

        self.headers = {
            "Host": "tieba.baidu.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.124 Safari/537.36 Edg/102.0.1245.44",
            "Cookie": f"BDUSS={self.bduss}",
            "Connection": "keep-alive",
        }

    # 获取用户名
    def get_user_info(self) -> str:
        try:
            rep = req.get(url=INFO_URL, headers=self.headers).json()

            self.name = rep["data"]["user"]["name"]

            print(f"获取用户名成功, username={self.name}")

        except Exception as ex:
            print(f"获取用户信息时出错, 原因: {ex}")

            self.name = "Unkown"

    # 获取 tbs
    def get_tbs(self):
        print("[start] tbs")

        try:
            res = req.get(url=TBS_URL, headers=self.headers, timeout=5).json()

            print(f"[success] tbs is {res['tbs']}")

            self.tbs = res["tbs"]

            return True
        except Exception as ex:
            print(f"[failed] tbs --> {ex}")

    def get_favorite(self):
        """[summary] 获取关注的贴吧列表

        Returns:
            [list]: 贴吧列表, 例如 [{
                "id": "18692060",
                "name": "龙珠超",
                "favo_type": "0",
                "level_id": "12",
                "level_name": "舞步融合",
                "cur_score": "8051",
                "levelup_score": "10000",
                "avatar": "xxxx",
                "slogan": "本吧不欢迎任何黑吹",
            }, {...}]
        """
        print("[start] 贴吧列表")

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

        data = encodeData(data)
        i = 1

        try:
            res = req.post(url=LIKE_URL, data=data, timeout=5).json()

            tieba_list = []  # 暂时存放贴吧信息的列表

            if "forum_list" not in res:
                return tieba_list

            if "non-gconforum" in res["forum_list"]:
                tieba_list.append(res["forum_list"]["non-gconforum"])

            if "gconforum" in res["forum_list"]:
                tieba_list.append(res["forum_list"]["gconforum"])

            while res.get("has_more") == "1":
                # 下一页
                i += 1

                data.update(
                    {
                        "page_no": str(i),
                        "timestamp": str(int(time.time())),
                    }
                )

                data = encodeData(data)

                try:
                    res = req.post(url=LIKE_URL, data=data, timeout=5).json()

                    if "forum_list" not in res:
                        continue

                    if "non-gconforum" in res["forum_list"]:
                        tieba_list.append(res["forum_list"]["non-gconforum"])

                    if "gconforum" in res["forum_list"]:
                        tieba_list.append(res["forum_list"]["gconforum"])

                except Exception as ex:
                    print(f"[failed] 贴吧列表 --> {ex}")
                    continue

            t = []

            for item in tieba_list:
                if isinstance(item, list):
                    t.extend(item)
                else:
                    t.append(item)

            print("[success] 贴吧列表")

            return t
        except Exception as ex:
            print(f"[failed] 贴吧列表 --> {ex}")

            return []

    def client_sign(self, fid, kw):
        print(f"[start] 签到贴吧 {kw}")

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

        data = encodeData(data)

        res = req.post(url=SIGN_URL, data=data, timeout=5).json()

        if res.get("error_code") == "160002":
            print(f"[success] {kw} {res['error_msg']}")

            return {
                "status": False,
                "exp": 0,
                "msg": "签到过了",
                "title": kw,
            }
        elif res.get("error_code") == "340006":
            return {
                "status": False,
                "exp": 0,
                "msg": "无法签到",
                "title": kw,
            }
        elif res.get("error_code") == "340011":
            return {
                "status": False,
                "exp": 0,
                "msg": "签到太快",
                "title": kw,
            }
        else:
            exp = res["user_info"].get("sign_bonus_point")

            print(f"[success] {kw} {exp}经验")

            return {
                "status": True,
                "exp": int(exp),
                "msg": "签到成功",
                "title": kw,
            }

    @handler
    def start(self) -> list:
        sign_list = []

        self.get_user_info()

        if self.get_tbs():  # 获取 tbs
            favorites = self.get_favorite()  # 获取关注的贴吧

            for favorite in favorites:
                # 循环签到
                res = self.client_sign(favorite["id"], favorite["name"])
                sign_list.append(res)

                time.sleep(0.5)

            print("[success] 签到结束")

        return {
            "account": self.name,
            "result": sign_list,
        }
