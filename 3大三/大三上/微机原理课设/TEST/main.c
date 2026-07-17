#include "STC8H.H"
#include "intrins.h"
#include <stdio.h>
#include <string.h>
#include <math.h>

// 宏定义
#define FOSC 11059200UL  // 11.0592MHz系统时钟
#define BAUD 9600UL      // 波特率9600

// MPU6050引脚定义
sbit SDA = P3^3;
sbit SCL = P3^2;

// MPU6050寄存器地址定义
#define MPU6050_ADDR 0xD0  // MPU6050设备地址
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
short acc_x, acc_y, acc_z;     // 加速度数据
short gyro_x, gyro_y, gyro_z;  // 陀螺仪数据
short temp;                    // 温度数据

// 延时函数（毫秒级）
void DelayMS(unsigned int ms)
{
    unsigned int i, j;
    for(i = 0; i < ms; i++)
        for(j = 0; j < 1100; j++)
            _nop_();
}

// 延时函数（微秒级）- 用于I2C时序
void DelayUS(unsigned int us)
{
    while(us--)
    {
        _nop_();_nop_();_nop_();_nop_();
        _nop_();_nop_();_nop_();_nop_();
    }
}

// 串口初始化
void Uart1_Init(void)
{
    // 关闭看门狗
    WDT_CONTR = 0;
    
    // 配置P3.0(RxD)和P3.1(TxD)引脚模式
    P3M1 |= 0x01;   // P3.0(RxD)设置为高阻输入
    P3M0 &= ~0x01;
    P3M1 &= ~0x02;  // P3.1(TxD)设置为推挽输出
    P3M0 |= 0x02;
    
    // 确保使用正确的引脚映射（串口1在P3.0/P3.1）
    P_SW1 &= 0x3F;  // 清除UART1引脚选择位，选择P3.0/P3.1
    
    SCON = 0x50;    // 8位数据,可变波特率
    AUXR |= 0x40;   // 定时器时钟1T模式
    AUXR &= 0xFE;   // 串口1选择定时器1为波特率发生器
    TMOD &= 0x0F;   // 设置定时器模式
    TL1 = 0xE0;     // 设置定时初始值
    TH1 = 0xFE;     // 设置定时初始值
    ET1 = 0;        // 禁止定时器1中断
    TR1 = 1;        // 定时器1开始计时
}

// 发送单个字节
void UART_SendByte(unsigned char dat)
{
    SBUF = dat;
    while (!TI);   // 等待发送完成
    TI = 0;        // 清除发送完成标志
}

// 发送字符串
void UART_SendString(char *str)
{
    while (*str) {
        UART_SendByte(*str++);
    }
}

// 重定向putchar函数，支持printf
char putchar(char c)
{
    UART_SendByte(c);
    return c;
}

// I2C初始化
void I2C_Init(void)
{
    // 将P3.2(SCL)和P3.3(SDA)设置为开漏输出模式
    // STC8H的I2C引脚应该设置为开漏模式，并外部上拉
    P3M1 |= (1<<2 | 1<<3);   // 设置为高阻输入（开漏输出时）
    P3M0 |= (1<<2 | 1<<3);   // 设置为推挽输出（开漏输出时）
    // 实际上STC8H的开漏模式设置：P3M1.n=1, P3M0.n=1 为开漏模式
    
    // 开漏模式设置
    P3M1 |= (1<<2 | 1<<3);   // 高阻输入特性
    P3M0 |= (1<<2 | 1<<3);   // 开漏输出
    
    SCL = 1;
    SDA = 1;
    
    // 添加初始化延时
    DelayMS(10);
}

// I2C起始信号
void I2C_Start(void)
{
    SDA = 1;
    DelayUS(10);
    SCL = 1;
    DelayUS(10);
    SDA = 0;
    DelayUS(10);
    SCL = 0;
    DelayUS(10);
}

// I2C停止信号
void I2C_Stop(void)
{
    SDA = 0;
    DelayUS(10);
    SCL = 1;
    DelayUS(10);
    SDA = 1;
    DelayUS(10);
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
        SCL = 1;
        DelayUS(10);
        SCL = 0;
        DelayUS(5);
    }
}

// I2C接收字节
unsigned char I2C_RecvByte(void)
{
    unsigned char i, dat = 0;
    
    // 确保SDA为输入模式
    P3M1 |= (1<<3);   // P3.3设置为高阻输入
    P3M0 &= ~(1<<3);
    
    SDA = 1;  // 释放SDA线
    
    for(i = 0; i < 8; i++)
    {
        dat <<= 1;
        DelayUS(5);
        SCL = 1;
        DelayUS(10);
        if(SDA) dat |= 0x01;
        SCL = 0;
        DelayUS(5);
    }
    
    // 恢复SDA为输出模式
    P3M1 |= (1<<3);
    P3M0 |= (1<<3);
    
    return dat;
}

// I2C发送应答
void I2C_Ack(void)
{
    // 确保SDA为输出模式
    P3M1 |= (1<<3);
    P3M0 |= (1<<3);
    
    SDA = 0;
    DelayUS(5);
    SCL = 1;
    DelayUS(10);
    SCL = 0;
    DelayUS(5);
    SDA = 1;
    DelayUS(5);
}

// I2C发送非应答
void I2C_NAck(void)
{
    // 确保SDA为输出模式
    P3M1 |= (1<<3);
    P3M0 |= (1<<3);
    
    SDA = 1;
    DelayUS(5);
    SCL = 1;
    DelayUS(10);
    SCL = 0;
    DelayUS(5);
}

// I2C等待应答
unsigned char I2C_WaitAck(void)
{
    unsigned char ack;
    
    // 设置SDA为输入模式
    P3M1 |= (1<<3);   // 高阻输入
    P3M0 &= ~(1<<3);
    
    SDA = 1;  // 释放SDA线
    DelayUS(5);
    SCL = 1;
    DelayUS(10);
    ack = SDA;  // 读取应答信号
    SCL = 0;
    DelayUS(5);
    
    // 恢复SDA为输出模式
    P3M1 |= (1<<3);
    P3M0 |= (1<<3);
    
    return ack;  // 0-应答, 1-非应答
}

// MPU6050写寄存器
bit MPU6050_WriteReg(unsigned char reg_addr, unsigned char dat)
{
    bit ack_flag;
    
    I2C_Start();
    I2C_SendByte(MPU6050_ADDR);
    ack_flag = I2C_WaitAck();
    if(ack_flag) {
        I2C_Stop();
        return 0;  // 写入失败
    }
    
    I2C_SendByte(reg_addr);
    ack_flag = I2C_WaitAck();
    if(ack_flag) {
        I2C_Stop();
        return 0;  // 写入失败
    }
    
    I2C_SendByte(dat);
    ack_flag = I2C_WaitAck();
    I2C_Stop();
    
    return (ack_flag == 0);  // 返回写入状态
}

// MPU6050读寄存器
unsigned char MPU6050_ReadReg(unsigned char reg_addr)
{
    unsigned char dat;
    bit ack_flag;
    
    I2C_Start();
    I2C_SendByte(MPU6050_ADDR);
    ack_flag = I2C_WaitAck();
    if(ack_flag) {
        I2C_Stop();
        return 0xFF;  // 读取失败
    }
    
    I2C_SendByte(reg_addr);
    ack_flag = I2C_WaitAck();
    if(ack_flag) {
        I2C_Stop();
        return 0xFF;  // 读取失败
    }
    
    I2C_Start();
    I2C_SendByte(MPU6050_ADDR | 0x01);
    ack_flag = I2C_WaitAck();
    if(ack_flag) {
        I2C_Stop();
        return 0xFF;  // 读取失败
    }
    
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
    
    DelayMS(100);  // 上电延时
    
    // 尝试多次读取设备ID
    for(i = 0; i < 5; i++) {
        id = MPU6050_ReadReg(WHO_AM_I);
        if(id == 0x68) {
            break;
        }
        DelayMS(10);
    }
    
    if(id != 0x68) {
        return 0;  // 初始化失败
    }
    
    // 解除休眠状态
    if(!MPU6050_WriteReg(PWR_MGMT_1, 0x00)) {
        return 0;
    }
    DelayMS(10);
    
    // 设置采样率
    if(!MPU6050_WriteReg(SMPLRT_DIV, 0x07)) {
        return 0;
    }
    
    // 设置数字低通滤波器
    if(!MPU6050_WriteReg(CONFIG, 0x06)) {
        return 0;
    }
    
    // 设置陀螺仪量程 ±2000度/秒
    if(!MPU6050_WriteReg(GYRO_CONFIG, 0x18)) {
        return 0;
    }
    
    // 设置加速度计量程 ±8g
    if(!MPU6050_WriteReg(ACCEL_CONFIG, 0x10)) {
        return 0;
    }
    
    DelayMS(100);
    return 1;  // 初始化成功
}

// 读取MPU6050数据
bit MPU6050_ReadData(void)
{
    unsigned char buf[14];
    unsigned char i;
    bit ack_flag;
    
    I2C_Start();
    I2C_SendByte(MPU6050_ADDR);
    ack_flag = I2C_WaitAck();
    if(ack_flag) {
        I2C_Stop();
        return 0;
    }
    
    I2C_SendByte(ACCEL_XOUT_H);
    ack_flag = I2C_WaitAck();
    if(ack_flag) {
        I2C_Stop();
        return 0;
    }
    
    I2C_Start();
    I2C_SendByte(MPU6050_ADDR | 0x01);
    ack_flag = I2C_WaitAck();
    if(ack_flag) {
        I2C_Stop();
        return 0;
    }
    
    for(i = 0; i < 13; i++)
    {
        buf[i] = I2C_RecvByte();
        I2C_Ack();
    }
    buf[13] = I2C_RecvByte();
    I2C_NAck();
    I2C_Stop();
    
    // 组合数据
    acc_x = (buf[0] << 8) | buf[1];
    acc_y = (buf[2] << 8) | buf[3];
    acc_z = (buf[4] << 8) | buf[5];
    temp = (buf[6] << 8) | buf[7];
    gyro_x = (buf[8] << 8) | buf[9];
    gyro_y = (buf[10] << 8) | buf[11];
    gyro_z = (buf[12] << 8) | buf[13];
    
    return 1;
}

// 获取MPU6050温度值（摄氏度）
float MPU6050_GetTemperature(void)
{
    return (temp / 340.0) + 36.53;
}

// 主函数
void main(void)
{
    unsigned char id;
    
    // 系统初始化
    Uart1_Init();
    I2C_Init();
    
    // 延时确保系统稳定
    DelayMS(1000);
    
    UART_SendString("Initializing MPU6050...\r\n");
    
    // 首先尝试读取设备ID
    id = MPU6050_ReadReg(WHO_AM_I);
    printf("MPU6050 ID: 0x%02X\r\n", id);
    
    if(id == 0x68) {
        UART_SendString("MPU6050 detected successfully!\r\n");
        
        // 初始化MPU6050
        if(MPU6050_Init()) {
            UART_SendString("MPU6050 initialized successfully!\r\n");
        } else {
            UART_SendString("MPU6050 initialization failed!\r\n");
            while(1);
        }
    } else {
        printf("MPU6050 detection failed! Expected 0x68, got 0x%02X\r\n", id);
        UART_SendString("Please check:\r\n");
        UART_SendString("1. I2C connections (SDA=P3.3, SCL=P3.2)\r\n");
        UART_SendString("2. Power supply (3.3V)\r\n");
        UART_SendString("3. Pull-up resistors (4.7k on SDA/SCL)\r\n");
        while(1);
    }
    
    DelayMS(1000);
    
    while(1) {
        // 读取MPU6050数据
        if(MPU6050_ReadData()) {
            // 输出MPU6050数据
            printf("=== MPU6050 Sensor Data ===\r\n");
            printf("Count: %u\r\n", count++);
            printf("Temperature: %.2f C\r\n", MPU6050_GetTemperature());
            
            printf("Accelerometer:\r\n");
            printf("  X: %6d | Y: %6d | Z: %6d\r\n", acc_x, acc_y, acc_z);
            
            printf("Gyroscope:\r\n");
            printf("  X: %6d | Y: %6d | Z: %6d\r\n", gyro_x, gyro_y, gyro_z);
            
            // 计算加速度值(g)
            printf("Acceleration (g):\r\n");
            printf("  X: %7.3f | Y: %7.3f | Z: %7.3f\r\n", 
                   acc_x/4096.0, acc_y/4096.0, acc_z/4096.0);
            
            // 计算角速度(度/秒)
            printf("Angular Rate (dps):\r\n");
            printf("  X: %7.1f | Y: %7.1f | Z: %7.1f\r\n", 
                   gyro_x/16.4, gyro_y/16.4, gyro_z/16.4);
            
            printf("===========================\r\n\r\n");
        } else {
            UART_SendString("Error reading MPU6050 data!\r\n");
        }
        
        // 延时1秒
        DelayMS(1000);
    }
}