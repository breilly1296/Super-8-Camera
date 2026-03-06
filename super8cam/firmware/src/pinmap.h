/**
 * pinmap.h — STM32L031K6 pin assignments
 *
 * Single source of truth for all GPIO, ADC channel, and timer AF mappings.
 *
 * Pin    Function                  Peripheral
 * ----   ----------------------    ------------------
 * PA0    Metering photodiode ADC   ADC_IN0
 * PA1    Battery voltage ADC       ADC_IN1 (2:1 divider)
 * PA4    Motor PWM                 TIM2_CH1 (AF2)
 * PA5    Needle galvanometer PWM   TIM2_CH2 (AF2)
 * PA8    Encoder input capture     TIM1_CH1 (AF2, via APR[1])
 * PA11   Cartridge detect switch   GPIO input (pull-up, active low)
 * PA12   Motor enable (H-bridge)   GPIO output
 * PA13   SWDIO                     reserved
 * PA14   SWCLK                     reserved
 * PB0    Trigger button            GPIO input (pull-up, active low)
 * PB1    FPS select switch         GPIO input (pull-up)
 * PB3    Film speed DIP bit 0      GPIO input (pull-up)
 * PB4    Film speed DIP bit 1      GPIO input (pull-up)
 * PB5    Motor direction (IN2)     GPIO output
 * PB6    Warning LED (red)         GPIO output
 * PB7    OK LED (green)            GPIO output
 */

#ifndef PINMAP_H
#define PINMAP_H

#include "stm32l0xx.h"

/* ---- Analog inputs ---- */

/* Metering photodiode: PA0 / ADC_IN0 */
#define PIN_ADC_METER_PORT      GPIOA
#define PIN_ADC_METER_PIN       0U
#define PIN_ADC_METER_CHANNEL   0U

/* Battery voltage: PA1 / ADC_IN1 */
#define PIN_ADC_BATT_PORT       GPIOA
#define PIN_ADC_BATT_PIN        1U
#define PIN_ADC_BATT_CHANNEL    1U

/* ---- PWM outputs ---- */

/* Motor PWM: PA4 / TIM2_CH1 (AF2) */
#define PIN_PWM_MOTOR_PORT      GPIOA
#define PIN_PWM_MOTOR_PIN       4U
#define PIN_PWM_MOTOR_AF        2U

/* Needle galvanometer: PA5 / TIM2_CH2 (AF2) */
#define PIN_PWM_NEEDLE_PORT     GPIOA
#define PIN_PWM_NEEDLE_PIN      5U
#define PIN_PWM_NEEDLE_AF       2U

/* ---- Timer input capture ---- */

/* Encoder: PA8 / TIM1_CH1 (AF2) */
#define PIN_ENC_PORT            GPIOA
#define PIN_ENC_PIN             8U
#define PIN_ENC_AF              2U

/* ---- Digital inputs ---- */

/* Trigger button: PB0 (active low, internal pull-up) */
#define PIN_TRIGGER_PORT        GPIOB
#define PIN_TRIGGER_PIN         0U

/* FPS select: PB1 (low=18fps, high=24fps) */
#define PIN_FPS_SEL_PORT        GPIOB
#define PIN_FPS_SEL_PIN         1U

/* Film speed DIP switches: PB3, PB4 */
#define PIN_DIP0_PORT           GPIOB
#define PIN_DIP0_PIN            3U
#define PIN_DIP1_PORT           GPIOB
#define PIN_DIP1_PIN            4U

/* Cartridge detect: PA11 (active low, internal pull-up) */
#define PIN_CART_DET_PORT       GPIOA
#define PIN_CART_DET_PIN        11U

/* ---- Digital outputs ---- */

/* Motor direction (H-bridge IN2): PB5 */
#define PIN_MOTOR_DIR_PORT      GPIOB
#define PIN_MOTOR_DIR_PIN       5U

/* Motor enable (H-bridge EN): PA12 */
#define PIN_MOTOR_EN_PORT       GPIOA
#define PIN_MOTOR_EN_PIN        12U

/* Warning LED (red): PB6 */
#define PIN_LED_RED_PORT        GPIOB
#define PIN_LED_RED_PIN         6U

/* OK LED (green): PB7 */
#define PIN_LED_GREEN_PORT      GPIOB
#define PIN_LED_GREEN_PIN       7U

/* SWD: PA13 (SWDIO), PA14 (SWCLK) — reserved, do not reconfigure */

#endif /* PINMAP_H */
