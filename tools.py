def handler(fn):
    def inner(*args, **kwargs):
        res = fn(*args, **kwargs)

        table = [("贴吧", "经验", "结果")]

        for i in res["result"]:
            table.append((i["title"], i["exp"], i["msg"]))

        return [
            {
                "h4": {
                    "content": f"用户名: {res['account']}",
                },
                "table": {
                    "contents": table,
                },
            }
        ]

    return inner
