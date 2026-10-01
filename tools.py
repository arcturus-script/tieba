__script_name__ = "百度贴吧"


def handler(fn):
    def inner(*args, **kwargs):
        res = fn(*args, **kwargs)

        msg = {
            "title": __script_name__,
            "message": [
                {"h4": {"content": __script_name__}},
                {"txt": {"content": " "}},
                {"unOrderedList": {"contents": []}},
            ],
        }

        result = []

        for i in res["result"]:
            if i["status"]:
                result.append({"content": f"**{i['title']}: ** {i['exp']} 经验"})
            else:
                result.append({"content": f"**{i['title']}: ** {i['msg']}"})

        msg["message"][2]["unOrderedList"]["contents"].extend(result)

        return msg

    return inner
