<div align="center">
<h1>百度贴吧签到-腾讯云函数版</h1>

[![GitHub issues](https://img.shields.io/github/issues/ICE99125/tieba_checkin?color=red&style=for-the-badge)](https://github.com/ICE99125/tieba_checkin/issues)  [![GitHub forks](https://img.shields.io/github/forks/ICE99125/tieba_checkin?style=for-the-badge)](https://github.com/ICE99125/tieba_checkin/network)  [![GitHub stars](https://img.shields.io/github/stars/ICE99125/tieba_checkin?style=for-the-badge)](https://github.com/ICE99125/tieba_checkin/stargazers)  [![Python](https://img.shields.io/badge/python-3.6%2B-orange?style=for-the-badge)](https://www.python.org/)
</div>



### 步骤

1. 进入[腾讯云云函数](https://console.cloud.tencent.com/)

   [![5gX9MQ.png](https://z3.ax1x.com/2021/10/23/5gX9MQ.png)](https://imgtu.com/i/5gX9MQ)

2. 新建云函数，选择自定义创建，选择 python3.6，修改成 index.main，将代码复制粘贴进去

   [![5gOxG8.png](https://z3.ax1x.com/2021/10/23/5gOxG8.png)](https://imgtu.com/i/5gOxG8)

   [![5gOvPf.png](https://z3.ax1x.com/2021/10/23/5gOvPf.png)](https://imgtu.com/i/5gOvPf)

3. 填写环境变量值

   [![5gXSxg.png](https://z3.ax1x.com/2021/10/23/5gXSxg.png)](https://imgtu.com/i/5gXSxg)

4. 记得修改超时时间

   [![5gOzRS.png](https://z3.ax1x.com/2021/10/23/5gOzRS.png)](https://imgtu.com/i/5gOzRS)

### 所需参数

|    key    |               description                |
| :-------: | :--------------------------------------: |
|   BDUSS   |        多账户使用 `;` 分割              |
| push_type |                    -                     |
|    key    | 如果使用 server 酱或者 pushplus 的话需要 |

#### push_type

| key  | description |
| :--: | :---------: |
|  0   | 不使用推送  |
|  1   |  企业微信   |
|  2   |  server 酱  |
|  3   |  pushplus   |

#### 企业微信

|     key      |   description   |
| :----------: | :-------------: |
|   AgentId    |     应用 ID     |
|    Secret    |    应用密钥     |
|    Touser    | 不填默认 `@all` |
| EnterpriseID |     企业 ID     |
