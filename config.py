push = {
    "type": "pushplus",
    "key": "xxx",
}


config = {
    "multi": [
        {
            "bduss": "xxx",
            "push": push,
        },
        {
            "bduss": "xxx",
            # "push": [
            #     # 以数组的形式填写, 则会向多个服务推送消息
            #     {
            #         "type": "pushplus",
            #         "key": "xxx",
            #     },
            #     {
            #         "type": "workWechat",
            #         "key": {
            #             "agentid": 1000002,
            #             "corpSecret": "xxx",
            #             "corpid": "xxx",
            #         },
            #     },
            # ],
        },
    ],
    # "push": {
    #     # 合并发送消息, 只合并未单独配置 push 的账号
    #     "type": "pushplus",
    #     "key": "xxx",
    # },
}
