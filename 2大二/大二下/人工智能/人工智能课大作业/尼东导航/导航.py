import tkinter as tk
from tkinter import ttk
import heapq
import math
import os
from PIL import Image, ImageTk
from tkinter import INSERT
import pyttsx3
import threading

class CampusNavigator:
    def __init__(self, root):
        self.root = root
        self.root.title("东北大学校园导航系统")
        self.instruction_window = None

        # 新增缩放状态变量
        self.is_zoomed = False
        self.zoom_factor = 1.0  # 当前缩放比例
        self.pan_start = (0, 0)
        self.bg_width = 1000  # 默认值
        self.bg_height = 800  # 默认值
        self.original_bg_image = None
        self.current_bg_image = None
        self.map_image_id = None

        # 加载背景图片
        try:
            current_dir = os.path.dirname(__file__)
            bg_image_path = os.path.join(current_dir, "地图.jpg")
            pil_image = Image.open(bg_image_path)
            self.bg_image = ImageTk.PhotoImage(pil_image)
            self.bg_width, self.bg_height = pil_image.size# 存储为实例变量
            zoomed_image_path = os.path.join(current_dir, "地图.jpg")
            pil_zoomed = Image.open(zoomed_image_path)
            self.zoomed_bg_image = ImageTk.PhotoImage(pil_zoomed)  # 保存放大模式背景图



        except Exception as e:
            print(f"地图加载失败: {str(e)}")
            self.bg_width, self.bg_height = 1000, 800  # 默认尺寸

        self.root.geometry(f"{self.bg_width + 320}x{self.bg_height + 20}")

        # 节点坐标数据
        self.node_coords = {
            1: (412, 787), 2: (596, 784), 3: (597, 823), 4: (596, 850), 5: (696, 780),
            6: (693, 846), 7: (813, 778), 8: (808, 828), 9: (842, 778), 10: (893, 776),
            11: (287, 778), 12: (289, 676), 13: (412, 677), 14: (568, 672), 15: (725, 670),
            16: (843, 670), 17: (889, 670), 18: (144, 621), 19: (286, 618), 20: (410, 618),
            21: (567, 613), 22: (724, 608), 23: (889, 607), 24: (134, 425), 25: (259, 419),
            26: (405, 463), 27: (566, 466), 28: (720, 462), 29: (883, 459), 30: (401, 364),
            31: (561, 360), 32: (716, 360), 33: (884, 362), 34: (887, 291), 35: (882, 144),
            36: (736, 228), 37: (711, 239), 38: (575, 239), 39: (560, 82), 40: (710, 82),
            41: (133, 373), 42: (133, 302), 43: (259, 307), 44: (757, 360), 45: (757, 375),
            46: (757, 405), 47: (740, 431), 48: (779, 420), 49: (818, 413), 50: (406, 418),
            51: (566, 418), 52: (492, 415), 53: (534, 466), 54: (616, 673), 55: (676, 673),
            "南门": (414, 930), "北门": (634, 5), "一舍东": (810, 778), "一舍西": (675, 700),
            "老二舍北": (615, 701), "老二舍南": (431, 785), "新二舍": (287, 729),
            "三舍A": (810, 830), "三舍B": (810, 830), "三舍C": (694, 845),
            "四舍": (597, 822), "五舍": (597, 849), "六舍": (133, 377), "七舍": (218, 340),
            "八舍": (132, 321), "九舍": (138, 521), "十舍": (83, 630), "博后公寓": (86, 622),
            "一食堂": (767, 780), "二食堂": (518, 781), "中心食堂": (596, 837), "培训餐厅": (695, 830),
            "五四": (880, 188), "五五": (135, 478),
            "大成": (807, 609), "逸夫": (492, 675), "何世礼": (521, 613),
            "机电": (487, 468), "采矿": (752, 361), "冶金": (800, 461), "建筑学馆": (554, 359),
            "大活": (567, 626), "综合楼": (644, 611), "信息楼": (637, 199), "汉卿会堂": (258, 420),
            "图书馆": (633, 359), "综合实验楼": (411, 828), "知行楼": (891, 739),
            "机械实验楼": (340, 619), "刘长春": (899, 359), "游泳馆": (884, 293)
        }

        # 特殊路径段配置
        self.special_segments = {
            ((259, 419), (401, 364)): "right",
            ((405, 463), (259, 419)): "right",
            ((887, 291), (736, 228)): "right",
            ((575, 239), (637, 199)): "right",
            ((637, 199), (711, 239)): "right",
            ((218, 340), (133, 373)): "right",
            ((401, 364), (259, 419)): "left",
            ((259, 419), (405, 463)): "left",
            ((736, 228), (887, 291)): "left",
            ((637, 199), (575, 239)): "left",
            ((711, 239), (637, 199)): "left",
            ((133, 373), (218, 340)): "left"
        }

        # 步行和骑行两种模式的邻接关系
        self.walk_graph = {
            "南门": {1: 1}, "北门": {39: 1, 40: 1}, "一舍东": {5: 1, 7: 1}, "一舍西": {55: 1, 5: 1},
            "一食堂": {5: 1, 7: 1}, "七舍": {41: 1}, "三舍A": {8: 1}, "三舍B": {8: 1},
            "三舍C": {6: 1}, "中心食堂": {3: 1, 4: 1}, "九舍": {18: 1, 24: 1},
            "二食堂": {1: 1, 2: 1}, "五五": {24: 1, 18: 1}, "五四": {34: 1, 35: 1},
            "五舍": {4: 1}, "何世礼": {20: 1, 21: 1}, "信息楼": {37: 1, 38: 1},
            "八舍": {42: 1, 41: 1}, "六舍": {24: 1, 41: 1}, "冶金": {28: 1, 29: 1},
            "刘长春": {33: 1}, "十舍": {18: 1}, "博后公寓": {18: 1}, "四舍": {3: 1},
            "图书馆": {31: 1, 32: 1}, "培训餐厅": {5: 1, 6: 1}, "大成": {22: 1, 23: 1},
            "大活": {21: 1, 14: 1}, "建筑学馆": {30: 1, 31: 1}, "新二舍": {11: 1, 12: 1},
            "机械实验楼": {19: 1, 20: 1}, "机电": {26: 1, 53: 1}, "汉卿会堂": {25: 1},
            "游泳馆": {34: 1}, "知行楼": {17: 1, 10: 1}, "综合实验楼": {1: 1},
            "综合楼": {21: 1, 22: 1}, "老二舍南": {1: 1, 2: 1}, "老二舍北": {2: 1, 54: 1},
            "逸夫": {13: 1, 14: 1}, "采矿": {32: 1, 33: 1, 44: 1},
            1: {11: 1, 2: 1, 13: 1, "综合实验楼": 1, "老二舍南": 1, "南门": 1, "二食堂": 1},
            2: {1: 1, 3: 1, 54: 1, 55: 1, "二食堂": 1, "老二舍北": 1, "老二舍南": 1},
            3: {2: 1, 4: 1, "四舍": 1, "中心食堂": 1},
            4: {3: 1, "五舍": 1, "中心食堂": 1},
            5: {54: 1, 55: 1, 6: 1, 7: 1, "培训餐厅": 1, "一食堂": 1, "一舍东": 1, "一舍西": 1},
            6: {5: 1, 8: 1, "三舍C": 1, "培训餐厅": 1},
            7: {5: 1, 8: 1, 9: 1, "一舍东": 1, "一食堂": 1},
            8: {7: 1, 6: 1, "三舍A": 1, "三舍B": 1},
            9: {7: 1, 10: 1, 16: 1},
            10: {9: 1, 17: 1, "知行楼": 1},
            11: {1: 1, 12: 1, "新二舍": 1},
            12: {11: 1, 13: 1, 19: 1, "新二舍": 1},
            13: {12: 1, 1: 1, 20: 1, 14: 1, "逸夫": 1},
            14: {13: 1, 21: 1, 54: 1, "逸夫": 1, "大活": 1},
            15: {55: 1, 22: 1, 16: 1},
            16: {15: 1, 9: 1, 17: 1},
            17: {16: 1, 10: 1, 23: 1, "知行楼": 1},
            18: {19: 1, 24: 1, "十舍": 1, "博后公寓": 1, "九舍": 1, "五五": 1},
            19: {18: 1, 12: 1, 20: 1, "机械实验楼": 1},
            20: {19: 1, 13: 1, 26: 1, 21: 1, "机械实验楼": 1, "何世礼": 1},
            21: {20: 1, 14: 1, 22: 1, 27: 1, "何世礼": 1, "大活": 1, "综合楼": 1},
            22: {23: 1, 21: 1, 15: 1, 28: 1, "综合楼": 1, "大成": 1},
            23: {22: 1, 17: 1, 29: 1, "大成": 1},
            24: {18: 1, 25: 1, 41: 1, "五五": 1, "六舍": 1, "九舍": 1},
            25: {24: 1, 43: 1, 26: 1, 30: 1, "汉卿会堂": 1},
            26: {25: 1, 50: 1, 20: 1, 53: 1, "机电": 1},
            27: {53: 1, 51: 1, 21: 1, 28: 1},
            28: {27: 1, 32: 1, 47: 1, 29: 1, 22: 1, "冶金": 1},
            29: {28: 1, 23: 1, 33: 1, 49: 1, "冶金": 1},
            30: {25: 1, 50: 1, 31: 1, "建筑学馆": 1},
            31: {30: 1, 51: 1, 32: 1, 38: 1, "建筑学馆": 1, "图书馆": 1},
            32: {31: 1, 44: 1, 37: 1, 28: 1, "图书馆": 1, "采矿": 1},
            33: {44: 1, 29: 1, 34: 1, 49: 1, "采矿": 1, "刘长春": 1},
            34: {33: 1, 36: 1, 35: 1, "五四": 1, "游泳馆": 1},
            35: {34: 1, 36: 1, "五四": 1},
            36: {37: 1, 35: 1, 34: 1},
            37: {32: 1, 38: 1, 40: 1, 36: 1, "信息楼": 1},
            38: {31: 1, 39: 1, 37: 1, "信息楼": 1},
            39: {38: 1, 40: 1, "北门": 1},
            40: {39: 1, 37: 1, "北门": 1},
            41: {24: 1, 42: 1, "六舍": 1, "七舍": 1, "八舍": 1},
            42: {41: 1, 43: 1, "八舍": 1},
            43: {42: 1, 25: 1},
            44: {32: 1, 33: 1, 45: 1, "采矿": 1},
            45: {44: 1, 49: 1, 46: 1},
            46: {45: 1, 48: 1, 47: 1},
            47: {28: 1, 46: 1, 48: 1},
            48: {47: 1, 46: 1, 49: 1},
            49: {48: 1, 45: 1, 29: 1, 33: 1},
            50: {30: 1, 52: 1, 26: 1},
            51: {52: 1, 31: 1, 27: 1},
            52: {51: 1, 50: 1, 53: 1},
            53: {26: 1, 27: 1, 52: 1, "机电": 1},
            54: {14: 1, 55: 1, 2: 1, 5: 1, "老二舍北": 1},
            55: {54: 1, 2: 1, 5: 1, 15: 1, "一舍西": 1}
        }

        self.bike_graph = {
            "南门": {1: 1}, "北门": {39: 1, 40: 1}, "一舍东": {5: 1, 7: 1}, "一舍西": {55: 1, 5: 1},
            "一食堂": {5: 1, 7: 1}, "七舍": {41: 1}, "三舍A": {8: 1}, "三舍B": {8: 1},
            "三舍C": {6: 1}, "中心食堂": {3: 1, 4: 1}, "九舍": {18: 1, 24: 1},
            "二食堂": {1: 1, 2: 1}, "五五": {24: 1, 18: 1}, "五四": {34: 1, 35: 1},
            "五舍": {4: 1}, "何世礼": {20: 1, 21: 1}, "信息楼": {37: 1, 38: 1},
            "八舍": {42: 1, 41: 1}, "六舍": {24: 1, 41: 1}, "冶金": {28: 1, 29: 1},
            "刘长春": {33: 1}, "十舍": {18: 1}, "博后公寓": {18: 1}, "四舍": {3: 1},
            "图书馆": {31: 1, 32: 1}, "培训餐厅": {5: 1, 6: 1}, "大成": {22: 1, 23: 1},
            "大活": {21: 1, 14: 1}, "建筑学馆": {31: 1}, "新二舍": {11: 1, 12: 1},
            "机械实验楼": {19: 1, 20: 1}, "机电": {26: 1, 53: 1}, "汉卿会堂": {25: 1},
            "游泳馆": {34: 1}, "知行楼": {17: 1, 10: 1}, "综合实验楼": {1: 1},
            "综合楼": {21: 1, 22: 1}, "老二舍南": {1: 1, 2: 1}, "老二舍北": {2: 1, 54: 1},
            "逸夫": {13: 1, 14: 1}, "采矿": {32: 1, 33: 1},
            1: {11: 1, 2: 1, 13: 1, "综合实验楼": 1, "老二舍南": 1, "南门": 1, "二食堂": 1},
            2: {1: 1, 3: 1, 54: 1, "二食堂": 1, "老二舍北": 1},
            3: {2: 1, 4: 1, "四舍": 1, "中心食堂": 1},
            4: {3: 1, "五舍": 1, "中心食堂": 1},
            5: {55: 1, 6: 1, 7: 1, "培训餐厅": 1, "一食堂": 1, "一舍东": 1, "一舍西": 1},
            6: {5: 1, 8: 1, "三舍C": 1, "培训餐厅": 1},
            7: {5: 1, 8: 1, 9: 1, "一舍东": 1, "一食堂": 1},
            8: {7: 1, 6: 1, "三舍A": 1, "三舍B": 1},
            9: {7: 1, 10: 1, 16: 1},
            10: {9: 1, 17: 1, "知行楼": 1},
            11: {1: 1, 12: 1, "新二舍": 1},
            12: {11: 1, 13: 1, 19: 1, "新二舍": 1},
            13: {12: 1, 1: 1, 20: 1, 14: 1, "逸夫": 1},
            14: {13: 1, 21: 1, 54: 1, "逸夫": 1, "大活": 1},
            15: {55: 1, 22: 1, 16: 1},
            16: {15: 1, 9: 1, 17: 1},
            17: {16: 1, 10: 1, 23: 1, "知行楼": 1},
            18: {19: 1, 24: 1, "十舍": 1, "博后公寓": 1, "九舍": 1, "五五": 1},
            19: {18: 1, 12: 1, 20: 1, "机械实验楼": 1},
            20: {19: 1, 13: 1, 26: 1, 21: 1, "机械实验楼": 1, "何世礼": 1},
            21: {20: 1, 14: 1, 22: 1, 27: 1, "何世礼": 1, "大活": 1, "综合楼": 1},
            22: {23: 1, 21: 1, 15: 1, 28: 1, "综合楼": 1, "大成": 1},
            23: {22: 1, 17: 1, 29: 1, "大成": 1},
            24: {18: 1, 25: 1, 41: 1, "五五": 1, "六舍": 1, "九舍": 1},
            25: {24: 1, 43: 1, 26: 1, 30: 1, "汉卿会堂": 1},
            26: {25: 1, 50: 1, 20: 1, 53: 1, "机电": 1},
            27: {53: 1, 51: 1, 21: 1, 28: 1},
            28: {27: 1, 32: 1, 29: 1, 22: 1, "冶金": 1},
            29: {28: 1, 23: 1, 33: 1, "冶金": 1},
            30: {25: 1, 50: 1, 31: 1, "建筑学馆": 1},
            31: {30: 1, 51: 1, 32: 1, 38: 1, "建筑学馆": 1, "图书馆": 1},
            32: {31: 1, 37: 1, 28: 1, "图书馆": 1, "采矿": 1},
            33: {29: 1, 34: 1, "采矿": 1, "刘长春": 1},
            34: {33: 1, 36: 1, 35: 1, "五四": 1, "游泳馆": 1},
            35: {34: 1, 36: 1, "五四": 1, "游泳馆": 1},
            36: {37: 1, 35: 1, 34: 1},
            37: {32: 1, 38: 1, 40: 1, 36: 1, "信息楼": 1},
            38: {31: 1, 39: 1, 37: 1, "信息楼": 1},
            39: {38: 1, 40: 1, "北门": 1},
            40: {39: 1, 37: 1, "北门": 1},
            41: {24: 1, 42: 1, "六舍": 1, "七舍": 1},
            42: {41: 1, 43: 1, "八舍": 1},
            43: {42: 1, 25: 1},
            50: {30: 1, 26: 1},
            51: {31: 1, 27: 1},
            53: {26: 1, 27: 1, "机电": 1},
            54: {14: 1, 55: 1, 2: 1, "老二舍北": 1},
            55: {54: 1, 5: 1, 15: 1, "一舍西": 1}
        }

        self._create_widgets()  # 修正点：移除了参数传递
        self.current_graph = self.walk_graph
        self._validate_data()
        self.locations = {k: v for k, v in self.node_coords.items() if isinstance(k, str)}
        self.all_locations = list(self.locations.keys())
        self.current_nav = None
        self._draw_base_map()

        self.location_order = [
            "南门", "北门", "一舍东", "一舍西", "老二舍北", "老二舍南", "新二舍",
            "三舍A", "三舍B", "三舍C", "四舍", "五舍", "六舍", "七舍", "八舍",
            "九舍", "十舍", "博后公寓", "一食堂", "二食堂", "中心食堂", "培训餐厅",
            "五四", "五五", "大成", "逸夫", "何世礼", "机电", "采矿", "冶金",
            "建筑学馆", "大活", "综合楼", "信息楼", "汉卿会堂", "图书馆", "综合实验楼",
            "知行楼", "机械实验楼", "刘长春", "游泳馆"
        ]
        self.map_canvas.bind("<Button-1>", self.on_map_click)
        # 语音引擎初始化
        self.engine = None
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 150)  # 设置语速
        except Exception as e:
            print(f"语音引擎初始化失败: {e}")

    def on_map_click(self, event):
        if self.is_zoomed:
            return
        canvas_x = self.map_canvas.canvasx(event.x)
        canvas_y = self.map_canvas.canvasy(event.y)

        for name, (nx, ny) in self.node_coords.items():
            if not isinstance(name, str):
                continue
            distance = math.hypot(canvas_x - nx, canvas_y - ny)
            if distance < 10:
                index = self.location_order.index(name) + 1 if name in self.location_order else None
                if index:
                    self.show_location_image(index, event.x_root, event.y_root)
                break

    def show_location_image(self, index, x, y):
        try:
            current_dir = os.path.dirname(__file__)
            scenery_dir = os.path.join(current_dir, "scenery")
            img_path = os.path.join(scenery_dir, f"{index}.png")
            pil_img = Image.open(img_path).resize((200, 200), Image.Resampling.LANCZOS)
            img = ImageTk.PhotoImage(pil_img)

            if hasattr(self, 'location_window'):
                self.location_window.destroy()

            self.location_window = tk.Toplevel(self.root)
            self.location_window.overrideredirect(True)

            # 调整显示位置
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()

            if x + 200 > screen_width:
                x = screen_width - 200
            if y + 200 > screen_height:
                y = screen_height - 200
            else:
                y += 10  # 与鼠标保持小间距

            self.location_window.geometry(f"+{int(x)}+{int(y)}")
            label = tk.Label(self.location_window, image=img)
            label.image = img
            label.pack()

            self.location_window.bind("<Button-1>", lambda e: self.location_window.destroy())
        except Exception as e:
            print(f"图片加载失败: {e}")

    def _create_widgets(self):
        # 地图画布保持不变
        self.map_canvas = tk.Canvas(self.root,
                                    width=self.bg_width,
                                    height=self.bg_height,
                                    bg="white")
        self.map_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        if hasattr(self, 'bg_image'):
            self.bg_image_id = self.map_canvas.create_image(0, 0, image=self.bg_image, anchor=tk.NW)
            self.map_canvas.create_image(0, 0, image=self.bg_image, anchor=tk.NW)

        # 控制面板框架
        control_frame = tk.Frame(self.root)
        control_frame.pack(side=tk.RIGHT, padx=15, pady=15, fill=tk.Y)

        # 统一控件样式
        style = ttk.Style()
        style.configure('TCombobox', padding=5)
        style.configure('TButton', padding=6, font=('微软雅黑', 10))

        # 输入参数区域
        input_frame = ttk.Frame(control_frame)
        input_frame.grid(row=0, column=0, pady=5, sticky='nw')

        # 起点选择（添加搜索功能）
        ttk.Label(input_frame, text="起点:", font=('微软雅黑', 11)).grid(row=0, column=0, sticky='w', pady=3)
        self.start_var = tk.StringVar()
        self.start_combo = ttk.Combobox(input_frame,
                                        textvariable=self.start_var,
                                        width=18,
                                        font=('微软雅黑', 10))  # 确保字体支持中文
        self.start_combo.grid(row=0, column=1, pady=3, padx=(5, 0))
        self.start_combo.bind('<KeyRelease>', lambda e: self._filter_locations(self.start_combo, self.start_var))
        self.start_combo.bind('<FocusIn>', lambda e: self._update_combobox_values(self.start_combo))

        # 终点选择（添加搜索功能）
        ttk.Label(input_frame, text="终点:", font=('微软雅黑', 11)).grid(row=1, column=0, sticky='w', pady=3)
        self.end_var = tk.StringVar()
        self.end_combo = ttk.Combobox(input_frame,
                                      textvariable=self.end_var,
                                      width=18,
                                      font=('微软雅黑', 10))
        self.end_combo.grid(row=1, column=1, pady=3, padx=(5, 0))
        self.end_combo.bind('<KeyRelease>', lambda e: self._filter_locations(self.end_combo, self.end_var))
        self.end_combo.bind('<FocusIn>', lambda e: self._update_combobox_values(self.end_combo))

        # 出行模式
        ttk.Label(input_frame, text="模式:", font=('微软雅黑', 11)).grid(row=2, column=0, sticky='w', pady=3)
        self.mode_var = tk.StringVar(value="步行")
        self.mode_combo = ttk.Combobox(input_frame, values=["步行", "骑行"],
                                       textvariable=self.mode_var, width=18, state="readonly")
        self.mode_combo.grid(row=2, column=1, pady=3, padx=(5, 0))
        self.mode_combo.bind("<<ComboboxSelected>>", self._switch_mode)

        # 功能按钮区域
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=1, column=0, pady=10, sticky='ew')

        ttk.Button(button_frame, text="定位", command=self._locate).grid(row=0, column=0, padx=2, sticky='ew')
        ttk.Button(button_frame, text="寻路", command=self._find_path).grid(row=0, column=1, padx=2, sticky='ew')
        ttk.Button(button_frame, text="模拟导航", command=self._simulate_nav).grid(row=1, column=0, columnspan=2,
                                                                                   pady=5, sticky='ew')
        ttk.Button(button_frame, text="重置", command=self._reset).grid(row=2, column=0, columnspan=2, sticky='ew')
        
        # 信息显示框
        self.info_box = tk.Text(control_frame, width=28, height=18, wrap=tk.WORD,
                                font=('微软雅黑', 9), padx=8, pady=8)
        self.info_box.grid(row=2, column=0, pady=10, sticky='nsew')

        # 布局权重配置
        control_frame.columnconfigure(0, weight=1)
        input_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        self.original_size = (self.bg_width, self.bg_height)

        self.normal_bg_id = self.map_canvas.create_image(0, 0, image=self.bg_image, anchor=tk.NW)
        self.zoomed_bg_id = self.map_canvas.create_image(0, 0, image=self.zoomed_bg_image,
                                                         anchor=tk.NW, state='hidden')

    def toggle_zoom(self):
        """切换放大模式（双图层最终方案）"""
        if not self.is_zoomed:
            if hasattr(self, 'location_window'):
                self.location_window.destroy()
            self.map_canvas.unbind("<Button-1>")
            # 进入放大模式
            self._switch_bg_layer(show_zoomed=True)
            self._apply_zoom_transform(2.0)
            self._adjust_scrollregion()
            self._enable_pan_handling()
        else:
            self.map_canvas.bind("<Button-1>", self.on_map_click)
            # 退出放大模式
            self._switch_bg_layer(show_zoomed=False)
            self._apply_zoom_transform(0.5)
            self._reset_scrollregion()
            self._disable_pan_handling()
        self.is_zoomed = not self.is_zoomed

    # 新增四个辅助方法（放在 toggle_zoom 下方）
    def _switch_bg_layer(self, show_zoomed):
        """切换背景图层（核心解决残留问题的关键）"""
        self.map_canvas.itemconfig(self.normal_bg_id, state='hidden' if show_zoomed else 'normal')
        self.map_canvas.itemconfig(self.zoomed_bg_id, state='normal' if show_zoomed else 'hidden')

    def _apply_zoom_transform(self, factor):
        """应用缩放变换"""
        self.map_canvas.scale("all", 0, 0, factor, factor)

    def _adjust_scrollregion(self):
        """调整滚动区域"""
        self.map_canvas.config(scrollregion=self.map_canvas.bbox("all"))

    def _reset_scrollregion(self):
        """重置滚动区域"""
        self.map_canvas.config(scrollregion=(0, 0, self.bg_width, self.bg_height))

    def _enable_pan_handling(self):
        """启用拖拽处理"""
        self.map_canvas.bind("<ButtonPress-1>", self.start_pan)
        self.map_canvas.bind("<B1-Motion>", self.do_pan)

    def _disable_pan_handling(self):
        """禁用拖拽处理"""
        self.map_canvas.unbind("<ButtonPress-1>")
        self.map_canvas.unbind("<B1-Motion>")


    def start_pan(self, event):
        """开始拖拽（已调整）"""
        self.map_canvas.scan_mark(event.x, event.y)
        self.pan_start = (event.x, event.y)

    def do_pan(self, event):
        """执行拖拽（已调整）"""
        self.map_canvas.scan_dragto(event.x, event.y, gain=1)
        # 限制移动边界（新增边界检查）
        x0, x1 = self.map_canvas.xview()
        y0, y1 = self.map_canvas.yview()

        # 计算有效滚动区域
        if self.is_zoomed:
            max_x = 2 - (self.original_size[0] / (self.zoom_factor * self.original_size[0]))
            max_y = 2 - (self.original_size[1] / (self.zoom_factor * self.original_size[1]))
            x0 = max(0.0, min(float(x0), max_x))
            y0 = max(0.0, min(float(y0), max_y))
            self.map_canvas.xview_moveto(x0)
            self.map_canvas.yview_moveto(y0)

    def center_view(self):
        """居中显示当前视图"""
        visible_width = 300  # 与放大尺寸一致
        visible_height = 300

        # 计算居中坐标
        center_x = (self.bg_width - visible_width) / (2 * self.bg_width)
        center_y = (self.bg_height - visible_height) / (2 * self.bg_height)

        self.map_canvas.xview_moveto(center_x)
        self.map_canvas.yview_moveto(center_y)

    def _filter_locations(self, combo, var):
        """改进的搜索功能，支持中文输入法"""
        # 获取当前输入内容（使用get()而不是直接访问变量）
        search_term = combo.get().lower()

        # 延迟处理输入法组合
        if combo.index(tk.INSERT) < len(search_term):  # 检测是否处于输入法组合状态
            return

        # 执行过滤
        if search_term == "":
            filtered = self.all_locations
        else:
            filtered = [loc for loc in self.all_locations if search_term in loc.lower()]

        # 更新下拉列表
        combo['values'] = filtered
        combo.icursor(tk.END)  # 保持光标在末尾
        combo.selection_range(0, tk.END)  # 全选文本方便继续输入

    def _update_combobox_values(self, combo):
        # 获取当前输入框内容
        current_input = combo.get()
        # 根据当前输入过滤地点列表
        filtered = [loc for loc in self.all_locations if current_input in loc]
        # 更新下拉列表选项
        combo['values'] = filtered

    def _switch_mode(self, event=None):
        """切换出行模式"""
        mode = self.mode_var.get()
        self.current_graph = self.walk_graph if mode == "步行" else self.bike_graph
        self._show_info(f"已切换为{mode}模式")

    def _draw_bezier(self, start, end, direction):
        """绘制方向敏感的贝塞尔曲线"""
        (x1, y1), (x2, y2) = start, end
        dx, dy = x2 - x1, y2 - y1

        # 计算垂直方向
        if direction == "left":
            perp = (-dy, dx)
        else:  # right
            perp = (dy, -dx)

        # 标准化向量
        length = math.hypot(*perp)
        if length == 0:
            return
        perp = (perp[0] / length * 50, perp[1] / length * 50)  # 控制弯曲程度

        # 计算控制点
        ctrl_x = (x1 + x2) / 2 + perp[0]
        ctrl_y = (y1 + y2) / 2 + perp[1]

        # 绘制三次贝塞尔曲线
        self.map_canvas.create_line(
            x1, y1,
            ctrl_x, ctrl_y,
            x2, y2,
            smooth=True,
            fill="#FF1493",
            width=4,
            tags="path",
            arrow=tk.LAST,
            arrowshape=(16, 20, 6)
        )

    def speak(self, text):
        """异步语音播报"""
        if self.engine is None:
            return

        def _speak():
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                print(f"语音播报失败: {e}")

        threading.Thread(target=_speak).start()

    def _find_path(self):
        """定位标记"""
        self.map_canvas.delete("highlight")
        start = self.start_var.get()
        end = self.end_var.get()

        if start in self.locations:
            x, y = self.locations[start]
            self.map_canvas.create_oval(x - 10, y - 10, x + 10, y + 10, outline="#00FF00", width=3, tags="highlight")
            self.map_canvas.create_text(x, y - 15, text="起点", anchor=tk.S,
                                        font=('微软雅黑', 9, 'bold'), fill="#009900", tags="highlight")

        if end in self.locations:
            x, y = self.locations[end]
            self.map_canvas.create_oval(x - 10, y - 10, x + 10, y + 10, outline="#FF0000", width=3, tags="highlight")
            self.map_canvas.create_text(x, y - 15, text="终点", anchor=tk.S,
                                        font=('微软雅黑', 9, 'bold'), fill="#FF0000", tags="highlight")
        """路径查找与绘制"""
        self.map_canvas.delete("path")
        start = self.start_var.get()
        end = self.end_var.get()

        if not start or not end:
            self._show_info("请先选择起点和终点")
            return

        path = self.a_star(start, end)
        if not path:
            self._show_info("未找到可行路径")
            return

        instructions = self._generate_instructions(path)
        self._show_info(instructions)

        # 转换路径为坐标序列
        coord_path = [self.node_coords[node] for node in path]

        # 绘制路径
        for i in range(len(coord_path) - 1):
            start_point = coord_path[i]
            end_point = coord_path[i + 1]
            self.map_canvas.create_line(
                *start_point, *end_point,
                fill="#FF1493", width=4, tags="path",
                arrow=tk.LAST, arrowshape=(16, 20, 6)
            )
        self.map_canvas.delete("path")
        start = self.start_var.get()
        end = self.end_var.get()

        if not start or not end:
            self._show_info("请先选择起点和终点")
            return

        path = self.a_star(start, end)
        if not path:
            self._show_info("未找到可行路径")
            return

        # 转换路径为坐标序列
        coord_path = [self.node_coords[node] for node in path]

        # 绘制路径
        for i in range(len(coord_path) - 1):
            start_point = coord_path[i]
            end_point = coord_path[i + 1]
            segment = (start_point, end_point)

            if segment in self.special_segments:
                self._draw_bezier(start_point, end_point, self.special_segments[segment])
            else:
                self.map_canvas.create_line(
                    *start_point, *end_point,
                    fill="#FF1493", width=4, tags="path",
                    arrow=tk.LAST, arrowshape=(16, 20, 6)
                )
        # 显示路径信息
        total_dist = sum(self._calc_distance(path[i], path[i + 1]) for i in range(len(path) - 1))
        self._show_info(f"路径规划完成\n总距离: {total_dist * 0.8:.1f}米")  # 假设比例尺转换
        # 在显示路径信息后添加语音播报
        instructions = self._generate_instructions(path)
        self._show_info(instructions)
        self.speak(instructions)  # 新增语音播报

    def a_star(self, start, end):
        """A*寻路算法"""
        open_set = []
        heapq.heappush(open_set, (0, start))
        came_from = {}
        g_score = {node: math.inf for node in self.current_graph}
        g_score[start] = 0
        f_score = {node: math.inf for node in self.current_graph}
        f_score[start] = self._calc_distance(start, end)

        while open_set:
            current = heapq.heappop(open_set)[1]
            if current == end:
                return self._reconstruct_path(came_from, current)

            for neighbor in self.current_graph.get(current, {}):
                tentative_g = g_score[current] + self._calc_distance(current, neighbor)
                if tentative_g < g_score.get(neighbor, math.inf):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + self._calc_distance(neighbor, end)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
        return None

    def _calc_distance(self, a, b):
        """计算两点间欧氏距离"""
        (x1, y1) = self.node_coords.get(a, (0, 0))
        (x2, y2) = self.node_coords.get(b, (0, 0))
        return math.hypot(x1 - x2, y1 - y2)

    def _reconstruct_path(self, came_from, current):
        """重建路径"""
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        return path[::-1]

    def _locate(self):
        """定位标记"""
        self.map_canvas.delete("highlight")
        start = self.start_var.get()
        end = self.end_var.get()

        if start in self.locations:
            x, y = self.locations[start]
            self.map_canvas.create_oval(x - 10, y - 10, x + 10, y + 10, outline="#00FF00", width=3, tags="highlight")
            self.map_canvas.create_text(x, y - 15, text="起点", anchor=tk.S,
                                        font=('微软雅黑', 9, 'bold'), fill="#009900", tags="highlight")

        if end in self.locations:
            x, y = self.locations[end]
            self.map_canvas.create_oval(x - 10, y - 10, x + 10, y + 10, outline="#FF0000", width=3, tags="highlight")
            self.map_canvas.create_text(x, y - 15, text="终点", anchor=tk.S,
                                        font=('微软雅黑', 9, 'bold'), fill="#FF0000", tags="highlight")

    def _simulate_nav(self):
        if self.current_nav:
            self.map_canvas.delete("nav_arrow")
        path = self.a_star(self.start_var.get(), self.end_var.get())  # 只获取一次路径
        if path:
            self.current_nav = iter(path)
            self._create_instruction_window()
            self._show_full_instructions(path)  # 确保调用指引生成
            self._animate_navigation_smooth(path)  # 传递已获得的路径

    def _animate_navigation_smooth(self, path):
        """定位标记"""
        self.map_canvas.delete("highlight")
        start = self.start_var.get()
        end = self.end_var.get()

        if start in self.locations:
            x, y = self.locations[start]
            self.map_canvas.create_oval(x - 10, y - 10, x + 10, y + 10, outline="#00FF00", width=3, tags="highlight")
            self.map_canvas.create_text(x, y - 15, text="起点", anchor=tk.S,
                                        font=('微软雅黑', 9, 'bold'), fill="#009900", tags="highlight")

        if end in self.locations:
            x, y = self.locations[end]
            self.map_canvas.create_oval(x - 10, y - 10, x + 10, y + 10, outline="#FF0000", width=3, tags="highlight")
            self.map_canvas.create_text(x, y - 15, text="终点", anchor=tk.S,
                                        font=('微软雅黑', 9, 'bold'), fill="#FF0000", tags="highlight")
        """路径查找与绘制"""
        self.map_canvas.delete("path")
        start = self.start_var.get()
        end = self.end_var.get()

        if not start or not end:
            self._show_info("请先选择起点和终点")
            return

        path = self.a_star(start, end)
        if not path:
            self._show_info("未找到可行路径")
            return

        # 转换路径为坐标序列
        coord_path = [self.node_coords[node] for node in path]

        # 绘制路径
        for i in range(len(coord_path) - 1):
            start_point = coord_path[i]
            end_point = coord_path[i + 1]
            segment = (start_point, end_point)

            if segment in self.special_segments:
                self._draw_bezier(start_point, end_point, self.special_segments[segment])
            else:
                self.map_canvas.create_line(
                    *start_point, *end_point,
                    fill="#FF1493", width=4, tags="path",
                    arrow=tk.LAST, arrowshape=(16, 20, 6)
                )
        """改进后的平滑导航动画"""
        path = self.a_star(self.start_var.get(), self.end_var.get())
        if not path: return

        # 生成完整路径点序列
        all_points = []
        for i in range(len(path) - 1):
            start = self.node_coords[path[i]]
            end = self.node_coords[path[i + 1]]

            # 获取当前路段方向提示
            dx = end[0] - start[0]
            dy = start[1] - end[1]  # Y轴翻转
            angle = math.degrees(math.atan2(dy, dx))
            direction = self._get_direction(start_point, end_point)
            distance = self._calc_distance(path[i], path[i + 1]) * 0.8
            # self._update_instruction(f"向{direction}移动{distance:.1f}米")

            # 生成移动点序列（自动处理曲线）
            all_points.extend(self._get_segment_points(start, end))

        # 执行动画
        for x, y in all_points:
            self.map_canvas.delete("nav_arrow")
            self.map_canvas.create_polygon(
                x - 12, y - 20, x + 12, y - 20, x, y,
                fill="#FF4500", outline="white", tags="nav_arrow"
            )
            self.root.update()
            self.root.after(30)

    def _get_direction(self, start, end):
        """计算两点间方向（八方向）"""
        dx = end[0] - start[0]
        dy = start[1] - end[1]  # 因画布坐标系Y轴向下，故取反

        angle = math.degrees(math.atan2(dy, dx))
        angle = angle % 360
        directions = [
            (337.5, 360, "东"), (0, 22.5, "东"),
            (22.5, 67.5, "东北"), (67.5, 112.5, "北"),
            (112.5, 157.5, "西北"), (157.5, 202.5, "西"),
            (202.5, 247.5, "西南"), (247.5, 292.5, "南"),
            (292.5, 337.5, "东南")
        ]

        for min_a, max_a, name in directions:
            if angle >= min_a and angle < max_a:
                return name
        return "东"

    def _generate_instructions(self, path):
        """生成导航指引文本"""
        instructions = []
        total_dist = 0

        for i in range(len(path) - 1):
            start_node = path[i]
            end_node = path[i + 1]

            # 获取实际坐标
            start_pos = self.node_coords[start_node]
            end_pos = self.node_coords[end_node]

            # 计算方向和距离
            direction = self._get_direction(start_pos, end_pos)
            distance = self._calc_distance(start_node, end_node) * 0.8  # 假设比例尺转换
            total_dist += distance

            instructions.append(f"第{i + 1}步：向{direction}移动{distance:.1f}米")

        instructions.append(f"\n到达终点，总里程：{total_dist:.1f}米")
        return "\n".join(instructions)

    def _create_instruction_window(self):
        """创建方向提示窗口"""
        if self.instruction_window:
            self.instruction_window.destroy()

        self.instruction_window = tk.Toplevel(self.root)
        self.instruction_window.title("导航提示")
        self.instruction_label = tk.Label(
            self.instruction_window,
            font=('微软雅黑', 12),
            padx=20,
            pady=10
        )
        self.instruction_label.pack()

    def _get_segment_points(self, start, end):
        """获取路段点序列（自动判断曲线）"""
        if (start, end) in self.special_segments:
            control = self._get_bezier_control(start, end)
            return self._bezier_curve(start, control, end, steps=20)
        return self._linear_points(start, end)

    def _bezier_curve(self, start, control, end, steps=20):
        """生成二次贝塞尔曲线点集"""
        return [
            (
                (1 - t) ** 2 * start[0] + 2 * (1 - t) * t * control[0] + t ** 2 * end[0],
                (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * control[1] + t ** 2 * end[1]
            ) for t in (i / steps for i in range(steps + 1))
        ]

    def _linear_points(self, start, end, steps=20):
        """生成直线路径的插值点集合"""
        (x1, y1), (x2, y2) = start, end
        return [
            (
                x1 + (x2 - x1) * t / steps,
                y1 + (y2 - y1) * t / steps
            )
            for t in range(steps + 1)
        ]

    def _get_bezier_control(self, start, end):
        """贝塞尔曲线控制点计算（新增）"""
        (x1, y1), (x2, y2) = start, end
        dx, dy = x2 - x1, y2 - y1

        # 复用原绘制逻辑的方向判断
        direction = self.special_segments.get((start, end), "right")
        perp = (-dy, dx) if direction == "left" else (dy, -dx)

        # 标准化向量（保持50px弯曲度）
        length = math.hypot(*perp)
        perp = (perp[0] / length * 50, perp[1] / length * 50)
        return ((x1 + x2) / 2 + perp[0], (y1 + y2) / 2 + perp[1])

    def _bezier_curve(self, start, control, end, steps=20):
        """贝塞尔曲线点生成（新增）"""
        return [
            (
                (1 - t) ** 2 * start[0] + 2 * (1 - t) * t * control[0] + t ** 2 * end[0],
                (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * control[1] + t ** 2 * end[1]
            ) for t in (i / steps for i in range(steps + 1))
        ]

    def _show_full_instructions(self, path):
        """生成全程路线指引"""
        if hasattr(self, 'instruction_label'):
            self.instruction_label.config(text="")
        instructions = []
        total_dist = 0

        for i in range(len(path) - 1):
            start_node = path[i]
            end_node = path[i + 1]

            # 获取实际坐标
            start_pos = self.node_coords[start_node]
            end_pos = self.node_coords[end_node]

            # 计算方向和距离
            direction = self._get_direction(start_pos, end_pos)  # 正确调用
            distance = self._calc_distance(start_node, end_node) * 0.8
            total_dist += distance

            instructions.append(f"第{i + 1}步：向{direction}移动{distance:.1f}米")

        full_text = "\n".join(instructions)
        self.instruction_label.config(text=full_text)
        self.instruction_label.pack()
        # 在生成指引后添加语音播报
        full_text = "\n".join(instructions)
        self.instruction_label.config(text=full_text)
        self.speak(full_text)  # 新增语音播报

    def _update_instruction(self, text):
        """更新提示内容（新增此方法）"""
        if hasattr(self, 'instruction_label'):
            self.instruction_label.config(text=text)
            self.instruction_window.update()

    def _create_instruction_window(self):
        """创建/复用指引窗口"""
        # 检查窗口是否有效
        if not hasattr(self, 'instruction_window') or \
                not self.instruction_window or \
                not self.instruction_window.winfo_exists():

            # 创建新窗口
            self.instruction_window = tk.Toplevel(self.root)
            self.instruction_window.title("导航指引")
            self.instruction_label = tk.Label(
                self.instruction_window,
                font=('微软雅黑', 10),
                padx=15,
                pady=15,
                justify=tk.LEFT
            )
            self.instruction_label.pack()
        else:
            # 已有窗口则提到最前
            self.instruction_window.lift()

    def _reset(self):
        """重置所有状态"""
        self.map_canvas.delete("path")
        self.map_canvas.delete("highlight")
        self.map_canvas.delete("nav_arrow")
        self.start_var.set('')
        self.end_var.set('')
        self.info_box.delete(1.0, tk.END)

    def _show_info(self, message):
        """显示信息"""
        self.info_box.delete(1.0, tk.END)
        self.info_box.insert(tk.END, message + "\n")

    def _validate_data(self):
        """验证数据完整性"""
        # 检查所有节点坐标是否存在
        missing_nodes = [n for n in self.current_graph if n not in self.node_coords]
        if missing_nodes:
            raise ValueError(f"缺失节点坐标: {missing_nodes}")

        # 检查邻接表的双向连接
        for node, neighbors in self.current_graph.items():
            for neighbor in neighbors:
                if node not in self.current_graph.get(neighbor, {}):
                    print(f"警告: 单向连接 {node} -> {neighbor}")

    def _draw_base_map(self):
        """绘制基础地图元素"""
        # 绘制所有连接线
        for src, dests in self.current_graph.items():
            src_coord = self.node_coords.get(src)
            if not src_coord: continue
            for dest in dests:
                dest_coord = self.node_coords.get(dest)
                if dest_coord:
                    self.map_canvas.create_line(*src_coord, *dest_coord, fill="#e0e0e0", width=1.5, tags="base_line")

        # 绘制地点标记
        for name, (x, y) in self.locations.items():
            self.map_canvas.create_rectangle(x - 5, y - 5, x + 5, y + 5, fill="#1E90FF", outline="", tags="node")
            self.map_canvas.create_text(x + 12, y, text=name, anchor=tk.W, font=('微软雅黑', 8), tags="label")


if __name__ == "__main__":
    root = tk.Tk()
    app = CampusNavigator(root)
    root.mainloop()