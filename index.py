import os
import requests
import hashlib
import time
import push

like_url = 'http://c.tieba.baidu.com/c/f/forum/like'
tbs_url = 'http://tieba.baidu.com/dc/common/tbs'
sign_url = 'http://c.tieba.baidu.com/c/c/forum/sign'

User_Agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36 Edg/95.0.1020.30'

UTF8 = 'utf-8'

s = requests.Session()


def get_tbs(bduss):
    print('获取 tbs 开始🦉🦉')
    headers = {
        'Host': 'tieba.baidu.com',
        'User-Agent': User_Agent,
        'Cookie': 'BDUSS=%s' % bduss
    }
    try:
        tbs = s.get(url=tbs_url, headers=headers, timeout=5).json()['tbs']
    except Exception as e:
        print('获取 tbs 出错' + e)
        print('重新获取 tbs...')
        tbs = s.get(url=tbs_url, headers=headers, timeout=5).json()['tbs']
    print('获取tbs结束🔔🔔')
    return tbs


def get_favorite(bduss):
    print('获取关注贴吧开始')
    i = 1
    data = {
        'BDUSS': bduss,
        '_client_type': '2',
        '_client_id': 'wappc_1534235498291_488',
        '_client_version': '9.7.8.0',
        '_phone_imei': '000000000000000',
        'from': '1008621y',
        'page_no': '1',
        'page_size': '200',
        'model': 'MI+5',
        'net_type': '1',
        'timestamp': str(int(time.time())),
        'vcode_tag': '11',
    }
    data = encodeData(data)
    try:
        res = s.post(url=like_url, data=data, timeout=5).json()

        if 'forum_list' not in res:
            return {'gconforum': [], 'non-gconforum': []}

        if 'non-gconforum' not in res['forum_list']:
            res['forum_list']['non-gconforum'] = []

        if 'gconforum' not in res['forum_list']:
            res['forum_list']['gconforum'] = []

        while 'has_more' in res and res['has_more'] == '1':
            # 下一页
            i = i + 1
            data.update({
                'page_no': str(i),
                'timestamp': str(int(time.time()))
            })
            data = encodeData(data)
            try:
                rep = s.post(url=like_url, data=data, timeout=5).json()

                if 'forum_list' not in rep:
                    continue
                if 'non-gconforum' in rep['forum_list']:
                    res['forum_list']['non-gconforum'].append(
                        rep['forum_list']['non-gconforum'])
                if 'gconforum' in res['forum_list']:
                    res['forum_list']['gconforum'].append(
                        rep['forum_list']['gconforum'])
            except Exception as e:
                print('获取关注的贴吧出错' + e)
                continue

        t = []
        for i in res['forum_list']['non-gconforum']:
            if isinstance(i, list):
                for j in i:
                    if isinstance(j, list):
                        for k in j:
                            t.append(k)
                    else:
                        t.append(j)
            else:
                t.append(i)

        for i in res['forum_list']['gconforum']:
            if isinstance(i, list):
                for j in i:
                    if isinstance(j, list):
                        for k in j:
                            t.append(k)
                    else:
                        t.append(j)
            else:
                t.append(i)
        print('获取关注的贴吧结束')
        return t
    except Exception as e:
        print('获取关注的贴吧出错' + e)
        return []


def encodeData(data):
    s = ''
    sign_key = 'tiebaclient!!!'
    keys = data.keys()
    for i in sorted(keys):
        s += '%s=%s' % (i, data[i])
    sign = hashlib.md5((s + sign_key).encode('utf-8')).hexdigest().upper()
    data['sign'] = str(sign)
    return data


def client_sign(bduss, tbs, fid, kw):
    print('开始签到贴吧:%s' % kw)
    data = {
        '_client_type': '2',
        '_client_version': '9.7.8.0',
        '_phone_imei': '000000000000000',
        'model': 'MI+5',
        'net_type': '1',
    }
    data.update({
        'BDUSS': bduss,
        'fid': fid,
        'kw': kw,
        'tbs': tbs,
        'timestamp': str(int(time.time()))
    })
    data = encodeData(data)
    res = s.post(url=sign_url, data=data, timeout=5).json()
    if 'error_msg' in res:
        print(kw + '吧签到情况：' + res['error_msg'])
        return {'status': False, 'exp': 0, 'msg': '签到过了'}
    else:
        exp = res['user_info'].get('sign_bonus_point')
        return {'status': True, 'exp': int(exp), 'msg': '签到成功'}


def start():
    b = os.environ['BDUSS'].split(',')
    push_type = os.getenv('push_type', '2')
    print('开始签到🐤🐤')
    name_list = []
    sign_list = []
    for i in b:
        username = getUserInfo(i)
        name_list.append(username)  # 保存用户名
        tbs = get_tbs(i)  # 获取用户 tbs
        favorites = get_favorite(i)  # 获取用户关注的贴吧
        sign_result = {}  # 存放签到结果
        content = ''  # 存放签到结果
        for index, j in enumerate(favorites):
            # 循环签到
            res = client_sign(i, tbs, j['id'], j['name'])
            content = content + '%s：+%d经验\n' % (j['name'], res['exp'])
            sign_result.update({
                index: {
                    'title': j['name'],
                    'exp': res['exp'],
                    'msg': res['msg']
                }
            })
        if push_type == '1':
            # 企业微信推送
            AgentId = os.getenv('AgentId')  # 应用 ID
            Secret = os.getenv('Secret')  # 应用密钥
            EnterpriseID = os.getenv('EnterpriseID')  # 企业 ID
            Touser = os.getenv('Touser', '@all')  # 用户 ID
            p = push.qiye_wechat(AgentId, Secret, EnterpriseID, Touser)
            p.push_text_message('百度贴吧', content, username)
        sign_list.append(sign_result)
    print('签到结束😸😸')

    if push_type != '0':
        key = os.getenv('key')
        content = ''
        for index, i in enumerate(sign_list):
            content = content + '## %s\n' % name_list[index]
            content = content + ('|贴吧|经验|签到结果|\n' '|:----:|:----:|:----:|\n')
            for j in i.values():
                content = content + '|%s|%d|%s|\n' % (j['title'], j['exp'],
                                                      j['msg'])

        if push_type == '2':
            p = push.server(key)
            p.push_message('百度贴吧', content)
        elif push_type == '3':
            p = push.pushplus(key)
            p.push_message('百度贴吧', content)


def getUserInfo(bduss):
    url = 'https://tieba.baidu.com/mg/o/profile?format=json'
    headers = {
        'Host': 'tieba.baidu.com',
        'User-Agent': User_Agent,
        'Cookie': 'BDUSS=%s' % bduss
    }
    rep = s.get(url=url, headers=headers).json()
    return rep['data']['user']['name']


def main(*arg):
    return start()


if __name__ == '__main__':
    main()
