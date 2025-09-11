import PIL
import os
import json
import base64

CHARACTERS_DIR = os.path.join(os.path.dirname(__file__), 'assets', 'characters')
FONT_PATH = os.path.join(os.path.dirname(__file__), 'assets', 'fonts', 'ShangShouFangTangTi.woff')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output')

def image_to_base64(image_path):
    """
    将图片文件转换为 Base64 编码字符串
    """
    with open(image_path, "rb") as f:
        encoded_bytes = base64.b64encode(f.read())
        # 转成字符串
        encoded_str = encoded_bytes.decode("utf-8")
    return encoded_str

async def get_all_characters():
    '''获取所有角色名
    Returns:
        characters (list): 角色名列表
    '''
    characters = []
    for character_dir in os.listdir(CHARACTERS_DIR):
        if character_dir.endswith('.png'):
            continue
        characters.append(character_dir)
    return characters

async def get_character_dir(character_name: str):
    '''获取指定角色的目录路径。如果角色不存在，返回None
    Args:
        character_name (str): 角色名
    Returns:
        dir_path (str): 角色目录路径
    '''
    dir_path = None
    for character_dir in os.listdir(CHARACTERS_DIR):
        if character_dir.lower() == character_name.lower():
            dir_path = os.path.join(CHARACTERS_DIR, character_dir)
            break
    return dir_path

async def get_character_images(character_dir: str):
    '''获取指定角色的所有图片路径
    Args:
        character_dir (str): 角色目录路径
    Returns:
        images (list): 角色图片路径列表
    '''
    images = [os.path.join(character_dir, f) for f in os.listdir(character_dir) if f.endswith('.png')]
    return images

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

async def get_character_color(character_name: str):
    fandom_color = "#000000"
    JSON_PATH = os.path.join(os.path.dirname(__file__), 'fandomcolor.json')
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for character in data.keys():
        if character.lower() == character_name.lower():
            fandom_color = data[character]
    return fandom_color

async def draw_text_with_border(draw, position, text, font, fill, border_color, border_width=2):
    """
    在 Pillow ImageDraw 上绘制带边框文字
    Args:
        draw: ImageDraw.Draw 对象
        position: (x, y) 左上角位置
        text: 要绘制的文字
        font: 字体对象
        fill: 内部文字颜色
        border_color: 描边颜色
        border_width: 描边厚度
    """
    x, y = position
    # 在文字周围偏移绘制 border
    for dx in range(-border_width, border_width + 1):
        for dy in range(-border_width, border_width + 1):
            if dx == 0 and dy == 0:
                continue
            draw.text((x + dx, y + dy), text, font=font, fill=border_color)

    draw.text((x, y), text, font=font, fill=fill)


async def make_sticker(character_dir: str, text: str, index: int=1, font_size: int=48):
    '''生成表情包贴纸
    Args:
        character_dir (str): 角色目录路径
        index (int): 角色贴纸索引
        text (str): 贴纸文字
        font_size (int): 字体大小
    Returns:
        output_path (str): 输出路径
    '''
    output_path = None
    try:
        images = [os.path.join(character_dir, f) for f in os.listdir(character_dir) if f.endswith('.png')]
        image_path = images[index]

        img = PIL.Image.open(image_path).convert("RGBA")
        draw = PIL.ImageDraw.Draw(img)
        font = PIL.ImageFont.truetype(FONT_PATH, font_size)

        line_spacing = int(font_size * 0.2)

        def wrap_text(text, font, max_width):
            words = list(text)
            lines = []
            current_line = ""
            for char in words:
                test_line = current_line + char
                bbox = draw.textbbox((0, 0), test_line, font=font)
                line_width = bbox[2] - bbox[0]
                if line_width <= max_width:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = char
            if current_line:
                lines.append(current_line)
            return lines

        # 最大文字宽度为图片宽度的90%
        max_text_width = int(img.width * 0.9)
        lines = wrap_text(text, font, max_text_width)

        ascent, descent = font.getmetrics()
        base_line_height = ascent + descent
        line_height = int(base_line_height * 1.2)

        # 顶部和底部 padding
        top_padding = int((line_height - base_line_height) / 2)
        bottom_padding = top_padding

        total_height = line_height * len(lines) + line_spacing * (len(lines) - 1) + top_padding + bottom_padding

        text_img = PIL.Image.new("RGBA", (max_text_width, total_height), (0, 0, 0, 0))
        text_draw = PIL.ImageDraw.Draw(text_img)

        for i, line in enumerate(lines):
            bbox = text_draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            x_line = (max_text_width - line_width) // 2  # 居中
            y_line = top_padding + i * (line_height + line_spacing)  # 顶部 padding + 行高

            character_name = character_dir.split('/')[-1] if not character_dir.endswith('/') else character_dir.split('/')[-2]
            fill_color = await get_character_color(character_name)
            fill_color = hex_to_rgb(fill_color)
            await draw_text_with_border(
                text_draw, 
                (x_line, y_line), 
                line, 
                font=font, 
                fill=fill_color,                                       # 文字颜色
                border_color=(255, 255, 255),                                  # 描边颜色
                border_width=4                                              # 描边厚度
            )

        # 旋转文字
        rotated_text = text_img.rotate(10, expand=1, resample=PIL.Image.BICUBIC)

        # 粘贴到原图
        x = (img.width - rotated_text.width) // 2
        y = (img.height - rotated_text.height) // 6
        img.paste(rotated_text, (x, y), rotated_text)

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        hash_str = str(hash(character_dir + text))
        output_filename = f'{hash_str}.png'
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        img.save(output_path)
    except Exception as e:
        return None, str(e)
    return output_path, ""
