import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from system_simulation import CascadeControlSystem
import matplotlib.pyplot as plt
import platform
import itertools
import time

# 定义全局样式常量
FONT_HEADER = ("Microsoft YaHei", 11, "bold")
FONT_LABEL = ("Microsoft YaHei", 9)
FONT_SMALL = ("Arial", 8)
COLOR_PRIMARY = "#007acc"
COLOR_BG_PLOT = "#f0f0f0"


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("精馏塔底温度串级控制系统仿真工作台 (Pro Engineer Edition)")
        self.root.geometry("1600x950")

        # --- 1. 初始化系统与配置 ---
        self._configure_fonts()
        self._init_styles()

        # 仿真核心对象 (初始步长设为0.5)
        self.system = CascadeControlSystem(dt=0.5)

        # 状态变量
        self.auto_refresh = tk.BooleanVar(value=True)  # 是否参数改变自动刷新
        self.sim_duration = tk.DoubleVar(value=500.0)  # 仿真总时长
        self.sim_dt = tk.DoubleVar(value=0.5)  # 仿真步长

        # 优化器状态
        self.opt_generator = None
        self.is_optimizing = False

        # --- 2. 构建界面布局 ---
        self._init_layout()

        # --- 3. 初始化绘图引擎 ---
        self._init_plot_engine()

        # --- 4. 首次运行 ---
        self.root.after(500, self.run_full_simulation)

    def _configure_fonts(self):
        """配置Matplotlib字体以支持中文显示，适配Windows/Mac/Linux"""
        system_name = platform.system()
        font_candidates = ['Microsoft YaHei', 'SimHei', 'Heiti TC', 'WenQuanYi Micro Hei', 'DejaVu Sans']
        found_font = ['Microsoft YaHei']  # Default fallback

        if system_name == "Windows":
            found_font = ['Microsoft YaHei', 'SimHei']
        elif system_name == "Darwin":
            found_font = ['Arial Unicode MS', 'Heiti TC']
        else:
            found_font = ['WenQuanYi Micro Hei', 'DejaVu Sans']

        plt.rcParams['font.sans-serif'] = found_font
        plt.rcParams['axes.unicode_minus'] = False

    def _init_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TLabel", font=FONT_LABEL)
        style.configure("TButton", font=FONT_LABEL)
        style.configure("Header.TLabel", font=FONT_HEADER, foreground="#333")
        style.configure("Small.TLabel", font=FONT_SMALL, foreground="gray")
        style.configure("Group.TLabelframe.Label", font=("Microsoft YaHei", 9, "bold"), foreground=COLOR_PRIMARY)

    def _init_layout(self):
        """构建主界面左右分栏布局"""
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # === 左侧控制面板 ===
        self.sidebar = ttk.Frame(main_paned, width=450)
        main_paned.add(self.sidebar, weight=0)
        self.sidebar.pack_propagate(False)

        self._build_sidebar_header(self.sidebar)
        self._build_notebook_tabs(self.sidebar)
        self._build_bottom_controls(self.sidebar)

        # === 右侧绘图区 ===
        self.plot_container = ttk.Frame(main_paned)
        main_paned.add(self.plot_container, weight=1)

    def _build_sidebar_header(self, parent):
        f = ttk.Frame(parent, padding="10 10 10 5")
        f.pack(fill=tk.X)
        ttk.Label(f, text="控制系统设计与仿真", style="Header.TLabel").pack(anchor="w")
        ttk.Label(f, text="Target: 塔底温度 (Temperature) | Slave: 蒸汽流量 (Flow)", style="Small.TLabel").pack(
            anchor="w")
        ttk.Separator(f, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)

    def _build_notebook_tabs(self, parent):
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)

        # Tab 1: 手动整定
        self._init_manual_tab()
        # Tab 2: 智能整定
        self._init_auto_tab()

    # =========================================================================
    # Tab 1: 手动整定 (Manual Tuning)
    # =========================================================================
    def _init_manual_tab(self):
        tab = ttk.Frame(self.notebook, padding=5)
        self.notebook.add(tab, text="手动整定 / 验证")

        # 1.1 系统全局设置
        cfg_frame = ttk.LabelFrame(tab, text="仿真环境设置", style="Group.TLabelframe", padding=5)
        cfg_frame.pack(fill=tk.X, pady=5)

        f_row = ttk.Frame(cfg_frame)
        f_row.pack(fill=tk.X)
        ttk.Label(f_row, text="总时长(s):").pack(side=tk.LEFT)
        ttk.Entry(f_row, textvariable=self.sim_duration, width=8).pack(side=tk.LEFT, padx=5)
        ttk.Label(f_row, text="步长(s):").pack(side=tk.LEFT)
        ttk.Entry(f_row, textvariable=self.sim_dt, width=8).pack(side=tk.LEFT, padx=5)

        # 自动刷新开关
        ttk.Checkbutton(cfg_frame, text="参数调整时自动刷新", variable=self.auto_refresh).pack(anchor="w", pady=2)

        # 1.2 副回路
        s_frame = ttk.LabelFrame(tab, text="1. 副回路 (流量环 FC)", style="Group.TLabelframe", padding=5)
        s_frame.pack(fill=tk.X, pady=5)
        self.s_kp = self._create_slider(s_frame, "Kp (比例)", 0, 10, 2.0)
        self.s_ki = self._create_slider(s_frame, "Ki (积分)", 0, 5.0, 0.5)
        self.s_kd = self._create_slider(s_frame, "Kd (微分)", 0, 10, 0.0)

        # 1.3 主回路
        m_frame = ttk.LabelFrame(tab, text="2. 主回路 (温度环 TC)", style="Group.TLabelframe", padding=5)
        m_frame.pack(fill=tk.X, pady=5)
        self.m_kp = self._create_slider(m_frame, "Kp (比例)", 0, 20, 3.5)
        self.m_ki = self._create_slider(m_frame, "Ki (积分)", 0, 0.5, 0.02)
        self.m_kd = self._create_slider(m_frame, "Kd (微分)", 0, 100, 20.0)

        # 1.4 干扰与设定
        op_frame = ttk.LabelFrame(tab, text="工况模拟 (设定值 & 干扰)", style="Group.TLabelframe", padding=5)
        op_frame.pack(fill=tk.X, pady=5)
        self.sp_temp_scale = self._create_slider(op_frame, "温度设定值 (SP)", 0, 100, 50)
        ttk.Separator(op_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        self.dist_flow_scale = self._create_slider(op_frame, "D1: 蒸汽压力扰动", -20, 20, 0)
        self.dist_temp_scale = self._create_slider(op_frame, "D2: 进料负荷扰动", -20, 20, 0)

    # =========================================================================
    # Tab 2: 智能整定 (Auto Tuning)
    # =========================================================================
    def _init_auto_tab(self):
        tab = ttk.Frame(self.notebook, padding=5)
        self.notebook.add(tab, text="智能整定 (Grid Search)")

        ttk.Label(tab, text="两阶段网格搜索算法 (Optimization)", font=("Arial", 9, "bold")).pack(anchor="w")
        ttk.Label(tab, text="针对 IAE/ITAE 指标自动寻优。耗时较长，请耐心等待。", style="Small.TLabel").pack(anchor="w",
                                                                                                          pady=(0, 5))

        # 搜索空间配置
        s_conf = ttk.LabelFrame(tab, text="Step 1: 副环搜索范围", style="Group.TLabelframe", padding=5)
        s_conf.pack(fill=tk.X, pady=2)
        self.entry_s_kp = self._create_range_input(s_conf, "Kp", "0.5", "5.0", "0.5")
        self.entry_s_ki = self._create_range_input(s_conf, "Ki", "0.1", "2.0", "0.3")

        m_conf = ttk.LabelFrame(tab, text="Step 2: 主环搜索范围", style="Group.TLabelframe", padding=5)
        m_conf.pack(fill=tk.X, pady=2)
        self.entry_m_kp = self._create_range_input(m_conf, "Kp", "1.0", "10.0", "1.0")
        self.entry_m_ki = self._create_range_input(m_conf, "Ki", "0.01", "0.2", "0.02")
        self.entry_m_kd = self._create_range_input(m_conf, "Kd", "0.0", "50.0", "10.0")

        # 按钮与进度
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, pady=5)
        self.btn_auto_tune = ttk.Button(btn_frame, text="⚡ 启动智能整定", command=self.start_auto_tune_thread)
        self.btn_auto_tune.pack(fill=tk.X)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(tab, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=2)

        # 日志
        log_frame = ttk.LabelFrame(tab, text="整定日志", padding=2)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=2)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, font=("Consolas", 8), state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _build_bottom_controls(self, parent):
        """左侧底部的公共操作按钮"""
        f = ttk.Frame(parent, padding="10")
        f.pack(fill=tk.X, side=tk.BOTTOM)

        # 突出的执行按钮
        self.btn_run = ttk.Button(f, text="▶ 执行仿真 (Run)", command=self.run_full_simulation)
        self.btn_run.pack(fill=tk.X, pady=5)

        btn_grid = ttk.Frame(f)
        btn_grid.pack(fill=tk.X)
        ttk.Button(btn_grid, text="↺ 重置", command=self.reset_ui).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(btn_grid, text="💾 导出数据", command=self.save_data).pack(side=tk.LEFT, fill=tk.X, expand=True,
                                                                             padx=2)

        # 性能指标面板
        m_frame = ttk.Frame(f, padding="5", relief=tk.RIDGE)
        m_frame.pack(fill=tk.X, pady=10)
        ttk.Label(m_frame, text="性能指标 (Performance)", font=("Arial", 8, "bold")).pack(anchor="w")
        self.lbl_iae = ttk.Label(m_frame, text="IAE: ---", foreground="#d9534f", font=("Consolas", 10, "bold"))
        self.lbl_iae.pack(anchor="w")
        self.lbl_itae = ttk.Label(m_frame, text="ITAE: ---", foreground="#d9534f", font=("Consolas", 10, "bold"))
        self.lbl_itae.pack(anchor="w")

    # =========================================================================
    # 绘图引擎 (Plot Engine) - Matplotlib Integration
    # =========================================================================
    def _init_plot_engine(self):
        """初始化绘图区域，包含 Toolbar"""
        self.fig = Figure(figsize=(10, 10), dpi=100)
        # 调整布局，留出标题空间
        self.fig.subplots_adjust(left=0.08, right=0.95, top=0.94, bottom=0.06, hspace=0.35)

        # 1. 塔底温度 (主控)
        self.ax1 = self.fig.add_subplot(311)
        self.ax1.set_title("主回路: 塔底温度 (Temperature PV)", fontsize=10, fontweight='bold')
        self.ax1.set_ylabel("温度 (℃)")
        self.ax1.grid(True, linestyle='--', alpha=0.5)
        self.line_sp_temp, = self.ax1.plot([], [], 'r--', label='设定值 (SP)', linewidth=1.5)
        self.line_pv_temp, = self.ax1.plot([], [], 'b-', label='测量值 (PV)', linewidth=1.5)
        self.ax1.legend(loc='upper right', fontsize='small', frameon=True)

        # 2. 蒸汽流量 (副控)
        self.ax2 = self.fig.add_subplot(312)
        self.ax2.set_title("副回路: 蒸汽流量 (Steam Flow)", fontsize=10, fontweight='bold')
        self.ax2.set_ylabel("流量 (kg/h)")
        self.ax2.grid(True, linestyle='--', alpha=0.5)
        self.line_sp_flow, = self.ax2.plot([], [], 'g--', label='串级给定 (Cascade SP)', linewidth=1.5)
        self.line_pv_flow, = self.ax2.plot([], [], 'k-', label='流量测量 (Flow PV)', linewidth=1.5)
        self.ax2.legend(loc='upper right', fontsize='small', frameon=True)

        # 3. 阀门开度
        self.ax3 = self.fig.add_subplot(313)
        self.ax3.set_title("执行器: 调节阀开度 (Valve Position)", fontsize=10, fontweight='bold')
        self.ax3.set_ylabel("开度 (%)")
        self.ax3.set_xlabel("时间 (Time s)")
        self.ax3.set_ylim(-5, 105)
        self.ax3.grid(True, linestyle='--', alpha=0.5)
        self.line_valve, = self.ax3.plot([], [], 'm-', linewidth=1.5)

        # Canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_container)
        self.canvas.draw()

        # --- 关键：添加 Matplotlib 导航工具栏 ---
        # 这就是实现“拖动坐标轴”、“缩放”的核心组件
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.plot_container)
        self.toolbar.update()

        # 布局
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    # =========================================================================
    # 核心仿真逻辑 (High Efficiency Instant Simulation)
    # =========================================================================
    def run_full_simulation(self, *args):
        """
        瞬间完成整个仿真周期的计算，并更新图表。
        替代了低效的逐帧动画。
        """
        if self.is_optimizing: return

        # 1. 获取仿真配置
        try:
            total_time = float(self.sim_duration.get())
            step_size = float(self.sim_dt.get())
            if step_size <= 0: raise ValueError
        except ValueError:
            return  # Ignore invalid input during typing

        # 2. 重置并更新系统参数
        self.system.reset()  # 清空历史数据
        self.system.dt = step_size  # 更新步长
        self.system.master_pid.sample_time = step_size
        self.system.slave_pid.sample_time = step_size

        # 设置PID和工况
        self.system.setpoint_temp = self.sp_temp_scale.get()
        self.system.disturbance_flow = self.dist_flow_scale.get()
        self.system.disturbance_temp = self.dist_temp_scale.get()

        self.system.set_pid_params(
            (self.m_kp.get(), self.m_ki.get(), self.m_kd.get()),
            (self.s_kp.get(), self.s_ki.get(), self.s_kd.get())
        )

        # 3. 极速计算循环
        # Python 处理几千次简单的加减乘除非常快，通常 < 50ms
        steps = int(total_time / step_size)

        # 预分配/局部变量优化速度 (虽然对于几千点来说差异不大，但习惯很好)
        for _ in range(steps):
            self.system.step()

        # 4. 一次性刷新图表
        self._update_plots_static()

        # 5. 更新指标
        metrics = self.system.get_metrics()
        self.lbl_iae.config(text=f"IAE: {metrics['m_iae']:.2f}")
        self.lbl_itae.config(text=f"ITAE: {metrics['m_itae']:.2f}")

    def _update_plots_static(self):
        """静态更新所有曲线"""
        history = self.system.history
        times = history['time']

        # 检查是否有数据
        if not times: return

        # 更新线条数据
        self.line_sp_temp.set_data(times, history['sp_temp'])
        self.line_pv_temp.set_data(times, history['pv_temp'])

        self.line_sp_flow.set_data(times, history['sp_flow'])
        self.line_pv_flow.set_data(times, history['pv_flow'])

        self.line_valve.set_data(times, history['valve'])

        # 处理填充区域 (先清空再添加)
        for c in self.ax3.collections:
            c.remove()
        self.ax3.fill_between(times, 0, history['valve'], color='magenta', alpha=0.1)

        # 自动调整坐标轴范围 (Auto Scale)
        # 注意：如果用户正在使用Toolbar的Zoom功能，这里的relim可能会重置用户的视图
        # 只有在完全Reset或者用户没有锁定视图时才自动缩放？
        # 为了“瞬间看到所有曲线”，这里强制 relim 和 autoscale_view
        for ax in [self.ax1, self.ax2, self.ax3]:
            ax.relim()
            ax.autoscale_view()

        self.canvas.draw()

    # =========================================================================
    # 辅助功能
    # =========================================================================
    def _create_slider(self, parent, label, min_val, max_val, default):
        f = ttk.Frame(parent)
        f.pack(fill=tk.X, pady=1)

        tf = ttk.Frame(f)
        tf.pack(fill=tk.X)
        ttk.Label(tf, text=label).pack(side=tk.LEFT)
        val_lbl = ttk.Label(tf, text=f"{default:.2f}", foreground=COLOR_PRIMARY, width=6)
        val_lbl.pack(side=tk.RIGHT)

        var = tk.DoubleVar(value=default)

        def _on_change(v):
            val_lbl.config(text=f"{float(v):.2f}")
            # 自动刷新逻辑: 节流，避免过于频繁，但这里简单处理
            if self.auto_refresh.get():
                self.run_full_simulation()  # 参数变动，立即重算

        # 使用 command 绑定回调，实现拖动即刷新
        scale = ttk.Scale(f, from_=min_val, to=max_val, variable=var, orient=tk.HORIZONTAL, command=_on_change)
        scale.pack(fill=tk.X)

        # 绑定鼠标释放事件，确保最后一次精确更新
        scale.bind("<ButtonRelease-1>", lambda e: self.run_full_simulation())

        return var

    def _create_range_input(self, parent, label, v_min, v_max, v_step):
        f = ttk.Frame(parent)
        f.pack(fill=tk.X, pady=1)
        ttk.Label(f, text=label, width=4).pack(side=tk.LEFT)
        e_min = ttk.Entry(f, width=5);
        e_min.insert(0, v_min);
        e_min.pack(side=tk.LEFT, padx=1)
        ttk.Label(f, text="-").pack(side=tk.LEFT)
        e_max = ttk.Entry(f, width=5);
        e_max.insert(0, v_max);
        e_max.pack(side=tk.LEFT, padx=1)
        ttk.Label(f, text="步长").pack(side=tk.LEFT)
        e_step = ttk.Entry(f, width=5);
        e_step.insert(0, v_step);
        e_step.pack(side=tk.LEFT, padx=1)
        return (e_min, e_max, e_step)

    def reset_ui(self):
        """重置所有参数到默认值并重新运行"""
        self.sim_duration.set(500.0)
        self.s_kp.set(2.0);
        self.s_ki.set(0.5);
        self.s_kd.set(0.0)
        self.m_kp.set(3.5);
        self.m_ki.set(0.02);
        self.m_kd.set(20.0)
        self.sp_temp_scale.set(50);
        self.dist_flow_scale.set(0);
        self.dist_temp_scale.set(0)
        self.run_full_simulation()

    def save_data(self):
        filename = self.system.save_data_to_csv()
        if filename:
            messagebox.showinfo("导出成功", f"数据已保存至:\n{filename}")
        else:
            messagebox.showerror("错误", "导出失败")

    # =========================================================================
    # 智能整定逻辑 (保持原逻辑，适配新界面)
    # =========================================================================
    def start_auto_tune_thread(self):
        # 1. 校验输入
        s_kp_rng = self._get_range_values(self.entry_s_kp)
        s_ki_rng = self._get_range_values(self.entry_s_ki)
        m_kp_rng = self._get_range_values(self.entry_m_kp)
        m_ki_rng = self._get_range_values(self.entry_m_ki)
        m_kd_rng = self._get_range_values(self.entry_m_kd)

        if not all([s_kp_rng, s_ki_rng, m_kp_rng, m_ki_rng, m_kd_rng]):
            messagebox.showerror("输入错误", "请检查搜索范围")
            return

        self.btn_auto_tune.config(state=tk.DISABLED)
        self.is_optimizing = True
        self.log_text.config(state='normal');
        self.log_text.delete(1.0, tk.END);
        self.log_text.config(state='disabled')

        self.opt_generator = self._tuning_process_generator(s_kp_rng, s_ki_rng, m_kp_rng, m_ki_rng, m_kd_rng)
        self._log(">>> 启动智能整定任务...")
        self.root.after(10, self._process_optimization_step)

    def _get_range_values(self, entries):
        try:
            start, stop, step = float(entries[0].get()), float(entries[1].get()), float(entries[2].get())
            if step <= 0: return None
            vals = []
            curr = start
            while curr <= stop + 1e-9:
                vals.append(round(curr, 4))
                curr += step
            return vals
        except ValueError:
            return None

    def _log(self, msg):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def _tuning_process_generator(self, s_kp_list, s_ki_list, m_kp_list, m_ki_list, m_kd_list):
        # 为了不破坏主界面的system实例，这里新建一个临时的
        sim = CascadeControlSystem(dt=0.5)

        # === Stage 1: 副环优化 ===
        best_cost_s = float('inf')
        best_params_s = (1.0, 0.5, 0.0)
        total_s = len(s_kp_list) * len(s_ki_list)
        count = 0
        m_dummy = (0.5, 0.0, 0.0)

        for kp, ki in itertools.product(s_kp_list, s_ki_list):
            sim.reset()
            sim.set_pid_params(m_dummy, (kp, ki, 0.0))
            sim.setpoint_temp = 50.0

            for _ in range(int(150 / 0.5)): sim.step()

            cost = 0.0
            for i in range(len(sim.history['time'])):
                err = abs(sim.history['sp_flow'][i] - sim.history['pv_flow'][i])
                cost += err * sim.history['time'][i] * 0.1

            if cost < best_cost_s:
                best_cost_s = cost
                best_params_s = (kp, ki, 0.0)
                self._log(f"[S] Kp={kp}, Ki={ki} -> Cost={cost:.1f}")

            count += 1
            yield (count / total_s) * 30

        self.temp_best_slave = best_params_s
        self._log(f">>> 副环最佳: {best_params_s}")

        # === Stage 2: 主环优化 ===
        best_cost_m = float('inf')
        best_params_m = (2.0, 0.02, 0.0)
        total_m = len(m_kp_list) * len(m_ki_list) * len(m_kd_list)
        count = 0

        for kp, ki, kd in itertools.product(m_kp_list, m_ki_list, m_kd_list):
            sim.reset()
            sim.set_pid_params((kp, ki, kd), self.temp_best_slave)
            sim.setpoint_temp = 50.0

            max_val = 0.0
            cost_itae = 0.0
            for _ in range(int(400 / 0.5)):
                sim.step()
                val = sim.pv_temp
                if val > max_val: max_val = val
                cost_itae += abs(50.0 - val) * sim.time * 0.1

            overshoot = max(0, max_val - 50.0)
            final_cost = cost_itae + (overshoot * 1000)

            if final_cost < best_cost_m:
                best_cost_m = final_cost
                best_params_m = (kp, ki, kd)
                self._log(f"[M] P={kp} I={ki} D={kd} -> Cost={final_cost:.0f}")

            count += 1
            yield 30 + (count / total_m) * 70

        self.opt_best_params = best_params_m
        yield 100

    def _process_optimization_step(self):
        try:
            for _ in range(5):
                progress = next(self.opt_generator)
                self.progress_var.set(progress)
            self.root.after(10, self._process_optimization_step)
        except StopIteration:
            self._optimization_finished()
        except Exception as e:
            self._log(f"Error: {str(e)}")
            self.btn_auto_tune.config(state=tk.NORMAL)

    def _optimization_finished(self):
        self.is_optimizing = False
        self.btn_auto_tune.config(state=tk.NORMAL)
        self.progress_var.set(100)

        res_m = self.opt_best_params
        res_s = self.temp_best_slave

        self._log(">>> 完成!")
        self._log(f"Best M: {res_m}")
        self._log(f"Best S: {res_s}")

        # 更新UI
        self.s_kp.set(res_s[0]);
        self.s_ki.set(res_s[1]);
        self.s_kd.set(res_s[2])
        self.m_kp.set(res_m[0]);
        self.m_ki.set(res_m[1]);
        self.m_kd.set(res_m[2])

        self.run_full_simulation()
        messagebox.showinfo("优化完成", "已自动应用最佳 PID 参数。")


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()