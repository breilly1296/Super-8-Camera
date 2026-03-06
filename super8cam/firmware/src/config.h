/**
 * config.h — Super 8 Camera Firmware Configuration
 *
 * Single source of truth for all firmware constants.  Values derived from
 * super8cam/specs/master_specs.py.  Regenerate with build.py if specs change.
 *
 * Organisation:
 *   SYSTEM       Clock, tick, debug
 *   MOTOR / PID  Speed control tuning
 *   ENCODER      Input capture timing
 *   METERING     ADC, calibration LUT, exposure math
 *   BATTERY      Voltage monitoring
 *   CARTRIDGE    End-of-film detection
 *   UI           LEDs, debounce, galvanometer
 */

#ifndef CONFIG_H
#define CONFIG_H

#include <stdint.h>

/* =====================================================================
 * SYSTEM
 * ===================================================================== */

#define SYS_HSI_HZ              16000000U   /* HSI16 oscillator             */
#define SYS_TICK_HZ             1000U       /* SysTick rate (1 ms)          */
#define SYS_TICK_RELOAD         (SYS_HSI_HZ / SYS_TICK_HZ - 1U)  /* 15999  */

/* UART debug output (USART2 on PA9/PA10) */
#define UART_BAUDRATE           115200U
#define UART_DEBUG_INTERVAL_MS  500U        /* telemetry print rate         */

/* =====================================================================
 * FRAME RATES
 * ===================================================================== */

#define FPS_LOW                 18U
#define FPS_HIGH                24U

/* =====================================================================
 * MOTOR PWM  (TIM2 CH1)
 *
 * 16 MHz / (15+1) / (999+1) = 1 kHz PWM
 * ===================================================================== */

#define PWM_TIM_PRESCALER       15U
#define PWM_TIM_PERIOD          999U
#define PWM_DUTY_MIN            50U         /* minimum to overcome friction */
#define PWM_DUTY_MAX            999U        /* 100% duty                    */

/* =====================================================================
 * PID CONTROLLER
 *
 * Tuned for Mabuchi FF-130SH through 15:1 Delrin gearbox.
 * ===================================================================== */

#define PID_KP                  1.8f
#define PID_KI                  0.9f
#define PID_KD                  0.05f
#define PID_INTERVAL_MS         20U         /* PID update rate (50 Hz)      */
#define PID_I_CLAMP             400.0f      /* anti-windup: max |integral|  */
#define PID_D_FILTER_ALPHA      0.3f        /* derivative low-pass: 0=hold, 1=raw */
#define PID_DUTY_RATE_LIMIT     50U         /* max duty change per PID cycle */

/* =====================================================================
 * STARTUP / STOP RAMP
 * ===================================================================== */

#define RAMP_STEP               5U          /* duty increment per ramp tick */
#define RAMP_INTERVAL_MS        10U         /* ms between ramp steps        */
#define RAMP_TARGET_PCT         40U         /* open-loop target as % of max */

#define STOP_STEP               8U          /* duty decrement per stop tick  */
#define STOP_INTERVAL_MS        8U          /* ms between stop steps         */
#define STOP_TIMEOUT_MS         2000U       /* max time to wait for stop     */

/* =====================================================================
 * STALL DETECTION
 * ===================================================================== */

#define STALL_TIMEOUT_MS        200U        /* kill motor if no pulse       */
#define STALL_STARTUP_MULT      3U          /* extra patience during ramp   */

/* =====================================================================
 * ENCODER  (TIM21 CH1 input capture)
 *
 * 16 MHz / (15+1) = 1 MHz → 1 µs resolution.
 * At 24 fps: period ≈ 41 667 µs — fits 16-bit counter (65 535 max).
 * At 18 fps: period ≈ 55 556 µs — fits 16-bit counter.
 * ===================================================================== */

#define ENC_TIM_PRESCALER       15U
#define ENC_AVG_SIZE            4U          /* moving-average window         */

/* =====================================================================
 * ADC / METERING
 * ===================================================================== */

#define METER_ADC_CHANNEL       7U          /* PA7 = ADC_IN7                */
#define METER_SAMPLE_HZ         100U        /* ADC sampling rate            */
#define METER_FILTER_SIZE       16U         /* rolling-average depth        */
#define ADC_VREF_MV             3300U       /* VDDA reference               */
#define ADC_RESOLUTION          4096U       /* 12-bit ADC                   */

/* Calibration LUT: ADC millivolts → EV at ISO 100.
 * Populate from a known-light calibration session with BPW34 + TIA.
 * Must be monotonically increasing in mV. */
#define CAL_TABLE_SIZE          13

/* =====================================================================
 * GALVANOMETER NEEDLE  (TIM22 CH1)
 *
 * Same PWM rate as motor: 1 kHz for smooth needle movement.
 * ===================================================================== */

#define GALVO_PWM_PRESCALER     15U
#define GALVO_PWM_PERIOD        999U

/* f-stop range the needle spans (×10 for integer math) */
#define FSTOP_MIN_X10           14U         /* f/1.4                        */
#define FSTOP_MAX_X10           220U        /* f/22                         */

/* =====================================================================
 * EXPOSURE
 * ===================================================================== */

/* Shutter speeds for 180° opening angle */
#define SHUTTER_18FPS           (1.0f / 36.0f)   /* seconds                */
#define SHUTTER_24FPS           (1.0f / 48.0f)

/* Exposure warning thresholds */
#define UNDER_WARN_EV           2.0f        /* blink red if >2 EV under     */

/* =====================================================================
 * FILM SPEED (ASA/ISO)
 *
 * Selected by 2-bit DIP switch on PB0:PB1.
 * ===================================================================== */

#define ASA_COUNT               4U
/* Values: { 50, 100, 200, 500 } — defined in metering.c */

/* =====================================================================
 * BATTERY MONITORING
 *
 * STM32L0 internal VBAT channel reads through a /2 divider.
 * ===================================================================== */

#define VBAT_ADC_CHANNEL        18U         /* internal VBAT channel        */
#define VBAT_LOW_THRESHOLD_MV   4200U       /* 4×AA end-of-life: 4×1.05V   */
#define VBAT_SAMPLE_INTERVAL_MS 1000U       /* check once per second        */
#define VBAT_DIVIDER            2U          /* internal /2 on L0            */

/* =====================================================================
 * CARTRIDGE END DETECTION
 * ===================================================================== */

#define CART_EMPTY_FRAME_LIMIT  5U          /* consecutive missed frames     */
#define CART_FRAME_TIMEOUT_MS   250U        /* max time per frame            */

/* =====================================================================
 * USER INTERFACE
 * ===================================================================== */

#define DEBOUNCE_MS             30U         /* trigger / FPS switch          */
#define LED_BLINK_PERIOD_MS     400U        /* warning LED full cycle        */
#define WARN_BLINK_PERIOD_MS    500U        /* low-bat / cart-empty blink    */

#endif /* CONFIG_H */
