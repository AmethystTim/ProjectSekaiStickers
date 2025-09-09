from operator import index
import os, re, json

from pkg.plugin.context import register, handler, BasePlugin, APIHost, EventContext
from pkg.plugin.events import *  # 导入事件类
from pkg.platform.types import *

from .utils import *
from .messageplatform import *

current_dir = os.path.dirname(__file__)

# 注册插件
@register(name="ProjectSekaiStickers", description="pjsk表情包生成器", version="1.0", author="Amethyst")
class ProjectSekaiStickers(BasePlugin):
    # 插件加载时触发
    def __init__(self, host: APIHost):
        self.msgplatform = NapCatApi(port=3000)
        self.instructions = {
            "pjsk": r"pjsk$",
            "pjsk help": r"pjsk\s+help$",
            "pjsk ls [角色名]": r"^pjsk\s+ls(?:\s+(\S+))?$",
            "pjsk [角色名] [文本]": r"pjsk\s+(\S+)\s+(.+?)(?:\s+-(?:font\s+(\d+)|i\s+(\d+)))*$",
        }

    def matchPattern(self, msg):
        '''
        匹配指令
        
        args:
            msg: 指令内容
        return:
            匹配结果
        '''
        res = None
        for pattern in self.instructions:
            if re.match(self.instructions[pattern], msg):
                res = pattern
                break
        return res    
    
    # 异步初始化
    async def initialize(self):
        pass

    # 当收到群消息时触发
    @handler(GroupMessageReceived)
    async def group_message_received(self, ctx: EventContext):
        msg = str(ctx.event.message_chain).strip()
        sender_id = ctx.event.sender_id
        
        if not self.matchPattern(msg):
            return
        match self.matchPattern(msg):
            case "pjsk" | "pjsk help":
                await ctx.reply(MessageChain([
                    Plain("ProjectSekaiStickers：啤酒烧烤表情包生成器\n"),
                    Plain("指令：\n"),
                    Plain("· pjsk help：查看帮助\n"),
                    Plain("· pjsk ls: 查看所有角色\n"),
                    Plain("· pjsk ls [角色名]：查看角色底图\n"),
                    Plain("· pjsk [角色名] [文本]：生成表情包\n"),
                    Plain("\n可选参数："),
                    Plain("\n-i [序号]：底图序号，默认值1"),
                    Plain("\n-font [大小]：字体大小，默认值48"),
                ]))       
            case "pjsk ls [角色名]":
                m = re.match(r"^pjsk\s+ls(?:\s+(\S+))?$", msg)
                if not m or not m.group(1):
                    characters = await get_all_characters()
                    await ctx.reply(MessageChain([
                        Plain("可用角色：\n"),
                        Plain("，".join(characters)),
                    ]))
                    return
                character_name = m.group(1)
                # 列出角色可用底图
                character_dir = await get_character_dir(character_name)
                if not character_dir:
                    await ctx.reply(MessageChain([
                        Plain(f"未找到角色：{character_name}"),
                    ]))
                    return
                images_path = await get_character_images(character_dir)
                
                # 使用langbot api回复消息
                # img_components = [await Image.from_local(os.path.join(character_dir, img_path)) for img_path in images_path]
                # msg_chain = MessageChain([
                #     Plain(f"{character_name}可用底图：\n"),
                # ])
                # for img_component in img_components:
                #     msg_chain.append(img_component)
                # await ctx.reply(msg_chain)
                
                # 使用napcat合并转发，避免刷屏
                temp_paths = []
                for index, img_path in enumerate(images_path):
                    resp = await self.msgplatform.callApi('/download_file', {
                        "base64": image_to_base64(img_path),
                        "thread_count": 0,
                        "name": f"{character_name}_{index+1}"
                    })
                    save_path = resp.get('data').get('file')
                    temp_paths.append(save_path)
                
                nodes = [{
                            "type": "node",
                            "data": {
                                "user_id": "2537971097",
                                "nickname": "BOT",
                                "content": [
                                    {"type": "text", "data": {"text": f"{character_name}_{str(index)}"}},
                                    {"type": "image", "data": {"file": f"{img_path}"}}
                                ]
                            }
                        } for index, img_path in enumerate(temp_paths)]
                resp = await self.msgplatform.callApi('/send_group_forward_msg', {
                    "group_id": str(ctx.event.launcher_id),
                    "user_id": "",
                    "messages": nodes,
                    "news": [
                        {"text": f"小波：你总是这样"},
                        {"text": f"小波：[图片]"},
                        {"text": f"小波：我们分手吧"}
                    ],
                    "prompt": "[文件]年度学习资料.zip",
                    "summary": "点击浏览",
                    "source": "合并转发的聊天记录"
                })
            case "pjsk [角色名] [文本]":
                match = re.match(r"pjsk\s+(\S+)\s+(.+?)(?:\s+-\w+\s+\d+)*$", msg)
                character_name = match.group(1)
                text = match.group(2)
                
                params = re.findall(r"-(font|i)\s+(\d+)", msg)
                font_size = 48
                image_index = 1
                for key, value in params:
                    if key == "font":
                        font_size = int(value)
                    elif key == "i":
                        image_index = int(value)
                
                character_dir = await get_character_dir(character_name)
                if not character_dir:
                    await ctx.reply(MessageChain([
                        Plain(f"未找到角色：{character_name}"),
                    ]))
                    return
                sticker_path, err = await make_sticker(character_dir, text, index=image_index, font_size=font_size)
                if not sticker_path:
                    await ctx.reply(MessageChain([
                        Plain(f"生成失败：{err}"),
                    ]))
                    return
                img_component = await Image.from_local(sticker_path)
                await ctx.reply(MessageChain([
                    img_component
                ]))
            case _:
                pass
                
    # 插件卸载时触发
    def __del__(self):
        pass
