/**
 * config.h — Firmware configuration constants
 *
 * Generated from super8cam.specs.master_specs.  Do not edit manually —
 * regenerate with build.py if specs change.
 */

#ifndef CONFIG_H
#define CONFIG_H

/* Frame rates */
#define FPS_LOW                 18U
#define FPS_HIGH                24U

/* PID gains */
#define PID_KP                  1.8f
#define PID_KI                  0.9f
#define PID_KD                  0.05f
#define PID_I_CLAMP             400.0f
#define PID_INTERVAL_MS         20U

/* PWM */
#define PWM_TIM_PRESCALER       15U
#define PWM_TIM_PERIOD          999U
#define PWM_DUTY_MIN            50U
#define PWM_DUTY_MAX            999U

/* Startup ramp */
#define RAMP_STEP               5U
#define RAMP_INTERVAL_MS        10U

/* Stall detection */
#define STALL_TIMEOUT_MS        200U

/* Encoder */
#define ENC_TIM_PRESCALER       15U

/* ADC / Metering */
#define METER_ADC_CHANNEL       7U
#define METER_SAMPLE_HZ         100U
#define METER_FILTER_SIZE       16U
#define ADC_VREF_MV             3300U
#define ADC_RESOLUTION          4096U

/* Battery */
#define VBAT_LOW_THRESHOLD_MV   4200U

/* Cartridge end detection */
#define CART_EMPTY_FRAME_LIMIT  5U
#define CART_FRAME_TIMEOUT_MS   250U

#endif /* CONFIG_H */
