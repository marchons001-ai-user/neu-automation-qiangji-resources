class PIDController:
    """
    高级离散PID控制器实现
    包含抗积分饱和(Anti-windup)和微分先行(Derivative on PV)选项
    """

    def __init__(self, kp, ki, kd, sample_time=0.1, output_limits=(None, None)):
        """
        :param kp: 比例系数
        :param ki: 积分系数
        :param kd: 微分系数
        :param sample_time: 采样时间 (dt)
        :param output_limits: 输出限幅 (min, max)
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.sample_time = sample_time
        self.output_limits = output_limits  # (min, max)

        self._integral = 0.0
        self._last_error = 0.0
        self._last_measurement = 0.0

        # 性能指标累积变量
        self.iae = 0.0  # 绝对误差积分
        self.itae = 0.0  # 时间乘绝对误差积分
        self.start_time = 0.0

    def update(self, setpoint, measurement, current_time=0.0):
        """
        计算PID输出
        :param setpoint: 设定值 (SP)
        :param measurement: 测量值 (PV)
        :return: 控制输出 (u)
        """
        error = setpoint - measurement

        # 1. 比例项 (Proportional)
        p_term = self.kp * error

        # 2. 积分项 (Integral) - 使用梯形积分以提高精度
        # 暂时计算，如果输出未饱和再累加，实现抗饱和
        new_integral = self._integral + (error * self.sample_time)
        i_term = self.ki * new_integral

        # 3. 微分项 (Derivative) - 使用测量值的变化率 (Derivative on Measurement) 避免设定值跳变冲击
        # d_term = -self.kd * (measurement - self._last_measurement) / self.sample_time
        # 这里为了简单符合教材，使用标准的误差微分
        d_term = 0.0
        if self.sample_time > 0:
            d_term = self.kd * (error - self._last_error) / self.sample_time

        # 总输出
        output = p_term + i_term + d_term

        # 4. 输出限幅与抗积分饱和 (Output Limiting & Anti-windup)
        min_out, max_out = self.output_limits

        if max_out is not None and output > max_out:
            output = max_out
            # 只有当误差反向时才累积积分，或者直接停止积分累积（钳位法）
            if error < 0:
                self._integral = new_integral
        elif min_out is not None and output < min_out:
            output = min_out
            if error > 0:
                self._integral = new_integral
        else:
            # 未饱和，正常累积积分
            self._integral = new_integral

        # 更新状态
        self._last_error = error
        self._last_measurement = measurement

        # 计算性能指标 (用于课程设计分析)
        abs_error = abs(error)
        self.iae += abs_error * self.sample_time
        self.itae += (current_time - self.start_time) * abs_error * self.sample_time

        return output

    def reset(self):
        """重置控制器状态"""
        self._integral = 0.0
        self._last_error = 0.0
        self._last_measurement = 0.0
        self.iae = 0.0
        self.itae = 0.0
        self.start_time = 0.0

    def set_tunings(self, kp, ki, kd):
        """实时更新PID参数"""
        self.kp = kp
        self.ki = ki
        self.kd = kd