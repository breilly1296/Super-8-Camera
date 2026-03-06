/**
 * motor_control.h — PID Motor Speed Controller
 *
 * Closed-loop PID speed control for the Mabuchi FF-130SH driving the
 * Super 8 film transport through a 15:1 gear reduction.
 *
 * Features:
 *   - Open-loop startup ramp until first encoder feedback
 *   - PID with anti-windup and filtered derivative
 *   - Per-cycle duty rate limiting for smooth transitions
 *   - Soft stop deceleration ramp
 *   - Stall fault detection and recovery
 *
 * All constants from config.h; all pins from pinmap.h.
 */

#ifndef MOTOR_CONTROL_H
#define MOTOR_CONTROL_H

#include <stdint.h>

/* Motor operating states (visible for telemetry) */
typedef enum {
    MOTOR_IDLE,         /* motor off, PWM at 0                          */
    MOTOR_RAMP_UP,      /* open-loop soft start, duty climbing           */
    MOTOR_RUNNING,      /* closed-loop PID active                        */
    MOTOR_RAMP_DOWN,    /* soft stop, duty decreasing                    */
    MOTOR_FAULT         /* stall detected — motor killed                 */
} motor_state_t;

/** One-time hardware init: TIM2 PWM, motor GPIO, encoder. */
void motor_init(void);

/**
 * Call from the superloop on every tick.  Internally rate-limits
 * PID to PID_INTERVAL_MS and ramp steps to RAMP_INTERVAL_MS.
 */
void motor_update(void);

/** Start the motor (transition IDLE → RAMP_UP).  No-op if already running. */
void motor_start(void);

/** Request a soft stop (transition → RAMP_DOWN). */
void motor_stop(void);

/** Emergency stop: PWM to 0 immediately, no ramp. */
void motor_emergency_stop(void);

/** Current measured FPS from encoder (0 if stopped). */
float motor_get_fps(void);

/** Current PWM duty cycle (0 .. PWM_DUTY_MAX). */
uint16_t motor_get_duty(void);

/** Current motor state. */
motor_state_t motor_get_state(void);

/** Non-zero if in FAULT state. */
uint8_t motor_is_stalled(void);

/** Clear a stall fault and return to IDLE. */
void motor_clear_fault(void);

/** Read the target FPS from the FPS select switch. */
uint32_t motor_read_target_fps(void);

#endif /* MOTOR_CONTROL_H */
