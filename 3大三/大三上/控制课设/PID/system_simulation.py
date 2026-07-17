from pid_controller import PIDController
from plant_model import TowerBottomSystem
import csv
import datetime


class CascadeControlSystem:
    def __init__(self, dt=0.1):
        self.dt = dt
        self.time = 0.0

        # --- 初始化对象 ---
        self.plant = TowerBottomSystem(dt=dt)

        # --- 初始化控制器 (修复了之前的参数名错误) ---
        # 主控制器 (Master/Primary): 温度环
        # 输出范围: 0-100 (假设最大设计流量为100)
        self.master_pid = PIDController(kp=1.0, ki=0.0, kd=0.0, sample_time=dt, output_limits=(0, 100))

        # 副控制器 (Slave/Secondary): 流量环
        # 输出范围: 0-100 (阀门开度 %)
        self.slave_pid = PIDController(kp=1.0, ki=0.0, kd=0.0, sample_time=dt, output_limits=(0, 100))

        # --- 系统变量 ---
        self.setpoint_temp = 50.0  # 设定温度
        self.setpoint_flow_cascade = 0.0  # 串级输出(流量设定值)

        self.pv_temp = 0.0
        self.pv_flow = 0.0
        self.valve_out = 0.0

        self.disturbance_flow = 0.0
        self.disturbance_temp = 0.0

        # --- 数据记录 ---
        self.history = {
            'time': [],
            'sp_temp': [], 'pv_temp': [],
            'sp_flow': [], 'pv_flow': [],
            'valve': []
        }

    def set_pid_params(self, m_params, s_params):
        """更新PID参数"""
        self.master_pid.set_tunings(*m_params)
        self.slave_pid.set_tunings(*s_params)

    def step(self):
        """执行单步仿真"""
        # 1. 主回路 (温度控制器)
        # 输入: 温度设定值, 温度测量值
        # 输出: 流量设定值 (串级给定)
        self.setpoint_flow_cascade = self.master_pid.update(self.setpoint_temp, self.pv_temp, self.time)

        # 2. 副回路 (流量控制器)
        # 输入: 流量设定值 (来自主回路), 流量测量值
        # 输出: 阀门开度
        self.valve_out = self.slave_pid.update(self.setpoint_flow_cascade, self.pv_flow, self.time)

        # 3. 对象响应
        self.pv_flow, self.pv_temp = self.plant.update(
            self.valve_out,
            self.disturbance_flow,
            self.disturbance_temp
        )

        # 4. 记录数据
        self.history['time'].append(self.time)
        self.history['sp_temp'].append(self.setpoint_temp)
        self.history['pv_temp'].append(self.pv_temp)
        self.history['sp_flow'].append(self.setpoint_flow_cascade)
        self.history['pv_flow'].append(self.pv_flow)
        self.history['valve'].append(self.valve_out)

        self.time += self.dt

    def get_metrics(self):
        """获取性能指标"""
        return {
            'm_iae': self.master_pid.iae,
            'm_itae': self.master_pid.itae,
            's_iae': self.slave_pid.iae
        }

    def save_data_to_csv(self):
        """导出数据到CSV"""
        filename = f"simulation_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Time(s)', 'Temp_SP', 'Temp_PV', 'Flow_SP', 'Flow_PV', 'Valve_Op'])
                rows = zip(
                    self.history['time'],
                    self.history['sp_temp'],
                    self.history['pv_temp'],
                    self.history['sp_flow'],
                    self.history['pv_flow'],
                    self.history['valve']
                )
                writer.writerows(rows)
            return filename
        except Exception as e:
            return None

    def reset(self):
        self.time = 0.0
        self.plant.reset()
        self.master_pid.reset()
        self.slave_pid.reset()
        self.pv_temp = 0.0
        self.pv_flow = 0.0
        self.valve_out = 0.0
        self.setpoint_flow_cascade = 0.0

        for key in self.history:
            self.history[key] = []