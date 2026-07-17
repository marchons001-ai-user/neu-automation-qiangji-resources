import math


class FirstOrderLag:
    """
    仿真一阶惯性环节: G(s) = K / (T*s + 1)
    离散化公式 (后向差分):
    y[k] = (dt * K * u[k] + T * y[k-1]) / (T + dt)
    """

    def __init__(self, K, T, initial_value=0.0, dt=0.1):
        self.K = K
        self.T = T
        self.dt = dt
        self.output = initial_value

    def update(self, u):
        if self.T + self.dt == 0:
            return self.output
        new_output = (self.dt * self.K * u + self.T * self.output) / (self.T + self.dt)
        self.output = new_output
        return self.output

    def reset(self, initial_value=0.0):
        self.output = initial_value


class TowerBottomSystem:
    """
    精馏塔塔底温度控制系统对象模型 (串级结构)

    副回路 (内环): 蒸汽流量控制
    对象 W3(s) = 1 / (2s + 1)

    主回路 (外环): 塔底温度控制
    对象 W4(s) = 2 / ((120s + 1)(130s + 1))
    """

    def __init__(self, dt=0.1):
        self.dt = dt

        # --- 副回路对象 (执行器+流量对象) ---
        # W3(s) = 1 / (2s + 1)
        self.steam_flow_plant = FirstOrderLag(K=1.0, T=2.0, dt=dt)

        # --- 主回路对象 (广义温度对象) ---
        # W4(s) = 2 / ((120s + 1)(130s + 1))
        # 拆分为两个一阶惯性环节串联
        # G1 = 1 / (120s + 1)
        # G2 = 2 / (130s + 1)
        self.temp_lag1 = FirstOrderLag(K=1.0, T=120.0, dt=dt)
        self.temp_lag2 = FirstOrderLag(K=2.0, T=130.0, dt=dt)

        self.flow_value = 0.0
        self.temp_value = 0.0

    def update(self, valve_opening, disturbance_flow=0.0, disturbance_temp=0.0):
        """
        :param valve_opening: 阀门开度 (来自副PID输出)
        :param disturbance_flow: 流量环干扰 D1 (如蒸汽总管压力波动)
        :param disturbance_temp: 温度环干扰 D2 (如进料流量/温度波动)
        """
        # 1. 计算蒸汽流量 (Inner Loop)
        clean_flow = self.steam_flow_plant.update(valve_opening)

        # 加入D1干扰 (加在流量测量值上，因为压力波动直接影响流量)
        self.flow_value = clean_flow + disturbance_flow

        # 2. 计算塔底温度 (Outer Loop)
        # 流量作为温度对象的输入
        intermediate_val = self.temp_lag1.update(self.flow_value)
        clean_temp = self.temp_lag2.update(intermediate_val)

        # 加入D2干扰
        self.temp_value = clean_temp + disturbance_temp

        return self.flow_value, self.temp_value

    def reset(self):
        self.steam_flow_plant.reset()
        self.temp_lag1.reset()
        self.temp_lag2.reset()
        self.flow_value = 0.0
        self.temp_value = 0.0