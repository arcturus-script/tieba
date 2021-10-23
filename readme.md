<div align="center">
<h1>百度贴吧签到-腾讯云函数版</h1>

[![GitHub issues](https://img.shields.io/github/issues/ICE99125/tieba_checkin?color=red&style=for-the-badge)](https://github.com/ICE99125/tieba_checkin/issues)  [![GitHub forks](https://img.shields.io/github/forks/ICE99125/tieba_checkin?style=for-the-badge)](https://github.com/ICE99125/tieba_checkin/network)  [![GitHub stars](https://img.shields.io/github/stars/ICE99125/tieba_checkin?style=for-the-badge)](https://github.com/ICE99125/tieba_checkin/stargazers)  [![Python](https://img.shields.io/badge/python-3.6%2B-orange?style=for-the-badge)](https://www.python.org/)
</div>

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

#### 企业微信所需参数

|     key      |   description   |
| :----------: | :-------------: |
|   AgentId    |     应用 ID     |
|    Secret    |    应用密钥     |
|    Touser    | 不填默认 `@all` |
| EnterpriseID |     企业 ID     |
