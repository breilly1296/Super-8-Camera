/**
 * motor_control.c — PID Closed-Loop DC Motor Speed Controller
 *
 * Drives the Mabuchi FF-130SH via TIM2 CH1 PWM.  Speed feedback from
 * the encoder module (TIM21 input capture, 4-sample average).
 *
 * Startup sequence:
 *   1. motor_start() → state = RAMP_UP, duty = PWM_DUTY_MIN
 *   2. Duty ramps at RAMP_STEP per RAMP_INTERVAL_MS toward 40% target
 *   3. On first encoder feedback → state = RUNNING, PID takes over
 *
 * PID features:
 *   - Anti-windup: integral clamped to ±PID_I_CLAMP
 *   - Derivative filter: first-order low-pass (alpha = PID_D_FILTER_ALPHA)
 *   - Rate limiting: duty change capped to ±PID_DUTY_RATE_LIMIT per cycle
 *
 * All constants from config.h; all pins from pinmap.h.
 *
 * Copyright (c) 2026 — released under MIT license.
 */

#include "motor_control.h"
#include "encoder.h"
#include "config.h"
#include "pinmap.h"
#include "stm32l0xx.h"

/* Global tick from main.c */
extern volatile uint32_t g_tick_ms;

/* =====================================================================
 * Internal state
 * ===================================================================== */

static motor_state_t mstate       = MOTOR_IDLE;
static uint16_t      current_duty = 0;
static float         measured_fps = 0.0f;

/* PID state */
static float pid_integral   = 0.0f;
static float pid_prev_error = 0.0f;
static float pid_d_filtered = 0.0f;

/* Timing */
static uint32_t next_pid_ms  = 0;
static uint32_t next_ramp_ms = 0;

/* =====================================================================
 * Low-level helpers
 * ===================================================================== */

/** Set PWM duty cycle (clamped to 0 .. PWM_DUTY_MAX). */
static void set_duty(uint16_t d)
{
    if (d > PWM_DUTY_MAX) d = PWM_DUTY_MAX;
    TIM2->CCR1   = d;
    current_duty = d;
}

/** Reset PID accumulator state. */
static void pid_reset(void)
{
    pid_integral   = 0.0f;
    pid_prev_error = 0.0f;
    pid_d_filtered = 0.0f;
}

/** Fault LED on PA3. */
static inline void fault_led(uint8_t on)
{
    if (on) PIN_LED_WARN_PORT->BSRR = (1U << PIN_LED_WARN_PIN);
    else    PIN_LED_WARN_PORT->BSRR = (1U << (PIN_LED_WARN_PIN + 16));
}

/* =====================================================================
 * PID controller
 *
 * Input:  target fps, measured fps
 * Output: new PWM duty value
 *
 * Anti-windup:    integral clamped to ±PID_I_CLAMP
 * Derivative:     low-pass filtered (alpha blend with previous)
 * Rate limiting:  output change capped to ±PID_DUTY_RATE_LIMIT
 * ===================================================================== */

static uint16_t pid_compute(float target, float actual)
{
    float error = target - actual;
    float dt    = (float)PID_INTERVAL_MS / 1000.0f;

    /* Proportional */
    float p_term = PID_KP * error;

    /* Integral with anti-windup */
    pid_integral += PID_KI * error * dt;
    if (pid_integral >  PID_I_CLAMP) pid_integral =  PID_I_CLAMP;
    if (pid_integral < -PID_I_CLAMP) pid_integral = -PID_I_CLAMP;

    /* Derivative with low-pass filter */
    float d_raw = PID_KD * (error - pid_prev_error) / dt;
    pid_d_filtered = PID_D_FILTER_ALPHA * d_raw
                   + (1.0f - PID_D_FILTER_ALPHA) * pid_d_filtered;
    pid_prev_error = error;

    /* Sum PID terms */
    float output = (float)current_duty + p_term + pid_integral + pid_d_filtered;

    /* Clamp to valid duty range */
    if (output < (float)PWM_DUTY_MIN) output = (float)PWM_DUTY_MIN;
    if (output > (float)PWM_DUTY_MAX) output = (float)PWM_DUTY_MAX;

    /* Rate limiting: restrict change per PID cycle */
    uint16_t new_duty = (uint16_t)output;
    if (new_duty > current_duty + PID_DUTY_RATE_LIMIT)
        new_duty = current_duty + PID_DUTY_RATE_LIMIT;
    else if (current_duty > PID_DUTY_RATE_LIMIT &&
             new_duty < current_duty - PID_DUTY_RATE_LIMIT)
        new_duty = current_duty - PID_DUTY_RATE_LIMIT;

    return new_duty;
}

/* =====================================================================
 * Hardware Init
 * ===================================================================== */

void motor_init(void)
{
    /* Enable clocks */
    RCC->IOPENR  |= RCC_IOPENR_GPIOAEN;
    RCC->APB1ENR |= RCC_APB1ENR_TIM2EN;

    /* PA0: TIM2_CH1 alternate function (AF2), push-pull */
    PIN_PWM_MOTOR_PORT->MODER =
        (PIN_PWM_MOTOR_PORT->MODER & ~(3U << (PIN_PWM_MOTOR_PIN * 2)))
        | (2U << (PIN_PWM_MOTOR_PIN * 2));
    PIN_PWM_MOTOR_PORT->AFR[0] =
        (PIN_PWM_MOTOR_PORT->AFR[0] & ~(0xFU << (PIN_PWM_MOTOR_PIN * 4)))
        | (PIN_PWM_MOTOR_AF << (PIN_PWM_MOTOR_PIN * 4));

    /* PA3: fault LED — output push-pull */
    PIN_LED_WARN_PORT->MODER =
        (PIN_LED_WARN_PORT->MODER & ~(3U << (PIN_LED_WARN_PIN * 2)))
        | (1U << (PIN_LED_WARN_PIN * 2));
    fault_led(0);

    /* TIM2: PWM mode 1 on CH1
     * 16 MHz / (15+1) / (999+1) = 1 kHz */
    TIM2->PSC  = PWM_TIM_PRESCALER;
    TIM2->ARR  = PWM_TIM_PERIOD;
    TIM2->CCR1 = 0;

    TIM2->CCMR1 = (TIM2->CCMR1 & ~0x7FU)
                 | TIM_CCMR1_OC1M_2 | TIM_CCMR1_OC1M_1
                 | TIM_CCMR1_OC1PE;

    TIM2->CCER |= TIM_CCER_CC1E;
    TIM2->CR1  |= TIM_CR1_ARPE;
    TIM2->EGR   = TIM_EGR_UG;
    TIM2->CR1  |= TIM_CR1_CEN;

    /* Init encoder subsystem */
    encoder_init();

    /* Zero motor state */
    mstate       = MOTOR_IDLE;
    current_duty = 0;
    measured_fps = 0.0f;
    pid_reset();
}

/* =====================================================================
 * State Machine Update — call from superloop every tick
 * ===================================================================== */

void motor_update(void)
{
    uint32_t now = g_tick_ms;

    /* Update last-pulse tracking from encoder */
    if (encoder_has_new_data()) {
        /* Don't clear here — let state_machine also see the flag */
    }

    switch (mstate) {

    /* ---- IDLE: motor off -------------------------------------------- */
    case MOTOR_IDLE:
        /* Nothing to do — motor_start() transitions out of IDLE */
        break;

    /* ---- RAMP UP: open-loop startup --------------------------------- */
    case MOTOR_RAMP_UP:
        if (now >= next_ramp_ms) {
            next_ramp_ms = now + RAMP_INTERVAL_MS;

            uint16_t target_duty = (uint16_t)(PWM_DUTY_MAX *
                                              RAMP_TARGET_PCT / 100U);

            if (current_duty < target_duty) {
                current_duty += RAMP_STEP;
                if (current_duty > target_duty)
                    current_duty = target_duty;
                set_duty(current_duty);
            }

            /* Once encoder feedback arrives, hand off to PID */
            if (encoder_has_new_data()) {
                encoder_clear_new_data();
                next_pid_ms = now + PID_INTERVAL_MS;
                mstate = MOTOR_RUNNING;
            }
        }

        /* Stall check during startup (3× normal timeout for inertia) */
        if (encoder_is_stalled(now, STALL_TIMEOUT_MS * STALL_STARTUP_MULT)) {
            set_duty(0);
            fault_led(1);
            mstate = MOTOR_FAULT;
        }
        break;

    /* ---- RUNNING: closed-loop PID ----------------------------------- */
    case MOTOR_RUNNING:
        /* Stall detection */
        if (encoder_is_stalled(now, STALL_TIMEOUT_MS)) {
            set_duty(0);
            pid_reset();
            fault_led(1);
            mstate = MOTOR_FAULT;
            break;
        }

        /* PID update at fixed interval */
        if (now >= next_pid_ms) {
            next_pid_ms = now + PID_INTERVAL_MS;

            /* Read averaged FPS from encoder */
            measured_fps = encoder_get_fps();

            float target = (float)motor_read_target_fps();
            uint16_t new_duty = pid_compute(target, measured_fps);
            set_duty(new_duty);
        }
        break;

    /* ---- RAMP DOWN: soft stop --------------------------------------- */
    case MOTOR_RAMP_DOWN:
        if (now >= next_ramp_ms) {
            next_ramp_ms = now + STOP_INTERVAL_MS;

            if (current_duty > STOP_STEP)
                current_duty -= STOP_STEP;
            else
                current_duty = 0;

            set_duty(current_duty);

            if (current_duty == 0) {
                pid_reset();
                measured_fps = 0.0f;
                mstate = MOTOR_IDLE;
            }
        }
        break;

    /* ---- FAULT: motor killed ---------------------------------------- */
    case MOTOR_FAULT:
        set_duty(0);
        /* Blink fault LED at ~2 Hz */
        fault_led((now / 250U) & 1U);
        break;
    }
}

/* =====================================================================
 * Public API
 * ===================================================================== */

void motor_start(void)
{
    if (mstate != MOTOR_IDLE) return;

    pid_reset();
    current_duty = PWM_DUTY_MIN;
    set_duty(current_duty);
    next_ramp_ms = g_tick_ms + RAMP_INTERVAL_MS;
    encoder_reset_frame_count();
    mstate = MOTOR_RAMP_UP;
}

void motor_stop(void)
{
    if (mstate == MOTOR_RUNNING || mstate == MOTOR_RAMP_UP) {
        next_ramp_ms = g_tick_ms + STOP_INTERVAL_MS;
        mstate = MOTOR_RAMP_DOWN;
    }
}

void motor_emergency_stop(void)
{
    TIM2->CCR1   = 0;
    current_duty = 0;
    measured_fps = 0.0f;
    pid_reset();
    fault_led(0);
    mstate = MOTOR_IDLE;
}

float motor_get_fps(void)
{
    return measured_fps;
}

uint16_t motor_get_duty(void)
{
    return current_duty;
}

motor_state_t motor_get_state(void)
{
    return mstate;
}

uint8_t motor_is_stalled(void)
{
    return (mstate == MOTOR_FAULT) ? 1U : 0U;
}

void motor_clear_fault(void)
{
    if (mstate == MOTOR_FAULT) {
        set_duty(0);
        pid_reset();
        fault_led(0);
        measured_fps = 0.0f;
        mstate = MOTOR_IDLE;
    }
}

uint32_t motor_read_target_fps(void)
{
    return (PIN_FPS_SEL_PORT->IDR & (1U << PIN_FPS_SEL_PIN))
           ? FPS_HIGH : FPS_LOW;
}
