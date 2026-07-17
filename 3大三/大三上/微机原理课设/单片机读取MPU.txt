#include "STC8H.H"
#include "intrins.h"
#include <stdio.h>
#include <string.h>
#include <math.h>

// 宏定义 - 系统时钟改为22.1184MHz，波特率115203
#define FOSC 22118400UL
#define BAUD 115203UL

// MPU6050引脚定义
sbit SDA = P3^3;
sbit SCL = P3^2;

// MPU6050寄存器地址定义
#define MPU6050_ADDR 0xD0
#define SMPLRT_DIV 0x19
#define CONFIG 0x1A
#define GYRO_CONFIG 0x1B
#define ACCEL_CONFIG 0x1C
#define ACCEL_XOUT_H 0x3B
#define ACCEL_XOUT_L 0x3C
#define ACCEL_YOUT_H 0x3D
#define ACCEL_YOUT_L 0x3E
#define ACCEL_ZOUT_H 0x3F
#define ACCEL_ZOUT_L 0x40
#define TEMP_OUT_H 0x41
#define TEMP_OUT_L 0x42
#define GYRO_XOUT_H 0x43
#define GYRO_XOUT_L 0x44
#define GYRO_YOUT_H 0x45
#define GYRO_YOUT_L 0x46
#define GYRO_ZOUT_H 0x47
#define GYRO_ZOUT_L 0x48
#define PWR_MGMT_1 0x6B
#define WHO_AM_I 0x75

// 全局变量
unsigned int count = 0;
short acc_x, acc_y, acc_z;
short gyro_x, gyro_y, gyro_z;
short temp;
bit timer_flag = 0;

// 定时器0初始化 - 22.1184MHz下精确100ms定时
void Timer0_Init(void)
{
    TMOD &= 0xF0;
    TMOD |= 0x01;  // 16位定时器模式
    
    // 22.1184MHz -> 定时器时钟 = FOSC/12 = 1843200Hz (周期0.5425us)
    // 50ms定时需要计数: 50000us / 0.5425us ≈ 92160 次
    // 初值 = 65536 - 92160 = 0xD8F0 (负数补码形式)
    TH0 = 0xD8;
    TL0 = 0xF0;
    
    ET0 = 1;
    TR0 = 1;
    EA = 1;
}

// 定时器0中断服务函数 - 100ms标志
void Timer0_ISR(void) interrupt 1
{
    static unsigned char timer_count = 0;
    TH0 = 0xD8;
    TL0 = 0xF0;  // 重装载初值
    
    timer_count++;
    if(timer_count >= 20)  // 5ms*20=100ms
    {
        timer_count = 0;
        timer_flag = 1;
    }
}

// 毫秒级延时函数
void DelayMS(unsigned int ms)
{
    unsigned int i, j;
    for(i = 0; i < ms; i++)
        for(j = 0; j < 2200; j++)  // 适配22.1184MHz
            _nop_();
}

// 微秒级延时函数 - I2C时序专用
void DelayUS(unsigned int us)
{
    while(us--)
    {
        _nop_();_nop_();_nop_();_nop_();
        _nop_();_nop_();_nop_();_nop_();
    }
}

// UART2初始化 - 115203bps@22.1184MHz (P1.0=RXD2, P1.1=TXD2)
void Uart2_Init(void)
{
    // 配置P1.0/P1.1引脚模式
    P1M1 &= ~0x03;
    P1M0 &= ~0x01;  // P1.0(RXD2) 准双向输入
    P1M0 |= 0x02;   // P1.1(TXD2) 推挽输出
    
    S2CON = 0x50;   // 8位数据,可变波特率,允许接收
    AUXR |= 0x04;   // 定时器2 1T模式
    T2L = 0xD0;     // 波特率115203 初值
    T2H = 0xFF;
    AUXR |= 0x10;   // 启动定时器2
}

// UART2发送单个字节
void Uart2_SendByte(unsigned char dat)
{
    S2BUF = dat;
    while (!(S2CON & 0x02));  // 等待TI2置位
    S2CON &= ~0x02;           // 清除标志
}

// UART2发送字符串
void Uart2_SendString(char *str)
{
    while (*str)
    {
        Uart2_SendByte(*str++);
    }
}

// 重定向printf到UART2
char putchar(char c)
{
    Uart2_SendByte(c);
    return c;
}

// I2C初始化
void I2C_Init(void)
{
    P3M1 |= (1<<2 | 1<<3);
    P3M0 |= (1<<2 | 1<<3);  // SCL/SDA 开漏输出
    SCL = 1;
    SDA = 1;
    DelayMS(10);
}

// I2C起始信号
void I2C_Start(void)
{
    SDA = 1;DelayUS(10);
    SCL = 1;DelayUS(10);
    SDA = 0;DelayUS(10);
    SCL = 0;DelayUS(10);
}

// I2C停止信号
void I2C_Stop(void)
{
    SDA = 0;DelayUS(10);
    SCL = 1;DelayUS(10);
    SDA = 1;DelayUS(10);
}

// I2C发送字节
void I2C_SendByte(unsigned char dat)
{
    unsigned char i;
    for(i = 0; i < 8; i++)
    {
        SDA = (dat & 0x80) ? 1 : 0;
        dat <<= 1;
        DelayUS(5);
        SCL = 1;DelayUS(10);
        SCL = 0;DelayUS(5);
    }
}

// I2C接收字节
unsigned char I2C_RecvByte(void)
{
    unsigned char i, dat = 0;
    P3M1 |= (1<<3);
    P3M0 &= ~(1<<3);  // SDA输入模式
    SDA = 1;
    
    for(i = 0; i < 8; i++)
    {
        dat <<= 1;
        DelayUS(5);
        SCL = 1;DelayUS(10);
        if(SDA) dat |= 0x01;
        SCL = 0;DelayUS(5);
    }
    
    P3M1 |= (1<<3);
    P3M0 |= (1<<3);  // 恢复SDA输出
    return dat;
}

// I2C发送应答
void I2C_Ack(void)
{
    P3M1 |= (1<<3);
    P3M0 |= (1<<3);
    SDA = 0;DelayUS(5);
    SCL = 1;DelayUS(10);
    SCL = 0;DelayUS(5);
    SDA = 1;DelayUS(5);
}

// I2C发送非应答
void I2C_NAck(void)
{
    P3M1 |= (1<<3);
    P3M0 |= (1<<3);
    SDA = 1;DelayUS(5);
    SCL = 1;DelayUS(10);
    SCL = 0;DelayUS(5);
}

// I2C等待应答
unsigned char I2C_WaitAck(void)
{
    unsigned char ack;
    P3M1 |= (1<<3);
    P3M0 &= ~(1<<3);
    SDA = 1;DelayUS(5);
    SCL = 1;DelayUS(10);
    ack = SDA;
    SCL = 0;DelayUS(5);
    P3M1 |= (1<<3);
    P3M0 |= (1<<3);
    return ack;
}

// MPU6050写寄存器
bit MPU6050_WriteReg(unsigned char reg_addr, unsigned char dat)
{
    bit ack_flag;
    I2C_Start();
    I2C_SendByte(MPU6050_ADDR);
    ack_flag = I2C_WaitAck();
    if(ack_flag) {I2C_Stop();return 0;}
    
    I2C_SendByte(reg_addr);
    ack_flag = I2C_WaitAck();
    if(ack_flag) {I2C_Stop();return 0;}
    
    I2C_SendByte(dat);
    ack_flag = I2C_WaitAck();
    I2C_Stop();
    return (ack_flag == 0);
}

// MPU6050读寄存器
unsigned char MPU6050_ReadReg(unsigned char reg_addr)
{
    unsigned char dat;
    bit ack_flag;
    I2C_Start();
    I2C_SendByte(MPU6050_ADDR);
    ack_flag = I2C_WaitAck();
    if(ack_flag) {I2C_Stop();return 0xFF;}
    
    I2C_SendByte(reg_addr);
    ack_flag = I2C_WaitAck();
    if(ack_flag) {I2C_Stop();return 0xFF;}
    
    I2C_Start();
    I2C_SendByte(MPU6050_ADDR | 0x01);
    ack_flag = I2C_WaitAck();
    if(ack_flag) {I2C_Stop();return 0xFF;}
    
    dat = I2C_RecvByte();
    I2C_NAck();
    I2C_Stop();
    return dat;
}

// MPU6050初始化
bit MPU6050_Init(void)
{
    unsigned char i;
    unsigned char id;
    DelayMS(100);
    
    for(i = 0; i < 5; i++) 
    {
        id = MPU6050_ReadReg(WHO_AM_I);
        if(id == 0x68) break;
        DelayMS(10);
    }
    if(id != 0x68) return 0;
    
    if(!MPU6050_WriteReg(PWR_MGMT_1, 0x00)) return 0;
    DelayMS(10);
    if(!MPU6050_WriteReg(SMPLRT_DIV, 0x07)) return 0;
    if(!MPU6050_WriteReg(CONFIG, 0x06)) return 0;
    if(!MPU6050_WriteReg(GYRO_CONFIG, 0x18)) return 0;
    if(!MPU6050_WriteReg(ACCEL_CONFIG, 0x10)) return 0;
    
    DelayMS(100);
    return 1;
}

// 读取MPU6050全部数据
bit MPU6050_ReadData(void)
{
    unsigned char buf[14];
    unsigned char i;
    bit ack_flag;
    
    I2C_Start();
    I2C_SendByte(MPU6050_ADDR);
    ack_flag = I2C_WaitAck();
    if(ack_flag) {I2C_Stop();return 0;}
    
    I2C_SendByte(ACCEL_XOUT_H);
    ack_flag = I2C_WaitAck();
    if(ack_flag) {I2C_Stop();return 0;}
    
    I2C_Start();
    I2C_SendByte(MPU6050_ADDR | 0x01);
    ack_flag = I2C_WaitAck();
    if(ack_flag) {I2C_Stop();return 0;}
    
    for(i = 0; i < 14; i++)
    {
        buf[i] = I2C_RecvByte();
        if(i < 13) I2C_Ack();
        else I2C_NAck();
    }
    I2C_Stop();
    
    acc_x = (buf[0] << 8) | buf[1];
    acc_y = (buf[2] << 8) | buf[3];
    acc_z = (buf[4] << 8) | buf[5];
    temp = (buf[6] << 8) | buf[7];
    gyro_x = (buf[8] << 8) | buf[9];
    gyro_y = (buf[10] << 8) | buf[11];
    gyro_z = (buf[12] << 8) | buf[13];
    return 1;
}

// 计算温度值(摄氏度)
float MPU6050_GetTemperature(void)
{
    return (temp / 340.0) + 36.53;
}

// 调试函数-读取单个寄存器值
void MPU6050_DebugRead(void)
{
    unsigned char i;
    short raw_data;
    Uart2_SendString("Debug - Reading individual registers:\r\n");
    
    for(i = 0; i < 3; i++) 
    {
        raw_data = (MPU6050_ReadReg(ACCEL_XOUT_H + i*2) << 8) | MPU6050_ReadReg(ACCEL_XOUT_L + i*2);
        printf("Acc%d raw: %d\r\n", i, raw_data);
    }
    for(i = 0; i < 3; i++) 
    {
        raw_data = (MPU6050_ReadReg(GYRO_XOUT_H + i*2) << 8) | MPU6050_ReadReg(GYRO_XOUT_L + i*2);
        printf("Gyro%d raw: %d\r\n", i, raw_data);
    }
}

// 主函数
void main(void)
{
    unsigned char id;
    Uart2_Init();   // 初始化UART2(蓝牙串口)
    I2C_Init();     // 初始化I2C
    Timer0_Init();  // 初始化100ms定时器
    DelayMS(1000);  // 系统稳定延时
    
    Uart2_SendString("Initializing MPU6050...\r\n");
    id = MPU6050_ReadReg(WHO_AM_I);
    printf("MPU6050 ID: 0x%02X\r\n", id);
    
    if(id == 0x68)
    {
        Uart2_SendString("MPU6050 detected successfully!\r\n");
        if(MPU6050_Init())
        {
            Uart2_SendString("MPU6050 initialized successfully!\r\n");
            MPU6050_DebugRead();
            DelayMS(1000);
            Uart2_SendString("Starting 100ms interval data transmission...\r\n");
            Uart2_SendString("Format: AccX,AccY,AccZ,GyroX,GyroY,GyroZ,Temp\r\n");
        }
        else
        {
            Uart2_SendString("MPU6050 initialization failed!\r\n");
            while(1);
        }
    }
    else
    {
        printf("MPU6050 detection failed! Expected 0x68, got 0x%02X\r\n", id);
        Uart2_SendString("Please check:\r\n");
        Uart2_SendString("1. I2C connections (SDA=P3.3, SCL=P3.2)\r\n");
        Uart2_SendString("2. Power supply (3.3V)\r\n");
        Uart2_SendString("3. Pull-up resistors (4.7k on SDA/SCL)\r\n");
        while(1);
    }
    
    DelayMS(1000);
    while(1)
    {
        if(timer_flag)
        {
            timer_flag = 0;
            if(MPU6050_ReadData())
            {
                // 发送格式化数据: 加速度(g)、陀螺仪(°/s)、温度(°C)
							  printf("MPU6050 Data:");
                printf("%.3f,%.3f,%.3f,", acc_x/4096.0, acc_y/4096.0, acc_z/4096.0);
                printf("%.3f,%.3f,%.3f,", gyro_x/16.4, gyro_y/16.4, gyro_z/16.4);
                printf("%.3f\r\n", MPU6050_GetTemperature());
                count++;
            }
            else
            {
                Uart2_SendString("Error reading MPU6050 data!\r\n");
            }
        }
    }
}