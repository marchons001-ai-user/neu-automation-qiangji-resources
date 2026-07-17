import pybullet as p
import numpy as np
import math
import tkinter as tk
from tkinter import ttk, messagebox
from scipy.optimize import fsolve


class DeltaSimulator:
    def __init__(self):
        self.R = 2.9  # 静平台半径
        self.r = 3.6  # 动平台半径
        self.lb = 13.5  # 主动臂长度
        self.la = 30  # 从动臂长度
        self.alpha = np.array([0, 2 * math.pi / 3, 4 * math.pi / 3])

        # 关节物理限位 (主动臂与水平面夹角，单位：度)
        self.theta_limits = (-25.0, 25.0)

        # 静平台铰链点 (Z=0 为基准面)
        self.base_joints = np.array([
            [self.R * math.cos(a), self.R * math.sin(a), 0.0] for a in self.alpha
        ])

        # 初始化 PyBullet
        p.connect(p.GUI)
        p.resetSimulation()
        p.setGravity(0, 0, 0)
        p.setRealTimeSimulation(0)
        p.resetDebugVisualizerCamera(cameraDistance=120, cameraYaw=45, cameraPitch=-30,
                                     cameraTargetPosition=[0, 0, -40])

    def inverse_kinematics(self, x, y, z):
        """逆运动学：输入末端坐标，返回三个关节角度。包含限位检查。"""
        f = self.R - self.r
        dx = [x - f * math.cos(a) for a in self.alpha]
        dy = [y - f * math.sin(a) for a in self.alpha]

        thetas = []
        for i in range(3):
            # 约束方程: (x-Bx)^2 + (y-By)^2 + (z-0)^2 = la^2
            # 展开后整理为 A = B*cosθ + C*sinθ
            A = dx[i] ** 2 + dy[i] ** 2 + z ** 2 + self.lb ** 2 - self.la ** 2
            B = 2 * self.lb * dx[i]
            C = 2 * self.lb * z

            denom = math.hypot(B, C)
            if abs(A) > denom + 1e-5:
                return None, f"目标点超出几何可达工作空间 (腿{i + 1})"

            phi = math.atan2(C, B)
            psi = math.acos(np.clip(A / denom, -1.0, 1.0))

            # Delta机器人有两个可能的解：phi - psi 和 phi + psi
            # 我们需要选择肘部向下的构型（通常 theta 为负值）
            th1 = phi - psi
            th2 = phi + psi

            # 选择更接近 0 的解（通常在 -90 到 0 之间）
            if -90 <= math.degrees(th1) <= 0:
                th = th1
            elif -90 <= math.degrees(th2) <= 0:
                th = th2
            else:
                # 如果两个解都不在理想范围，选择绝对值较小的
                th = th1 if abs(th1) < abs(th2) else th2

            thetas.append(math.degrees(th))

        # 检查所有关节角是否在物理限位范围内
        t_min, t_max = self.theta_limits
        for i, t in enumerate(thetas):
            if not (t_min <= t <= t_max):
                return None, f"关节角 θ{i + 1}={t:.1f}° 超出物理限位 [{t_min}, {t_max}]"

        return thetas, "逆解求解成功"

    def forward_kinematics(self, th1, th2, th3):
        """正运动学：输入三个角度，返回末端坐标"""
        thetas_rad = np.radians([th1, th2, th3])

        def residuals(vars):
            x, y, z = vars
            res = []
            for i in range(3):
                dx = x - (self.R - self.r) * math.cos(self.alpha[i])
                dy = y - (self.R - self.r) * math.sin(self.alpha[i])
                A = dx ** 2 + dy ** 2 + z ** 2 + self.lb ** 2 - self.la ** 2
                B = 2 * self.lb * dx
                C = 2 * self.lb * z
                res.append(B * math.cos(thetas_rad[i]) + C * math.sin(thetas_rad[i]) - A)
            return res

        sol = fsolve(residuals, [0.0, 0.0, -60.0], full_output=False)
        return sol, "正解求解成功"

    def visualize(self, x, y, z, thetas):
        p.removeAllUserDebugItems()
        line_color = [0.2, 0.6, 1.0]
        text_color = [1.0, 1.0, 1.0]

        # 1. 静平台 (Z=0)
        for i in range(3):
            p.addUserDebugLine(self.base_joints[i], self.base_joints[(i + 1) % 3], line_color, lineWidth=2)

        # 2. 各腿
        for i in range(3):
            th_rad = math.radians(thetas[i])
            u_dir = np.array([math.cos(self.alpha[i]), math.sin(self.alpha[i]), 0.0])
            elbow_pos = self.base_joints[i] + self.lb * (
                        math.cos(th_rad) * u_dir + math.sin(th_rad) * np.array([0.0, 0.0, 1.0]))

            moving_joint = np.array([
                x + self.r * math.cos(self.alpha[i]),
                y + self.r * math.sin(self.alpha[i]),
                z
            ])

            p.addUserDebugLine(self.base_joints[i], elbow_pos, [0.2, 0.9, 0.3], lineWidth=3)
            p.addUserDebugLine(elbow_pos, moving_joint, [0.9, 0.3, 0.2], lineWidth=3)

            mid_arm = (self.base_joints[i] + elbow_pos) / 2
            p.addUserDebugText(f"θ{i + 1}={thetas[i]:.1f}°", mid_arm + [0, 0, 3], text_color, textSize=1.2)

        # 3. 动平台
        moving_joints = [
            [x + self.r * math.cos(a), y + self.r * math.sin(a), z] for a in self.alpha
        ]
        for i in range(3):
            p.addUserDebugLine(moving_joints[i], moving_joints[(i + 1) % 3], line_color, lineWidth=2)

        # 4. 坐标系
        base_origin = np.array([0.0, 0.0, 0.0])
        axis_len = 12
        p.addUserDebugLine(base_origin, base_origin + [axis_len, 0, 0], [1, 0, 0], lineWidth=2)
        p.addUserDebugLine(base_origin, base_origin + [0, axis_len, 0], [0, 1, 0], lineWidth=2)
        p.addUserDebugLine(base_origin, base_origin + [0, 0, axis_len], [0, 0, 1], lineWidth=2)
        p.addUserDebugText("Base(O)", base_origin + [-3, 0, 2], text_color, textSize=1.0)

        ee_pos = np.array([x, y, z])
        p.addUserDebugLine(ee_pos, ee_pos + [axis_len * 0.7, 0, 0], [1, 0, 0], lineWidth=2)
        p.addUserDebugLine(ee_pos, ee_pos + [0, axis_len * 0.7, 0], [0, 1, 0], lineWidth=2)
        p.addUserDebugLine(ee_pos, ee_pos + [0, 0, axis_len * 0.7], [0, 0, 1], lineWidth=2)
        p.addUserDebugText(f"EE({x:.1f},{y:.1f},{z:.1f})", ee_pos + [0, 0, 5], text_color, textSize=1.2)

        p.stepSimulation()

    def clear_robot(self):
        """清除机器人可视化"""
        p.removeAllUserDebugItems()


class DeltaGUI:
    def __init__(self):
        self.sim = DeltaSimulator()
        self.root = tk.Tk()
        self.root.title("3-DOF Delta Robot 仿真交互")
        self.root.geometry("500x700")
        self.scales = []
        self.entries = {}
        self.is_updating = False

        self.setup_scrollable_ui()

    def setup_scrollable_ui(self):
        self.canvas = tk.Canvas(self.root, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.setup_ui_content(self.scrollable_frame)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def setup_ui_content(self, parent):
        pad_opts = {'padx': 10, 'pady': 5}

        tk.Label(parent, text="求解模式:", font=('Arial', 10, 'bold')).pack(**pad_opts)
        self.mode_var = tk.StringVar(value="逆运动学 (输入XYZ求角度)")
        mode_menu = ttk.Combobox(parent, textvariable=self.mode_var, state="readonly", width=32)
        mode_menu['values'] = ["逆运动学 (输入XYZ求角度)", "正运动学 (输入角度求XYZ)"]
        mode_menu.pack(**pad_opts)
        mode_menu.bind("<<ComboboxSelected>>", lambda e: self.rebuild_scales())

        tk.Label(parent, text="⚠️ 建议范围 (mm/°):", fg="gray", font=('Arial', 9)).pack(**pad_opts)
        self.range_label = tk.Label(parent, text=f"X/Y: [-20, 20] | Z: [-90, -10] | 关节限位: {self.sim.theta_limits}",
                                    font=('Arial', 9))
        self.range_label.pack()

        self.scale_frame = tk.LabelFrame(parent, text="连续调节滑块", font=('Arial', 10, 'bold'))
        self.scale_frame.pack(fill=tk.X, padx=10, pady=5)
        self.rebuild_scales()

        self.entry_frame = tk.LabelFrame(parent, text="精确输入", font=('Arial', 10, 'bold'))
        self.entry_frame.pack(fill=tk.X, padx=10, pady=5)
        for label in ["X", "Y", "Z", "θ1", "θ2", "θ3"]:
            frame = tk.Frame(self.entry_frame)
            frame.pack(fill=tk.X, padx=5, pady=2)
            tk.Label(frame, text=f"{label}: ", width=6, anchor=tk.E).pack(side=tk.LEFT)
            entry = tk.Entry(frame, width=10)
            entry.pack(side=tk.LEFT, padx=5)
            self.entries[label] = entry

        self.entries["X"].insert(0, "0");
        self.entries["Y"].insert(0, "0");
        self.entries["Z"].insert(0, "-60")
        self.entries["θ1"].insert(0, "-30");
        self.entries["θ2"].insert(0, "-30");
        self.entries["θ3"].insert(0, "-30")

        tk.Button(parent, text="🔄 手动求解 (使用输入框)", bg="#2196F3", fg="white", font=('Arial', 10, 'bold'),
                  command=self.on_solve).pack(fill=tk.X, padx=20, pady=10)

        self.status_frame = tk.Frame(parent, bg="#f5f5f5", relief=tk.SUNKEN, bd=2)
        self.status_frame.pack(fill=tk.X, padx=10, pady=5)
        self.lbl_xyz = tk.Label(self.status_frame, text="末端坐标 (mm):  --", bg="#f5f5f5", font=('Consolas', 10),
                                anchor=tk.W)
        self.lbl_xyz.pack(fill=tk.X, padx=5, pady=3)
        self.lbl_thetas = tk.Label(self.status_frame, text="关节角度 (°):  --", bg="#f5f5f5", font=('Consolas', 10),
                                   anchor=tk.W)
        self.lbl_thetas.pack(fill=tk.X, padx=5, pady=3)
        self.lbl_msg = tk.Label(self.status_frame, text="状态: 等待操作...", bg="#f5f5f5", fg="blue", font=('Arial', 9))
        self.lbl_msg.pack(fill=tk.X, padx=5, pady=3)

    def rebuild_scales(self):
        for widget in self.scale_frame.winfo_children():
            widget.destroy()
        self.scales = []

        is_inv = "逆" in self.mode_var.get()
        labels = ["X", "Y", "Z"] if is_inv else ["θ1", "θ2", "θ3"]
        ranges = [(-20, 20), (-20, 20), (-90, -10)] if is_inv else [(-90, 10), (-90, 10), (-90, 10)]
        self.range_label.config(
            text=f"X/Y: [-20, 20] | Z: [-90, -10] | 关节限位: {self.sim.theta_limits}" if is_inv else f"关节限位: {self.sim.theta_limits}")

        for i, lbl in enumerate(labels):
            frm = tk.Frame(self.scale_frame)
            frm.pack(fill=tk.X, padx=5, pady=3)
            tk.Label(frm, text=f"{lbl}: ", width=6, anchor=tk.E).pack(side=tk.LEFT)
            sc = tk.Scale(frm, from_=ranges[i][0], to=ranges[i][1], orient=tk.HORIZONTAL, length=280, resolution=0.5)
            sc.pack(side=tk.LEFT, fill=tk.X, expand=True)

            if lbl == "Z":
                sc.set(-60)
            else:
                sc.set(0 if is_inv else -30)

            sc.config(command=lambda val, lb=lbl: self.on_scale_drag(val, lb))
            self.scales.append(sc)

    def on_scale_drag(self, val, label):
        if self.is_updating: return
        self.is_updating = True
        try:
            self.entries[label].delete(0, tk.END)
            self.entries[label].insert(0, str(float(val)))
            self.execute_solve()
        except Exception as e:
            self.lbl_msg.config(text=f"错误: {str(e)}", fg="red")
        finally:
            self.is_updating = False

    def on_solve(self):
        try:
            self.execute_solve()
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")

    def execute_solve(self):
        try:
            vals = {k: float(v.get()) for k, v in self.entries.items()}
            is_inv = "逆" in self.mode_var.get()

            if is_inv:
                thetas, msg = self.sim.inverse_kinematics(vals["X"], vals["Y"], vals["Z"])
                if thetas is None:
                    # 【关键修改】逆解失败时，清除机器人可视化
                    self.sim.clear_robot()
                    self.update_display(vals["X"], vals["Y"], vals["Z"], 0, 0, 0, msg)
                    return
                self.sim.visualize(vals["X"], vals["Y"], vals["Z"], thetas)
                self.update_display(vals["X"], vals["Y"], vals["Z"], thetas[0], thetas[1], thetas[2], msg)
            else:
                xyz, msg = self.sim.forward_kinematics(vals["θ1"], vals["θ2"], vals["θ3"])
                self.sim.visualize(xyz[0], xyz[1], xyz[2], [vals["θ1"], vals["θ2"], vals["θ3"]])
                self.update_display(xyz[0], xyz[1], xyz[2], vals["θ1"], vals["θ2"], vals["θ3"], msg)
        except Exception as e:
            self.lbl_msg.config(text=f"求解异常: {str(e)}", fg="red")

    def update_display(self, x, y, z, t1, t2, t3, msg):
        self.lbl_xyz.config(text=f"末端坐标 (mm):  X={x:.2f}  Y={y:.2f}  Z={z:.2f}")
        self.lbl_thetas.config(text=f"关节角度 (°):  θ1={t1:.2f}  θ2={t2:.2f}  θ3={t3:.2f}")
        color = "green" if "成功" in msg else "red"
        self.lbl_msg.config(text=f"状态: {msg}", fg=color)

    def run(self):
        self.update_pybullet_loop()
        self.root.mainloop()

    def update_pybullet_loop(self):
        if p.isConnected():
            p.stepSimulation()
        self.root.after(16, self.update_pybullet_loop)


if __name__ == "__main__":
    app = DeltaGUI()
    app.run()