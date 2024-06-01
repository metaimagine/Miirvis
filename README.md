# Miirvis

**Miirvis米维斯**，将大模型能力整合进小米智能音箱中，实现类似于Jarvis的功能。

## 初衷

朋友转发了[mi-gpt](https://github.com/idootop/mi-gpt)项目，了解后发现自己家里就有个小米音箱，于是想着跑着玩玩。但是发现项目启动搞了半天，一气之下就想自己用python写了。

在Github上找到的[MiService](https://github.com/Yonsm/MiService)和[xiaogpt](https://github.com/yihong0618/xiaogpt)，前者是比较全的小米音箱的接入服务，后者是魔改前者后接入了GPT、多种TTS、Agent(还不太算)。

本项目主要是做**音箱** + **Agent**，在音箱交互上还是用[MiService](https://github.com/Yonsm/MiService)，参考大佬的[xiaogpt](https://github.com/yihong0618/xiaogpt)消息处理方式，将Agent整合进去。


## 使用

#### 1. 安装依赖
```shell
$ pip install -r requirements.txt
```
#### 2. 配置信息
```shell
$ cp .env.example .env
```
在.env上配置自己的信息
```
# LLM config
API_KEY=**************************  # openai的key (或是能用openai库的模型服务)
MODEL=deepseek-chat                 # 模型名称
BASE_URL=https://api.deepseek.com   # 模型服务请求地址

# Mi config
MI_USER=123456789                   # 小米账号（米家APP上的账号）
MI_PASS=********                    # 小米密码（米家APP上的密码）
MI_DID=0123456789                   # 小米音箱设备ID（使用cli.py查看）
DEVICE_TYPE=X08A                    # 小米音箱型号（音箱的贴纸上有写）
```
#### 3. 启动服务
```shell
$ python run.py
```
## 感谢大佬
- [xiaogpt](https://github.com/yihong0618/xiaogpt) : Python实现的小米音箱接入GPT，还适配了多种tts，非常棒的项目
- [mi-gpt](https://github.com/idootop/mi-gpt) : Typescript实现的小米音箱接入GPT(我的入坑项目hhh)
- [MiService](https://github.com/Yonsm/MiService) : Python实现的小米音箱接入服务，我看了一圈大部分做python的魔改小米音箱小应用都用的这个库，感谢大佬的开源!

## 参考文档
[Mi Speaker Spec](https://home.miot-spec.com/spec)

## 大坑记录

#### 主动停止小爱回复
- 项目中stop(pause)功能并不能终止小爱的回复，只能终止播放音乐或是播客内容。所以，你要打断小爱只能**主动wake up**或是**主动tts说话**（暂时我只成功过这两种）。

#### device_id 和 did
- 这俩id完全不同，device_id是设备硬件id唯一标识，did是设备id。项目中miioservice的ubus和部分查询接口用的是device_id，miiocommand的接口中用的是did。

#### 小米IoT官网的云对云服务文档无法查看 (2024/05/31)
- 一直不支持访问，导致开发过程中spec一些参数不知道咋传到服务那边，因为可能MiService那套有些地方leg了，我这边一直调用不成功。有小伙伴有文档的话，麻烦分享到issue一下，感谢。

## TODO List

- [√] Add the Mi common service.
- [√] Add GPT in the Mi Video Box.
- [×] Add the base agent module.
- [×] Add multi tts.