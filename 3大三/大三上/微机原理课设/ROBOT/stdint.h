/* 自定义的stdint.h文件，用于解决Keil C51等编译器缺失问题 */
#ifndef _STDINT_H
#define _STDINT_H

/* 有符号整数类型 */
typedef signed char int8_t;
typedef signed int int16_t;
typedef signed long int32_t;

/* 无符号整数类型 */
typedef unsigned char uint8_t;
typedef unsigned int uint16_t;
typedef unsigned long uint32_t;

/* 指针类型（根据您的内存模型调整） */
typedef unsigned int uintptr_t;

#endif