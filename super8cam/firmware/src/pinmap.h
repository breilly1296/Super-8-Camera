/**
 * pinmap.h — STM32L031K6 GPIO Pin Assignments
 *
 * Single source for all firmware modules.  No other file should contain
 * raw pin numbers — import the #defines from here.
 *
 * Target: STM32L031K6 (LQFP32)
 *
 * Connector cross-reference (from specs/modularity.py):
 *   J1: 2-pin JST-VH  MOD-500→MOD-300  MOTOR+, MOTOR-         (800 mA)
 *   J2: 3-pin JST-XH  MOD-200→MOD-500  ENCODER_A/B, GND       (20 mA)
 *   J3: 4-pin JST-XH  MOD-600→MOD-500  VBATT, GND, SENSE, THM (1200 mA)
 *   J4: 5-pin JST-XH  MOD-500→MOD-100  FPS_SEL, TRIG, LED,GND (50 mA)
 *   J5: 6-pin JST-XH  MOD-400→MOD-500  CART/FILM/DOOR/NOTCH   (100 mA)
 *   J6: 7-pin JST-XH  MOD-500→MOD-700  SPI + I2C bus           (30 mA)
 *   J7: 8-pin JST-XH  MOD-500→MOD-600  UART, I2C, PWM, AUX   (200 mA)
 *
 * ┌──────────┬──────┬─────────────────────────────────────────────────┐
 * │ Pin      │ Mode │ Function                                       │
 * ├──────────┼──────┼─────────────────────────────────────────────────┤
 * │ PA0      │ AF2  │ TIM2_CH1  — Motor PWM output          → J1     │
 * │ PA1      │ IN   │ FPS select switch (low=18, high=24)   → J4.1   │
 * │ PA2      │ IN   │ Trigger button (active low)           → J4.3   │
 * │ PA3      │ OUT  │ Fault / warning LED (active high)     → J4.4   │
 * │ PA4      │ AF4  │ TIM22_CH1 — Galvanometer needle PWM            │
 * │ PA5      │ OUT  │ Green LED (exposure OK)                        │
 * │ PA6      │ OUT  │ Red LED (underexposed)                         │
 * │ PA7      │ ANA  │ ADC_IN7   — Photodiode / TIA output            │
 * │ PA9      │ AF4  │ USART2_TX — Debug UART                → J7.1   │
 * │ PA10     │ AF4  │ USART2_RX — Debug UART                → J7.2   │
 * │ PA13     │ AF0  │ SWDIO     — SWD debug (reserved)               │
 * │ PA14     │ AF0  │ SWCLK     — SWD debug (reserved)               │
 * │ PB0      │ IN   │ DIP switch bit 0 (ASA select, pull-down)       │
 * │ PB1      │ IN   │ DIP switch bit 1 (ASA select, pull-down)       │
 * │ PB2      │ OUT  │ Low-battery warning LED               → J3     │
 * │ PB4      │ AF6  │ TIM21_CH1 — Encoder input capture     → J2.1   │
 * │ PB5      │ OUT  │ Cartridge-empty warning LED           → J5.1   │
 * │ PB6      │ IN   │ Film door switch (active low)         → J5.3   │
 * │ PB7      │ OUT  │ Motor direction control               → J1     │
 * └──────────┴──────┴─────────────────────────────────────────────────┘
 */

#ifndef PINMAP_H
#define PINMAP_H

#include "stm32l0xx.h"

/* =====================================================================
 * PORT A
 * ===================================================================== */

/* PA0: Motor PWM — TIM2 CH1 (AF2)
 * Connector J1 pin 1 (MOTOR+), 2-pin JST-VH, red wire
 * MOD-500 ELECTRONICS → MOD-300 DRIVETRAIN, 800 mA max */
#define PIN_PWM_MOTOR_PORT      GPIOA
#define PIN_PWM_MOTOR_PIN       0U
#define PIN_PWM_MOTOR_AF        2U

/* PA1: FPS select switch (input, pull-down)
 * Connector J4 pin 1 (FPS_SEL_A), 5-pin JST-XH, blue wire
 * MOD-500 ELECTRONICS → MOD-100 FILM_TRANSPORT, 50 mA max */
#define PIN_FPS_SEL_PORT        GPIOA
#define PIN_FPS_SEL_PIN         1U

/* PA2: Trigger button (input, active low, external pull-up)
 * Connector J4 pin 3 (TRIG_SW), 5-pin JST-XH, grey wire
 * MOD-500 ELECTRONICS → MOD-100 FILM_TRANSPORT, 50 mA max */
#define PIN_TRIGGER_PORT        GPIOA
#define PIN_TRIGGER_PIN         2U

/* PA3: Fault / warning LED (output, push-pull, active high)
 * Connector J4 pin 4 (LED_STATUS), 5-pin JST-XH, white wire
 * MOD-500 ELECTRONICS → MOD-100 FILM_TRANSPORT, 50 mA max */
#define PIN_LED_WARN_PORT       GPIOA
#define PIN_LED_WARN_PIN        3U

/* PA4: Galvanometer PWM — TIM22 CH1 (AF4)
 * On-board metering needle, no external connector */
#define PIN_PWM_NEEDLE_PORT     GPIOA
#define PIN_PWM_NEEDLE_PIN      4U
#define PIN_PWM_NEEDLE_AF       4U

/* PA5: Green exposure LED (output, push-pull)
 * On-board indicator, no external connector */
#define PIN_LED_GREEN_PORT      GPIOA
#define PIN_LED_GREEN_PIN       5U

/* PA6: Red exposure LED (output, push-pull)
 * On-board indicator, no external connector */
#define PIN_LED_RED_PORT        GPIOA
#define PIN_LED_RED_PIN         6U

/* PA7: Metering ADC — ADC_IN7 (analog)
 * On-board photodiode TIA, no external connector */
#define PIN_ADC_METER_PORT      GPIOA
#define PIN_ADC_METER_PIN       7U
#define PIN_ADC_METER_CHANNEL   7U

/* PA9: UART TX — USART2 (AF4)
 * Connector J7 pin 1 (UART_TX), 8-pin JST-XH, red wire
 * MOD-500 ELECTRONICS → MOD-600 POWER, 200 mA max */
#define PIN_UART_TX_PORT        GPIOA
#define PIN_UART_TX_PIN         9U
#define PIN_UART_TX_AF          4U

/* PA10: UART RX — USART2 (AF4)
 * Connector J7 pin 2 (UART_RX), 8-pin JST-XH, orange wire
 * MOD-500 ELECTRONICS → MOD-600 POWER, 200 mA max */
#define PIN_UART_RX_PORT        GPIOA
#define PIN_UART_RX_PIN         10U
#define PIN_UART_RX_AF          4U

/* PA13: SWDIO (reserved — do not reconfigure) */
/* PA14: SWCLK (reserved — do not reconfigure) */

/* =====================================================================
 * PORT B
 * ===================================================================== */

/* PB0: DIP switch bit 0 — ASA select (input, pull-down)
 * On-board DIP switch, no external connector */
#define PIN_DIP0_PORT           GPIOB
#define PIN_DIP0_PIN            0U

/* PB1: DIP switch bit 1 — ASA select (input, pull-down)
 * On-board DIP switch, no external connector */
#define PIN_DIP1_PORT           GPIOB
#define PIN_DIP1_PIN            1U

/* PB2: Low-battery warning LED (output, push-pull)
 * Connector J3 (BATT_SENSE), 4-pin JST-XH
 * MOD-600 POWER → MOD-500 ELECTRONICS, 1200 mA max */
#define PIN_LED_LOWBAT_PORT     GPIOB
#define PIN_LED_LOWBAT_PIN      2U

/* PB4: Encoder input — TIM21 CH1 (AF6)
 * Connector J2 pin 1 (ENCODER_A), 3-pin JST-XH, orange wire
 * MOD-200 SHUTTER → MOD-500 ELECTRONICS, 20 mA max */
#define PIN_ENC_PORT            GPIOB
#define PIN_ENC_PIN             4U
#define PIN_ENC_AF              6U

/* PB5: Cartridge-empty warning LED (output, push-pull)
 * Connector J5 pin 1 (CART_DET), 6-pin JST-XH, red wire
 * MOD-400 CARTRIDGE_BAY → MOD-500 ELECTRONICS, 100 mA max */
#define PIN_LED_CART_PORT       GPIOB
#define PIN_LED_CART_PIN        5U

/* PB6: Film door switch (input, active low, optional)
 * Connector J5 pin 3 (DOOR_SW), 6-pin JST-XH, yellow wire
 * MOD-400 CARTRIDGE_BAY → MOD-500 ELECTRONICS, 100 mA max */
#define PIN_DOOR_PORT           GPIOB
#define PIN_DOOR_PIN            6U

/* PB7: Motor direction control (output, optional)
 * Connector J1 pin 2 (MOTOR-), 2-pin JST-VH, black wire
 * MOD-500 ELECTRONICS → MOD-300 DRIVETRAIN, 800 mA max */
#define PIN_MOTOR_DIR_PORT      GPIOB
#define PIN_MOTOR_DIR_PIN       7U

/* =====================================================================
 * EXTI line numbers (match pin numbers for SYSCFG mux)
 * ===================================================================== */

#define EXTI_TRIGGER_LINE       2U          /* PA2 → EXTI2 (J4.3 TRIG_SW)   */
#define EXTI_FPS_LINE           1U          /* PA1 → EXTI1 (J4.1 FPS_SEL_A) */

#endif /* PINMAP_H */
