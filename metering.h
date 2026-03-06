/**
 * metering.h — Super 8 Camera Light Meter / Exposure Calculator
 *
 * Reads a BPW34 photodiode via transimpedance amplifier on ADC CH0.
 * Computes EV, derives the required f-stop for the current film speed
 * and shutter speed, drives a galvanometer via PWM, and indicates
 * exposure status on green/red LEDs.
 *
 * Target: STM32L0xx at 16 MHz, bare-register access.
 *
 * Hardware mapping:
 *   PA0  — ADC_IN0   photodiode / TIA output (analog input)
 *   PA4  — TIM22 CH1 PWM output to galvanometer needle
 *   PA5  — green LED  (correct exposure, ±2 EV)
 *   PA6  — red LED    (underexposed > 2 stops)
 *   PB0  — DIP switch bit 0 (ASA select, pulled down)
 *   PB1  — DIP switch bit 1 (ASA select, pulled down)
 *   PA1  — FPS select (low = 18 fps, high = 24 fps) — shared with motor
 */

#ifndef METERING_H
#define METERING_H

#include <stdint.h>

/* -----------------------------------------------------------------------
 * Tunable parameters
 * ----------------------------------------------------------------------- */

/* ADC sampling */
#define METER_ADC_CHANNEL       0U          /* PA0 = ADC_IN0                */
#define METER_SAMPLE_HZ         100U        /* ADC sample rate              */
#define METER_FILTER_SIZE       16U         /* rolling-average window       */

/* ADC reference and resolution */
#define ADC_VREF_MV             3300U       /* VDDA in millivolts           */
#define ADC_RESOLUTION          4096U       /* 12-bit ADC                   */

/* Calibration: number of entries in the voltage → EV lookup table */
#define CAL_TABLE_SIZE          13

/* Galvanometer PWM (TIM22 CH1) */
#define GALVO_PWM_PRESCALER     15U         /* 16 MHz / 16 = 1 MHz         */
#define GALVO_PWM_PERIOD        999U        /* 1 kHz PWM                   */

/* f-stop range the galvanometer needle spans */
#define FSTOP_MIN_X10           14U         /* f/1.4 × 10 = 14             */
#define FSTOP_MAX_X10           220U        /* f/22  × 10 = 220            */

/* Exposure warning threshold */
#define UNDER_WARN_EV           2.0f        /* blink red if > 2 EV under   */

/* LED blink rate when underexposed */
#define RED_BLINK_PERIOD_MS     400U        /* full cycle ms                */

/* Film speed options (ASA / ISO), indexed by 2-bit DIP switch */
#define ASA_COUNT               4U

/* Shutter speeds for 18 fps and 24 fps (with ~180° shutter) */
#define SHUTTER_18FPS           (1.0f / 36.0f)    /* seconds               */
#define SHUTTER_24FPS           (1.0f / 48.0f)    /* seconds               */

/* Pin assignments */
#define GALVO_PIN               4U          /* PA4 — TIM22 CH1 AF4         */
#define GALVO_AF                4U
#define GREEN_LED_PIN           5U          /* PA5                          */
#define RED_LED_PIN             6U          /* PA6                          */
#define DIP_BIT0_PIN            0U          /* PB0                          */
#define DIP_BIT1_PIN            1U          /* PB1                          */
#define FPS_SEL_PIN             1U          /* PA1                          */

/* -----------------------------------------------------------------------
 * Public API
 * ----------------------------------------------------------------------- */

/** One-time init: ADC, timer, GPIOs, calibration table. */
void meter_init(void);

/**
 * Call from superloop as fast as possible.
 * Handles ADC triggering, filtering, EV computation, needle + LEDs.
 */
void meter_update(void);

/** Most recent filtered ADC voltage in millivolts. */
uint32_t meter_get_mv(void);

/** Most recent computed exposure value. */
float meter_get_ev(void);

/** Required f-stop for correct exposure (as float, e.g. 5.6). */
float meter_get_fstop(void);

/** Currently selected ASA from DIP switch. */
uint16_t meter_get_asa(void);

#endif /* METERING_H */
