/**
 * motor_control.h — Super 8 Camera DC Motor Speed Controller
 *
 * Closed-loop PID speed control for film transport at 18 or 24 fps.
 * Target: STM32L0xx (bare-register access, no HAL dependency).
 *
 * Hardware mapping:
 *   PA0  — TIM2 CH1  PWM output  (motor driver)
 *   PB4  — TIM21 CH1 input capture (optical encoder, 1 pulse/frame)
 *   PA1  — FPS select toggle switch (low = 18fps, high = 24fps)
 *   PA2  — Trigger button (active low, external pull-up)
 *   PA3  — Stall/fault LED output (active high)
 */

#ifndef MOTOR_CONTROL_H
#define MOTOR_CONTROL_H

#include <stdint.h>

/* -----------------------------------------------------------------------
 * Tunable parameters — tweak these for your mechanical setup
 * ----------------------------------------------------------------------- */

/* Frame rates */
#define FPS_LOW                 18U
#define FPS_HIGH                24U

/* PID gains (fixed-point × 1024 internally; these are floating for clarity) */
#define PID_KP                  1.8f
#define PID_KI                  0.9f
#define PID_KD                  0.05f

/* PID integral windup clamp (duty cycle units, 0–999) */
#define PID_I_CLAMP             400.0f

/* PWM timer (TIM2) */
#define PWM_TIM_PRESCALER       15U       /* 16 MHz / 16 = 1 MHz tick          */
#define PWM_TIM_PERIOD          999U      /* 1 MHz / 1000 = 1 kHz PWM          */
#define PWM_DUTY_MIN            50U       /* minimum duty to overcome friction  */
#define PWM_DUTY_MAX            999U      /* maximum duty (100 %)              */

/* Startup ramp */
#define RAMP_STEP               5U        /* duty increment per ramp tick       */
#define RAMP_INTERVAL_MS        10U       /* ms between ramp steps              */

/* Soft-stop deceleration */
#define STOP_STEP               8U        /* duty decrement per tick            */
#define STOP_INTERVAL_MS        8U        /* ms between stop steps              */

/* Stall detection */
#define STALL_TIMEOUT_MS        200U      /* kill motor if no pulse in this time*/

/* Encoder input capture timer (TIM21) prescaler.
 * 16 MHz / 16 = 1 MHz capture clock → 1 µs resolution.
 * At 24 fps the period is ~41 666 µs, fits in 16-bit counter. */
#define ENC_TIM_PRESCALER       15U

/* Control loop interval */
#define PID_INTERVAL_MS         20U       /* run PID every 20 ms (50 Hz)       */

/* -----------------------------------------------------------------------
 * Pin / peripheral assignments
 * ----------------------------------------------------------------------- */

/* PWM output: PA0 / TIM2_CH1 (AF2) */
#define PWM_PORT_RCC_BIT        (1U << 0)                 /* GPIOA             */
#define PWM_PIN                 0U
#define PWM_AF                  2U                         /* AF2 = TIM2        */

/* Encoder input: PB4 / TIM21_CH1 (AF6) */
#define ENC_PORT_RCC_BIT        (1U << 1)                 /* GPIOB             */
#define ENC_PIN                 4U
#define ENC_AF                  6U                         /* AF6 = TIM21       */

/* FPS select: PA1, digital input with internal pull-down */
#define FPS_PIN                 1U

/* Trigger: PA2, active-low with external pull-up */
#define TRIGGER_PIN             2U

/* Fault LED: PA3, push-pull output */
#define FAULT_LED_PIN           3U

/* -----------------------------------------------------------------------
 * Public API
 * ----------------------------------------------------------------------- */

/** One-time hardware init — call from main() before the loop. */
void motor_init(void);

/** Call from the superloop as fast as possible.
 *  Handles PID updates, ramp, stop, and stall detection. */
void motor_update(void);

/** Read back the most recent measured fps (for telemetry / debug). */
float motor_get_fps(void);

/** Returns 1 if the motor is in a stall-fault state. */
uint8_t motor_is_stalled(void);

/** Clear a stall fault (call after the operator acknowledges). */
void motor_clear_fault(void);

#endif /* MOTOR_CONTROL_H */
