from __future__ import annotations

from pathlib import Path
import shutil

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / "latex_assets"
CODE_DIR = ASSET_DIR / "code"
ASSET_DIR.mkdir(exist_ok=True)
CODE_DIR.mkdir(exist_ok=True)

FONT_PATH = Path(r"C:\Windows\Fonts\simsun.ttc")

CODE_MAP = {
    "dingweipao.txt": ROOT / "STL代码" / "定位跑.txt",
    "zhefanpao.txt": ROOT / "STL代码" / "折返跑.txt",
    "kualanpao.txt": ROOT / "STL代码" / "跨栏跑.txt",
    "position_pid.txt": ROOT / "STL代码" / "位置PID.txt",
    "dual_pid.txt": ROOT / "STL代码" / "双闭环PID.txt",
}


def strip_stl_comments(text: str) -> str:
    cleaned: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            cleaned.append("")
            continue
        if stripped.startswith("TITLE="):
            continue
        if stripped.startswith("//"):
            continue
        if "//" in line:
            line = line.split("//", 1)[0].rstrip()
        cleaned.append(line.rstrip())
    while cleaned and cleaned[-1] == "":
        cleaned.pop()
    return "\n".join(cleaned) + "\n"


def font(size: int):
    return ImageFont.truetype(str(FONT_PATH), size)


def wrap(text: str, width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in text:
        if char == "\n":
            if current:
                lines.append(current)
                current = ""
            continue
        current += char
        if len(current) >= width:
            lines.append(current)
            current = ""
    if current:
        lines.append(current)
    return lines


def draw_multiline_center(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, ft, fill: str) -> None:
    x1, y1, x2, y2 = box
    raw_lines = []
    for part in text.split("\n"):
        raw_lines.extend(wrap(part, 12))
    boxes = [draw.textbbox((0, 0), line, font=ft) for line in raw_lines]
    total_h = sum(b[3] - b[1] for b in boxes) + 10 * (len(boxes) - 1)
    y = y1 + ((y2 - y1) - total_h) / 2
    for line, bb in zip(raw_lines, boxes):
        w = bb[2] - bb[0]
        h = bb[3] - bb[1]
        x = x1 + ((x2 - x1) - w) / 2
        draw.text((x, y), line, font=ft, fill=fill)
        y += h + 10


def rounded_box(draw: ImageDraw.ImageDraw, box, text: str, fill: str, outline: str, ft) -> None:
    draw.rounded_rectangle(box, radius=26, fill=fill, outline=outline, width=4)
    draw_multiline_center(draw, box, text, ft, "#1F2F45")


def arrow(draw: ImageDraw.ImageDraw, pts: list[tuple[int, int]], *, fill="#40516F", width=5) -> None:
    for a, b in zip(pts[:-1], pts[1:]):
        draw.line([a, b], fill=fill, width=width)
    sx, sy = pts[-2]
    ex, ey = pts[-1]
    if abs(ex - sx) >= abs(ey - sy):
        d = 1 if ex > sx else -1
        tri = [(ex, ey), (ex - 18 * d, ey - 9), (ex - 18 * d, ey + 9)]
    else:
        d = 1 if ey > sy else -1
        tri = [(ex, ey), (ex - 9, ey - 18 * d), (ex + 9, ey - 18 * d)]
    draw.polygon(tri, fill=fill)


def label_box(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, ft, *, fill="#FFFFFF", outline="#C9D2E3") -> None:
    bb = draw.multiline_textbbox((0, 0), text, font=ft, spacing=4, align="center")
    pad_x = 16
    pad_y = 10
    x, y = xy
    box = (x, y, x + (bb[2] - bb[0]) + pad_x * 2, y + (bb[3] - bb[1]) + pad_y * 2)
    draw.rounded_rectangle(box, radius=14, fill=fill, outline=outline, width=2)
    draw.multiline_text((x + pad_x, y + pad_y), text, font=ft, fill="#40516F", spacing=4, align="center")


def make_hardware() -> None:
    img = Image.new("RGB", (1800, 1080), "#FFFFFF")
    draw = ImageDraw.Draw(img)
    ft_title = font(34)
    ft_box = font(28)
    ft_small = font(20)

    draw.text((560, 36), "数字化集成控制系统硬件拓扑图", font=ft_title, fill="#20324D")

    boxes = {
        "power": (90, 160, 410, 300),
        "hmi": (90, 510, 440, 660),
        "plc": (620, 300, 1040, 470),
        "encoder": (1240, 120, 1590, 270),
        "vfd": (1210, 410, 1590, 570),
        "motor": (1220, 740, 1590, 900),
    }

    rounded_box(draw, boxes["power"], "电源模块", "#D9E8F6", "#5A88B6", ft_box)
    rounded_box(draw, boxes["hmi"], "HMI 触摸屏\n数值输入 / 状态显示", "#DDECD1", "#7FA268", ft_box)
    rounded_box(draw, boxes["plc"], "S7-200 PLC\n高速计数 / 逻辑控制 / PID 运算", "#F7DEC8", "#D18252", ft_box)
    rounded_box(draw, boxes["encoder"], "增量式编码器\nA/B 相位置反馈", "#FBEAB7", "#C8A243", ft_box)
    rounded_box(draw, boxes["vfd"], "FRS520SE 变频器\n接收方向与速度指令", "#E3DDEE", "#8A73B0", ft_box)
    rounded_box(draw, boxes["motor"], "电机执行机构\n实现定位、折返、跨栏运动", "#F2CFCF", "#B55F5F", ft_box)

    arrow(draw, [(410, 220), (540, 220), (540, 340), (620, 340)])
    label_box(draw, (448, 170), "供电", ft_small)

    arrow(draw, [(250, 300), (250, 510)])
    label_box(draw, (170, 385), "触摸屏供电", ft_small)

    arrow(draw, [(410, 245), (1080, 245), (1080, 470), (1210, 470)])
    label_box(draw, (720, 195), "驱动器接口电源", ft_small)

    arrow(draw, [(440, 585), (560, 585), (560, 390), (620, 390)])
    label_box(draw, (468, 528), "RS485 通讯", ft_small)

    arrow(draw, [(1240, 195), (1120, 195), (1040, 385)])
    label_box(draw, (1050, 210), "I0.0 / I0.1", ft_small)

    arrow(draw, [(1040, 435), (1130, 435), (1210, 490)])
    label_box(draw, (960, 500), "Q0.0 / Q0.1\nAQW0 / Q0.3~Q0.5", ft_small)

    arrow(draw, [(1400, 570), (1400, 740)])
    label_box(draw, (1440, 630), "驱动输出", ft_small)

    img.save(ASSET_DIR / "hardware_topology.png")


def make_software() -> None:
    img = Image.new("RGB", (1800, 1260), "#FFFFFF")
    draw = ImageDraw.Draw(img)
    ft_title = font(34)
    ft_box = font(26)
    ft_small = font(20)

    draw.text((555, 34), "主程序与子程序软件流程图", font=ft_title, fill="#20324D")

    center_x1 = 620
    center_x2 = 1180
    y = 110
    step_h = 118
    gap = 62
    steps = [
        ("系统上电初始化\n配置 HSC0、定时中断、PID 参数", "#D9E8F6", "#5A88B6"),
        ("读取 HMI 参数\n圈数、折返点、速度切换点", "#DDECD1", "#7FA268"),
        ("模式判断\n定位跑 / 折返跑 / 跨栏跑 / PID 模式", "#F7DEC8", "#D18252"),
        ("执行对应子程序\n状态机 / 计数器 / PID 运算", "#E3DDEE", "#8A73B0"),
        ("输出控制量\n方向输出、速度档位、模拟量", "#FBEAB7", "#C8A243"),
        ("编码器反馈与结束判断\n到位、折返、变速、停机", "#F2CFCF", "#B55F5F"),
    ]
    boxes = []
    for text, fill, outline in steps:
        box = (center_x1, y, center_x2, y + step_h)
        boxes.append(box)
        rounded_box(draw, box, text, fill, outline, ft_box)
        y += step_h + gap

    for a, b in zip(boxes[:-1], boxes[1:]):
        arrow(draw, [((a[0] + a[2]) // 2, a[3]), ((b[0] + b[2]) // 2, b[1])])

    high_speed = (110, 520, 430, 670)
    pid_box = (110, 760, 430, 910)
    rounded_box(draw, high_speed, "高速计数子程序\nHC0 脉冲换算", "#DDECD1", "#7FA268", ft_box)
    rounded_box(draw, pid_box, "PID 运算子程序\n位置环 / 速度环", "#D9E8F6", "#5A88B6", ft_box)
    arrow(draw, [(430, 595), (520, 595), (520, 640), (620, 640)])
    arrow(draw, [(430, 835), (520, 835), (520, 820), (620, 820)])
    label_box(draw, (120, 930), "子程序结果写回主流程", ft_small)

    loop_note = (1300, 520, 1650, 680)
    draw.rounded_rectangle(loop_note, radius=22, fill="#F7F9FC", outline="#B7C4D6", width=3)
    draw_multiline_center(draw, loop_note, "未结束则循环\n实时刷新参数", ft_box, "#40516F")
    arrow(draw, [(1180, boxes[-1][3] - 20), (1270, boxes[-1][3] - 20), (1270, 600), (1300, 600)])
    arrow(draw, [(1300, 600), (1270, 600), (1270, boxes[1][1] + 50), (1180, boxes[1][1] + 50)])

    img.save(ASSET_DIR / "software_flow.png")


def copy_code_files() -> None:
    for target, source in CODE_MAP.items():
        text = source.read_text(encoding="utf-8")
        (CODE_DIR / target).write_text(strip_stl_comments(text), encoding="utf-8")


def main() -> None:
    make_hardware()
    make_software()
    copy_code_files()


if __name__ == "__main__":
    main()
