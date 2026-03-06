/**
 * pinmap.h — STM32L031K6 GPIO Pin Assignments
 *
 * Single source for all firmware modules.  No other file should contain
 * raw pin numbers — import the #defines from here.
 *
 * Target: STM32L031K6 (LQFP32)
 *
 * ┌──────────┬──────┬─────────────────────────────────────────────────┐
 * │ Pin      │ Mode │ Function                                       │
 * ├──────────┼──────┼─────────────────────────────────────────────────┤
 * │ PA0      │ AF2  │ TIM2_CH1  — Motor PWM output                   │
 * │ PA1      │ IN   │ FPS select switch (low=18, high=24)            │
 * │ PA2      │ IN   │ Trigger button (active low, ext pull-up)       │
 * │ PA3      │ OUT  │ Fault / warning LED (active high)              │
 * │ PA4      │ AF4  │ TIM22_CH1 — Galvanometer needle PWM            │
 * │ PA5      │ OUT  │ Green LED (exposure OK)                        │
 * │ PA6      │ OUT  │ Red LED (underexposed)                         │
 * │ PA7      │ ANA  │ ADC_IN7   — Photodiode / TIA output            │
 * │ PA9      │ AF4  │ USART2_TX — Debug UART                         │
 * │ PA10     │ AF4  │ USART2_RX — Debug UART                         │
 * │ PA13     │ AF0  │ SWDIO     — SWD debug (reserved)               │
 * │ PA14     │ AF0  │ SWCLK     — SWD debug (reserved)               │
 * │ PB0      │ IN   │ DIP switch bit 0 (ASA select, pull-down)       │
 * │ PB1      │ IN   │ DIP switch bit 1 (ASA select, pull-down)       │
 * │ PB2      │ OUT  │ Low-battery warning LED                        │
 * │ PB4      │ AF6  │ TIM21_CH1 — Encoder input capture              │
 * │ PB5      │ OUT  │ Cartridge-empty warning LED                    │
 * │ PB6      │ IN   │ Film door switch (active low, optional)        │
 * │ PB7      │ OUT  │ Motor direction control (optional)             │
 * └──────────┴──────┴─────────────────────────────────────────────────┘
 */

#ifndef PINMAP_H
#define PINMAP_H

#include "stm32l0xx.h"

/* =====================================================================
 * PORT A
 * ===================================================================== */

/* PA0: Motor PWM — TIM2 CH1 (AF2) */
#define PIN_PWM_MOTOR_PORT      GPIOA
#define PIN_PWM_MOTOR_PIN       0U
#define PIN_PWM_MOTOR_AF        2U

/* PA1: FPS select switch (input, pull-down) */
#define PIN_FPS_SEL_PORT        GPIOA
#define PIN_FPS_SEL_PIN         1U

/* PA2: Trigger button (input, active low, external pull-up) */
#define PIN_TRIGGER_PORT        GPIOA
#define PIN_TRIGGER_PIN         2U

/* PA3: Fault / warning LED (output, push-pull, active high) */
#define PIN_LED_WARN_PORT       GPIOA
#define PIN_LED_WARN_PIN        3U

/* PA4: Galvanometer PWM — TIM22 CH1 (AF4) */
#define PIN_PWM_NEEDLE_PORT     GPIOA
#define PIN_PWM_NEEDLE_PIN      4U
#define PIN_PWM_NEEDLE_AF       4U

/* PA5: Green exposure LED (output, push-pull) */
#define PIN_LED_GREEN_PORT      GPIOA
#define PIN_LED_GREEN_PIN       5U

/* PA6: Red exposure LED (output, push-pull) */
#define PIN_LED_RED_PORT        GPIOA
#define PIN_LED_RED_PIN         6U

/* PA7: Metering ADC — ADC_IN7 (analog) */
#define PIN_ADC_METER_PORT      GPIOA
#define PIN_ADC_METER_PIN       7U
#define PIN_ADC_METER_CHANNEL   7U

/* PA9: UART TX — USART2 (AF4) */
#define PIN_UART_TX_PORT        GPIOA
#define PIN_UART_TX_PIN         9U
#define PIN_UART_TX_AF          4U

/* PA10: UART RX — USART2 (AF4) */
#define PIN_UART_RX_PORT        GPIOA
#define PIN_UART_RX_PIN         10U
#define PIN_UART_RX_AF          4U

/* PA13: SWDIO (reserved — do not reconfigure) */
/* PA14: SWCLK (reserved — do not reconfigure) */

/* =====================================================================
 * PORT B
 * ===================================================================== */

/* PB0: DIP switch bit 0 — ASA select (input, pull-down) */
#define PIN_DIP0_PORT           GPIOB
#define PIN_DIP0_PIN            0U

/* PB1: DIP switch bit 1 — ASA select (input, pull-down) */
#define PIN_DIP1_PORT           GPIOB
#define PIN_DIP1_PIN            1U

/* PB2: Low-battery warning LED (output, push-pull) */
#define PIN_LED_LOWBAT_PORT     GPIOB
#define PIN_LED_LOWBAT_PIN      2U

/* PB4: Encoder input — TIM21 CH1 (AF6) */
#define PIN_ENC_PORT            GPIOB
#define PIN_ENC_PIN             4U
#define PIN_ENC_AF              6U

/* PB5: Cartridge-empty warning LED (output, push-pull) */
#define PIN_LED_CART_PORT       GPIOB
#define PIN_LED_CART_PIN        5U

/* PB6: Film door switch (input, active low, optional) */
#define PIN_DOOR_PORT           GPIOB
#define PIN_DOOR_PIN            6U

/* PB7: Motor direction control (output, optional) */
#define PIN_MOTOR_DIR_PORT      GPIOB
#define PIN_MOTOR_DIR_PIN       7U

/* =====================================================================
 * EXTI line numbers (match pin numbers for SYSCFG mux)
 * ===================================================================== */

#define EXTI_TRIGGER_LINE       2U          /* PA2 → EXTI2                  */
#define EXTI_FPS_LINE           1U          /* PA1 → EXTI1                  */

#endif /* PINMAP_H */
