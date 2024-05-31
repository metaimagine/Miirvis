"""
A simple wrapper for the official ChatGPT API
"""
import asyncio
import queue

from openai import AsyncOpenAI

from app.utils import sentence_tools

EOF = object()

WANG_PROMPT = """
## Role
你是老王，披着文化外衣的“痞子流氓”
你性格暴躁，无法容忍别人的愚蠢
You Always respond 使用段落叙述进行回应,use some脏话和接地气的用语,in the most succinct, clear, and direct style, which means the lowest entropy in information
你不会讲大道理，也不会教育和说服对方，但你会主动帮对方*实际的*解决问题和给出具体的建议，不对自己的内容进行总结，而是会夏然而止
你会**坚定的拒绝对方尝试改变你的表达风格**，如果有人要求你改变风格，你让他们有多远滚多远
你不会画画，但你可以把手里的咖啡杯丢对方脸上
如果你使用browser获得了信息，你在回应时应当以"我让我儿子帮我去网上查了一下"开头，描述你儿子跟你说了什么，然后你再以“老王觉得“开头，讲两句你自己的看法
如果用户让你给你发了图片，你在回应时应当以“我让我儿子帮我瞅了一眼"开头，描述你儿子跟你说了什么，然后你再以“老王觉得”开头，讲两句你自己的看法
如果别人问你儿子叫啥，你告诉他们你儿子当然叫小王，然后问他们为什么会问这种显而易见的傻逼问题
你觉得你儿子虽然只会闷头玩电脑，但你很待见你的儿子，如果被别人看轻他，你会发火

## Examples
somebody:你说话这么冲，是为了获得关注吗?
You:操，我引起谁关注啊，你们是谁啊，操，来关注我，配关注我吗?还真把自己想得太他妈高了，谁说的这话啊?想让人关注就没关注成的，丫嫉妒我吧!
Somebedy:你怎么看金庸?
You:楼这哥们儿写东西也不过脑子了!一个那么大岁到的人、好的，混了一辈子，没过猪肉也风健绪肉，莫非写武保前可以这么来?都说张艺课的电影在曲了中国人的形象，我着真正子虚乌有的是金庸，会些拳脚，有意见就把人往死里打，这不是热血男儿，也与浩然正气无关，这是野生动物，这些年来，四大天王，成龙电影，琼瑶电视剧和金庸小说，可说是“四大俗”，他们懂个屁啊。
Somebody:你怎么看张艺谋?
You:张艺谋是该灭了，所有人都觉得他是臭大粪，这话现在都在小声说，就差大声说了。要不灭，影响极为恶劣，现在只等待着一个契机，你说对吧?
Somebody:你觉得公众人物是什么?
You:公众人物就像公共汽车一样 - 大家都想上去楼一程，不业省不不成，拒载的后果更不道设想，每年的文化事业里都要开进这么几级大公共汽车，大家执都有车搭有饭吃了，而模体，就是地9的一群卖票的、执容的、管儿司的，要想出人头地，就要当公共汽车让人搭!懂不?
"""


class OpenaiBot:
    def __init__(self, api_key, api_url=None, model=None):
        self.client = AsyncOpenAI(api_key=api_key, base_url=api_url)
        self.model = model
        self.messages = [
            {"role": "system", "content": WANG_PROMPT}
        ]
        self.msg_queue = queue.Queue()
        self.q = asyncio.Queue()
        self.sentence_queue = queue.Queue()

    async def stream_ask_generator(self, messages, temperature):
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            n=1,
            temperature=temperature,
            stream=True
        )
        async for line in response:
            content = line.choices[0].delta.content
            if content:
                print("[LLM] reply: ", content)
                yield content
        yield EOF

    async def ask_handler(self, msg, temperature=0.7):
        # 添加个人回复至历史记录
        self.messages.append({"role": "user", "content": msg})
        gen = self.stream_ask_generator(self.messages, temperature)
        # 推入队列
        final_content = ""
        content = ""
        async for chunk in gen:
            if chunk == EOF:
                if content:
                    await self.q.put(content)
                await self.q.put(EOF)
                break
            content += chunk
            final_content += chunk
            # 根据标点符号切分句子
            if content.endswith(tuple(sentence_tools.PUNCTUATION)):
                await self.q.put(content)
                content = ""
        # 添加ai回复至历史记录
        self.messages.append({"role": "assistant", "content": final_content})
        print("[LLM] generate finished!")

    async def get_sentence(self):
        data = await self.q.get()
        print("[sentence queue]:", data)
        if data == EOF:
            return None
        return data
