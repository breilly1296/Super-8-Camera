/**
 * pinmap.h — STM32L0 pin assignments (single source for all firmware modules)
 */

#ifndef PINMAP_H
#define PINMAP_H

/* Motor PWM: PA0 / TIM2_CH1 (AF2) */
#define PIN_PWM_MOTOR_PORT      GPIOA
#define PIN_PWM_MOTOR_PIN       0U
#define PIN_PWM_MOTOR_AF        2U

/* FPS select: PA1 */
#define PIN_FPS_SEL_PORT        GPIOA
#define PIN_FPS_SEL_PIN         1U

/* Trigger button: PA2 (active low) */
#define PIN_TRIGGER_PORT        GPIOA
#define PIN_TRIGGER_PIN         2U

/* Fault/warning LED: PA3 */
#define PIN_LED_WARN_PORT       GPIOA
#define PIN_LED_WARN_PIN        3U

/* Galvanometer PWM: PA4 / TIM22_CH1 (AF4) */
#define PIN_PWM_NEEDLE_PORT     GPIOA
#define PIN_PWM_NEEDLE_PIN      4U
#define PIN_PWM_NEEDLE_AF       4U

/* Green LED: PA5 */
#define PIN_LED_GREEN_PORT      GPIOA
#define PIN_LED_GREEN_PIN       5U

/* Red LED: PA6 */
#define PIN_LED_RED_PORT        GPIOA
#define PIN_LED_RED_PIN         6U

/* Metering ADC: PA7 / ADC_IN7 */
#define PIN_ADC_METER_PORT      GPIOA
#define PIN_ADC_METER_PIN       7U
#define PIN_ADC_METER_CHANNEL   7U

/* DIP switch: PB0, PB1 */
#define PIN_DIP0_PORT           GPIOB
#define PIN_DIP0_PIN            0U
#define PIN_DIP1_PORT           GPIOB
#define PIN_DIP1_PIN            1U

/* Low battery LED: PB2 */
#define PIN_LED_LOWBAT_PORT     GPIOB
#define PIN_LED_LOWBAT_PIN      2U

/* Encoder input: PB4 / TIM21_CH1 (AF6) */
#define PIN_ENC_PORT            GPIOB
#define PIN_ENC_PIN             4U
#define PIN_ENC_AF              6U

/* Cartridge empty LED: PB5 */
#define PIN_LED_CART_PORT       GPIOB
#define PIN_LED_CART_PIN        5U

/* SWD: PA13 (SWDIO), PA14 (SWCLK) — reserved */

#endif /* PINMAP_H */
