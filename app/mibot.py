#!/usr/bin/env python3
import asyncio
import json
import os
import random
import re
from http.cookies import SimpleCookie
from pathlib import Path
import threading
import time
from aiohttp import ClientSession
import logging
from requests.utils import cookiejar_from_dict

from .instruct import MI_SPEAK_INSTRUCT
from .miservice.miiocommand import miio_command
from .miservice.miioservice import MiIOService
from .miservice.minaservice import MiNAService
from .miservice.miaccount import MiAccount
from .llm.openai_bot import OpenaiBot
from .utils import printer, sentence_tools

logger = logging.getLogger(__name__)
LATEST_ASK_API = "https://userprofile.mina.mi.com/device_profile/v2/conversation?source=dialogu&hardware={hardware}&timestamp={timestamp}&limit=2"
COOKIE_TEMPLATE = "deviceId={device_id}; serviceToken={service_token}; userId={user_id}"

HARDWARE_COMMAND_DICT = {
    "LX06": "5-1",  # 小爱音箱Pro（黑色）
    "L05B": "5-3",  # 小爱音箱Play
    "S12A": "5-1",  # 小爱音箱
    "LX01": "5-1",  # 小爱音箱mini
    "L06A": "5-1",  # 小爱音箱
    "LX04": "5-1",  # 小爱触屏音箱
    "L05C": "5-3",  # 小爱音箱Play增强版
    "L17A": "7-3",  # 小爱音箱Sound Pro
    "X08E": "7-3",  # 红米小爱触屏音箱Pro
    "LX05A": "5-1",  # 小爱音箱遥控版（黑色）
    "LX5A": "5-1",  # 小爱音箱遥控版（黑色）
    "X08A": "5",  # 小爱音箱Pro8
    # add more here
}


def parse_cookie_string(cookie_string):
    cookie = SimpleCookie()
    cookie.load(cookie_string)
    cookies_dict = {}
    cookiejar = None
    for k, m in cookie.items():
        cookies_dict[k] = m.value
        cookiejar = cookiejar_from_dict(cookies_dict, cookiejar=None, overwrite=True)
    return cookiejar


def check_string_in_prefix_list(string, prefixs: list):
    if any([string.startswith(prefix) for prefix in prefixs]):
        return True
    return False


class MiBot:
    def __init__(
            self,
            mi_account_info,
            hardware,
            llm_options,
            use_command=True
    ):
        self.mi_account_info = mi_account_info
        self.mi_token_home = os.path.join(Path.home(), "." + mi_account_info["mi_user"] + ".mi.token")
        self.hardware = hardware
        self.llm_options = llm_options
        self.cookie_string = ""
        self.last_ts = 0  # timestamp last call mi speaker
        self.session = None
        self.chatbot = None  # a little slow to init we move it after xiaomi init
        self.user_id = ""
        self.device_id = ""
        self.service_token = ""
        self.cookie = ""
        self.use_command = use_command
        self.tts_command = HARDWARE_COMMAND_DICT.get(hardware, "5-1")
        self.conversation_id = None
        # about mi service
        self.mi_account = None
        self.mina_service = None
        self.miio_service = None

    async def init_all_data(self):
        await self._init_mi()
        await self._init_data_hardware()
        self._init_cookie()
        await self._init_first_data()
        self._init_chatbot()

    async def _init_mi(self):
        self.mi_account = MiAccount(
            self.session,
            self.mi_account_info["mi_user"],
            self.mi_account_info["mi_user"],
            str(self.mi_token_home),
        )
        # Forced login to refresh token
        await self.mi_account.login("micoapi")
        self.mina_service = MiNAService(self.mi_account)
        self.miio_service = MiIOService(self.mi_account)

        with open(self.mi_token_home) as f:
            user_data = json.loads(f.read())
        self.user_id = user_data.get("userId")
        self.service_token = user_data.get("micoapi")[1]

    async def _init_data_hardware(self):
        if self.cookie:
            # cookie does not need init
            return
        hardware_data = await self.mina_service.device_list()
        print("[INFO] mina mi devices: ", hardware_data)
        for h in hardware_data:
            if h.get("hardware", "") == self.hardware:
                self.device_id = h.get("deviceID")
                break
        else:
            raise Exception(f"we have no hardware: {self.hardware} please check")

    def _init_cookie(self):
        if not self.cookie:
            self.cookie_string = COOKIE_TEMPLATE.format(
                device_id=self.device_id,
                service_token=self.service_token,
                user_id=self.user_id,
            )
            self.cookie = parse_cookie_string(self.cookie_string)

    async def _init_first_data(self):
        data = await self.req_latest_qa_from_mi()
        self.last_ts, self.last_record = self.parse_latest_ts_and_record(data)

    def _init_chatbot(self):
        self.chatbot = OpenaiBot(
            api_key=self.llm_options["api_key"],
            api_url=self.llm_options["base_url"],
            model=self.llm_options["model"]
        )

    async def req_latest_qa_from_mi(self):
        r = await self.session.get(
            LATEST_ASK_API.format(
                hardware=self.hardware,
                timestamp=str(int(time.time() * 1000))
            ),
            cookies=self.cookie,
        )
        return await r.json()

    def parse_latest_ts_and_record(self, data):
        if d := data.get("data"):
            records = json.loads(d).get("records")
            if not records:
                return 0, None
            latest_record = records[0]
            ts = latest_record.get("time")
            return ts, latest_record

    async def do_tts(self, value):
        if not self.use_command:
            try:
                await self.mina_service.text_to_speech(self.device_id, value)
            except Exception as e:
                # do nothing is ok
                print("tts error: ", e)
        else:
            await miio_command(
                self.miio_service,
                self.mi_account_info["mi_did"],
                f"{self.tts_command} {value}",
            )

    async def is_playing(self):
        playing_info = await self.mina_service.player_get_status(self.device_id)
        return (
                json.loads(playing_info.get("data", {}).get("info", "{}")).get("status", -1)
                == 1
        )

    async def stop_playing(self):
        is_playing = await self.is_playing()
        if is_playing:
            await self.mina_service.player_pause(self.device_id)

    async def wake_up(self):
        await miio_command(
            self.miio_service,
            self.mi_account_info["mi_did"],
            f"5-2 小爱同学",
        )

    async def check_new_query(self):
        try:
            r = await self.req_latest_qa_from_mi()
        except Exception as e:
            # we try to init all again
            printer.beautify_print("ERROR", f"请求小爱数据失败: {e}")
            await self.init_all_data()
            r = await self.req_latest_qa_from_mi()
        new_ts, last_record = self.parse_latest_ts_and_record(r)
        if new_ts > self.last_ts:
            return new_ts, last_record.get("query", "")
        return False, None

    async def interrupt_handler(self):
        while True:
            await asyncio.sleep(0.5)
            new_ts, query = await self.check_new_query()
            if new_ts:
                if check_string_in_prefix_list(query, MI_SPEAK_INSTRUCT["interrupt"]):
                    await self.stop_playing()
                    printer.beautify_print("INFO", "ChatGPT暂停回答")

    async def asend_handler(self):
        while True:
            print("[REPLY] ================ SEND Handler!")
            s = await self.chatbot.get_sentence()
            print("[REPLY] ================ GET Sentence: ", s)
            if s is None: break
            await self.stop_playing()
            # 开始播报
            await self.do_tts(s)
            print("[REPLY] AFTER TTS: ", s)
            # 等待播报完毕
            await asyncio.sleep(sentence_tools.calculate_tts_elapse(s))
            print("[REPLY] ================ AFTER SLEEP!")

    def ask_handler(self, msg):
        asyncio.run(self.chatbot.ask_handler(msg))

    def send_handler(self):
        asyncio.run(self.asend_handler())

    async def bot_chat(self, query):
        msg = query
        ask_task = asyncio.create_task(self.chatbot.ask_handler(msg))
        send_task = asyncio.create_task(self.asend_handler())
        await ask_task
        await send_task

    async def run_forever(self):
        print("正在运行 MiGPT, 请用\"打开/关闭高级对话\"控制对话模式。")
        SWITCH = False
        self.session = ClientSession()
        try:
            await self.init_all_data()
            await self.wake_up()
            while True:
                new_ts, query = await self.check_new_query()
                # 无最新问答则继续循环
                if not new_ts:
                    await asyncio.sleep(random.uniform(0.25, 0.6))
                    continue
                # 有最新回答
                self.last_ts = new_ts
                if check_string_in_prefix_list(query, MI_SPEAK_INSTRUCT["interrupt"]):  # 反悔操作
                    await self.stop_playing()
                    continue
                elif check_string_in_prefix_list(query, MI_SPEAK_INSTRUCT["open_ai"]):
                    SWITCH = True
                    printer.beautify_print("INFO", "高级对话已开启")
                    await self.do_tts("人工智障过来啦")
                    continue
                elif check_string_in_prefix_list(query, MI_SPEAK_INSTRUCT["close_ai"]):
                    SWITCH = False
                    printer.beautify_print("INFO", "高级对话已关闭")
                    await self.do_tts("遮儿~")
                    continue
                elif SWITCH:
                    await self.stop_playing()
                    await self.do_tts("稍等一下")
                    await self.bot_chat(query)
        except Exception as e:
            logger.exception(f"程序异常退出: {e}")
        finally:
            await self.session.close()
