/**
 * motor_control.c — Super 8 Camera DC Motor Speed Controller
 *
 * Closed-loop PID control of a DC motor driving Super 8 film transport.
 * Speed feedback from a slotted-disc optical encoder (1 slot per frame)
 * read via TIM21 input capture.  PWM drive via TIM2 CH1.
 *
 * Target: STM32L0xx at 16 MHz (MSI or HSI).  Bare-register access.
 *
 * Connections:
 *   PA0  TIM2_CH1   → motor driver PWM input
 *   PB4  TIM21_CH1  ← encoder photointerrupter output
 *   PA1              ← FPS select switch (low=18, high=24)
 *   PA2              ← trigger button (active low)
 *   PA3              → stall / fault LED
 *
 * Copyright (c) 2026 — released under MIT license.
 */

#include "motor_control.h"

/* -----------------------------------------------------------------------
 * STM32L0 register-level includes
 * If building outside of a vendor CMSIS tree, replace with your header.
 * ----------------------------------------------------------------------- */
#include "stm32l0xx.h"

/* -----------------------------------------------------------------------
 * Internal state
 * ----------------------------------------------------------------------- */

/** Motor operating states. */
typedef enum {
    STATE_IDLE,       /* motor off, waiting for trigger                      */
    STATE_RAMP_UP,    /* soft-start ramp: duty increasing toward set-point   */
    STATE_RUNNING,    /* closed-loop PID active                              */
    STATE_RAMP_DOWN,  /* trigger released, decelerating to stop              */
    STATE_FAULT       /* stall detected — motor killed                       */
} motor_state_t;

static volatile motor_state_t  state         = STATE_IDLE;

/* Encoder capture data (written in ISR, read in main loop) */
static volatile uint32_t       enc_period_us = 0;  /* latest pulse period   */
static volatile uint32_t       enc_last_cap  = 0;  /* previous capture val  */
static volatile uint8_t        enc_new_data  = 0;  /* flag: fresh capture   */

/* Timing helpers (driven by SysTick) */
static volatile uint32_t       tick_ms       = 0;

/* PID state */
static float  pid_integral   = 0.0f;
static float  pid_prev_error = 0.0f;
static float  measured_fps   = 0.0f;

/* Current PWM duty (0 .. PWM_TIM_PERIOD) */
static uint16_t current_duty = 0;

/* Stall watchdog: ms timestamp of last encoder pulse */
static uint32_t last_pulse_ms = 0;

/* -----------------------------------------------------------------------
 * Low-level helpers
 * ----------------------------------------------------------------------- */

static inline uint32_t millis(void)
{
    return tick_ms;
}

/** Read the FPS select switch.  Returns FPS_HIGH or FPS_LOW. */
static inline uint32_t read_target_fps(void)
{
    return (GPIOA->IDR & (1U << FPS_PIN)) ? FPS_HIGH : FPS_LOW;
}

/** Return non-zero when the trigger is pressed (active low). */
static inline uint8_t trigger_pressed(void)
{
    return !(GPIOA->IDR & (1U << TRIGGER_PIN));
}

/** Set PWM duty cycle (0 .. PWM_TIM_PERIOD). */
static void set_duty(uint16_t duty)
{
    if (duty > PWM_DUTY_MAX)
        duty = PWM_DUTY_MAX;
    TIM2->CCR1 = duty;
    current_duty = duty;
}

/** Turn the fault LED on or off. */
static inline void fault_led(uint8_t on)
{
    if (on)
        GPIOA->BSRR = (1U << FAULT_LED_PIN);
    else
        GPIOA->BSRR = (1U << (FAULT_LED_PIN + 16));  /* reset */
}

/* -----------------------------------------------------------------------
 * PID controller
 *
 * Input:  target fps, measured fps
 * Output: PWM duty adjustment (clamped to [PWM_DUTY_MIN .. PWM_DUTY_MAX])
 * ----------------------------------------------------------------------- */

static uint16_t pid_compute(float target, float actual)
{
    float error = target - actual;

    /* Proportional */
    float p_term = PID_KP * error;

    /* Integral with anti-windup clamp */
    pid_integral += PID_KI * error * ((float)PID_INTERVAL_MS / 1000.0f);
    if (pid_integral >  PID_I_CLAMP) pid_integral =  PID_I_CLAMP;
    if (pid_integral < -PID_I_CLAMP) pid_integral = -PID_I_CLAMP;

    /* Derivative (on error, not measurement — acceptable for this use) */
    float d_term = PID_KD * (error - pid_prev_error) /
                   ((float)PID_INTERVAL_MS / 1000.0f);
    pid_prev_error = error;

    /* Sum and clamp to valid duty range */
    float output = (float)current_duty + p_term + pid_integral + d_term;
    if (output < (float)PWM_DUTY_MIN) output = (float)PWM_DUTY_MIN;
    if (output > (float)PWM_DUTY_MAX) output = (float)PWM_DUTY_MAX;

    return (uint16_t)output;
}

static void pid_reset(void)
{
    pid_integral   = 0.0f;
    pid_prev_error = 0.0f;
}

/* -----------------------------------------------------------------------
 * Hardware initialisation
 * ----------------------------------------------------------------------- */

/** Configure SysTick for 1 ms interrupts at 16 MHz. */
static void systick_init(void)
{
    SysTick->LOAD = 16000U - 1U;          /* 16 MHz / 16000 = 1 kHz        */
    SysTick->VAL  = 0;
    SysTick->CTRL = SysTick_CTRL_CLKSOURCE_Msk |
                    SysTick_CTRL_TICKINT_Msk    |
                    SysTick_CTRL_ENABLE_Msk;
}

/** Configure GPIOs: PWM out, encoder in, switch, trigger, LED. */
static void gpio_init(void)
{
    /* Enable GPIOA and GPIOB clocks */
    RCC->IOPENR |= RCC_IOPENR_GPIOAEN | RCC_IOPENR_GPIOBEN;

    /* --- PA0: TIM2_CH1 alternate function (AF2), push-pull --------------- */
    GPIOA->MODER   = (GPIOA->MODER   & ~(3U << (PWM_PIN * 2)))
                    |  (2U << (PWM_PIN * 2));          /* AF mode            */
    GPIOA->AFR[0]  = (GPIOA->AFR[0]  & ~(0xFU << (PWM_PIN * 4)))
                    |  (PWM_AF << (PWM_PIN * 4));      /* AF2                */

    /* --- PB4: TIM21_CH1 alternate function (AF6) ------------------------ */
    GPIOB->MODER   = (GPIOB->MODER   & ~(3U << (ENC_PIN * 2)))
                    |  (2U << (ENC_PIN * 2));          /* AF mode            */
    GPIOB->AFR[0]  = (GPIOB->AFR[0]  & ~(0xFU << (ENC_PIN * 4)))
                    |  (ENC_AF << (ENC_PIN * 4));      /* AF6                */

    /* --- PA1: FPS select — input with pull-down ------------------------- */
    GPIOA->MODER  &= ~(3U << (FPS_PIN * 2));          /* input              */
    GPIOA->PUPDR   = (GPIOA->PUPDR & ~(3U << (FPS_PIN * 2)))
                    |  (2U << (FPS_PIN * 2));          /* pull-down          */

    /* --- PA2: Trigger — input (external pull-up assumed) ----------------- */
    GPIOA->MODER  &= ~(3U << (TRIGGER_PIN * 2));      /* input              */

    /* --- PA3: Fault LED — output push-pull ------------------------------ */
    GPIOA->MODER   = (GPIOA->MODER & ~(3U << (FAULT_LED_PIN * 2)))
                    |  (1U << (FAULT_LED_PIN * 2));    /* output             */
    fault_led(0);
}

/**
 * Configure TIM2 CH1 for PWM output.
 * 16 MHz / (PSC+1) / (ARR+1) = 16 MHz / 16 / 1000 = 1 kHz PWM.
 */
static void pwm_init(void)
{
    RCC->APB1ENR |= RCC_APB1ENR_TIM2EN;

    TIM2->PSC  = PWM_TIM_PRESCALER;
    TIM2->ARR  = PWM_TIM_PERIOD;
    TIM2->CCR1 = 0;                             /* start at 0 % duty        */

    /* CH1: PWM mode 1 (OCxM = 0b110), preload enable */
    TIM2->CCMR1 = (TIM2->CCMR1 & ~(0x7FU))
                 | TIM_CCMR1_OC1M_2 | TIM_CCMR1_OC1M_1
                 | TIM_CCMR1_OC1PE;

    TIM2->CCER |= TIM_CCER_CC1E;                /* enable CH1 output        */
    TIM2->CR1  |= TIM_CR1_ARPE;                 /* buffered ARR             */
    TIM2->EGR   = TIM_EGR_UG;                   /* load shadow registers    */
    TIM2->CR1  |= TIM_CR1_CEN;                  /* start timer              */
}

/**
 * Configure TIM21 CH1 for input capture on rising edge.
 * 16 MHz / 16 = 1 MHz → 1 µs resolution.
 * 16-bit counter wraps at 65 536 µs (~15 fps minimum before wrap).
 * The capture interrupt computes pulse-to-pulse period.
 */
static void encoder_init(void)
{
    RCC->APB2ENR |= RCC_APB2ENR_TIM21EN;

    TIM21->PSC  = ENC_TIM_PRESCALER;
    TIM21->ARR  = 0xFFFF;                       /* free-running 16-bit      */

    /* CH1 mapped to TI1, no filter, no prescaler */
    TIM21->CCMR1 = (TIM21->CCMR1 & ~0xFFU)
                  | TIM_CCMR1_CC1S_0;           /* CC1 = TI1                */

    /* Rising edge capture */
    TIM21->CCER &= ~(TIM_CCER_CC1P | TIM_CCER_CC1NP);
    TIM21->CCER |=  TIM_CCER_CC1E;              /* enable capture           */

    /* Enable capture interrupt */
    TIM21->DIER |= TIM_DIER_CC1IE;
    NVIC_EnableIRQ(TIM21_IRQn);
    NVIC_SetPriority(TIM21_IRQn, 1);

    TIM21->EGR  = TIM_EGR_UG;
    TIM21->CR1 |= TIM_CR1_CEN;
}

/* -----------------------------------------------------------------------
 * Interrupt handlers
 * ----------------------------------------------------------------------- */

/** SysTick: 1 ms tick for timing. */
void SysTick_Handler(void)
{
    tick_ms++;
}

/** TIM21 capture: compute encoder pulse period in microseconds. */
void TIM21_IRQHandler(void)
{
    if (TIM21->SR & TIM_SR_CC1IF) {
        TIM21->SR = ~TIM_SR_CC1IF;              /* clear flag               */

        uint32_t cap = TIM21->CCR1;
        uint32_t diff;

        /* Handle 16-bit wrap-around */
        if (cap >= enc_last_cap)
            diff = cap - enc_last_cap;
        else
            diff = (0xFFFFU - enc_last_cap) + cap + 1U;

        enc_last_cap  = cap;
        enc_period_us = diff;                    /* period in µs             */
        enc_new_data  = 1;
        last_pulse_ms = tick_ms;                 /* reset stall watchdog     */
    }
}

/* -----------------------------------------------------------------------
 * Public API
 * ----------------------------------------------------------------------- */

void motor_init(void)
{
    systick_init();
    gpio_init();
    pwm_init();
    encoder_init();

    state        = STATE_IDLE;
    current_duty = 0;
    set_duty(0);
    pid_reset();
    fault_led(0);
    last_pulse_ms = millis();
}

void motor_update(void)
{
    static uint32_t next_pid_ms  = 0;
    static uint32_t next_ramp_ms = 0;

    uint32_t now = millis();

    switch (state) {

    /* ---- IDLE: motor off, watch for trigger --------------------------- */
    case STATE_IDLE:
        if (trigger_pressed()) {
            /* Begin soft-start ramp */
            pid_reset();
            current_duty  = PWM_DUTY_MIN;
            set_duty(current_duty);
            next_ramp_ms  = now + RAMP_INTERVAL_MS;
            last_pulse_ms = now;                 /* reset stall watchdog     */
            state = STATE_RAMP_UP;
        }
        break;

    /* ---- RAMP UP: gently increase duty until first encoder pulses ---- */
    case STATE_RAMP_UP:
        if (!trigger_pressed()) {
            /* Trigger released during ramp — abort to soft stop */
            state = STATE_RAMP_DOWN;
            next_ramp_ms = now + STOP_INTERVAL_MS;
            break;
        }

        if (now >= next_ramp_ms) {
            next_ramp_ms = now + RAMP_INTERVAL_MS;

            /* Estimate a reasonable open-loop duty for the target fps.
             * Use ~40 % as a rough midpoint and ramp toward it. */
            uint16_t target_duty = (uint16_t)(PWM_DUTY_MAX * 0.40f);

            if (current_duty < target_duty) {
                current_duty += RAMP_STEP;
                if (current_duty > target_duty)
                    current_duty = target_duty;
                set_duty(current_duty);
            }

            /* Once we have encoder feedback, hand off to PID */
            if (enc_new_data) {
                enc_new_data = 0;
                next_pid_ms  = now + PID_INTERVAL_MS;
                state = STATE_RUNNING;
            }
        }

        /* Stall check during ramp — motor might be jammed */
        if ((now - last_pulse_ms) > STALL_TIMEOUT_MS * 3U) {
            /* Allow 3x timeout during startup for initial inertia */
            set_duty(0);
            fault_led(1);
            state = STATE_FAULT;
        }
        break;

    /* ---- RUNNING: closed-loop PID ------------------------------------ */
    case STATE_RUNNING:
        /* Trigger released → begin soft stop */
        if (!trigger_pressed()) {
            state = STATE_RAMP_DOWN;
            next_ramp_ms = now + STOP_INTERVAL_MS;
            break;
        }

        /* Stall detection */
        if ((now - last_pulse_ms) > STALL_TIMEOUT_MS) {
            set_duty(0);
            pid_reset();
            fault_led(1);
            state = STATE_FAULT;
            break;
        }

        /* PID update at fixed interval */
        if (now >= next_pid_ms) {
            next_pid_ms = now + PID_INTERVAL_MS;

            /* Compute measured fps from encoder period.
             * fps = 1 000 000 / period_us  (one pulse per frame). */
            uint32_t period = enc_period_us;     /* snapshot volatile        */
            if (period > 0)
                measured_fps = 1000000.0f / (float)period;
            else
                measured_fps = 0.0f;

            float target = (float)read_target_fps();
            uint16_t new_duty = pid_compute(target, measured_fps);
            set_duty(new_duty);
        }
        break;

    /* ---- RAMP DOWN: soft stop after trigger release ------------------- */
    case STATE_RAMP_DOWN:
        if (now >= next_ramp_ms) {
            next_ramp_ms = now + STOP_INTERVAL_MS;

            if (current_duty > STOP_STEP)
                current_duty -= STOP_STEP;
            else
                current_duty = 0;

            set_duty(current_duty);

            if (current_duty == 0) {
                pid_reset();
                state = STATE_IDLE;
            }
        }
        break;

    /* ---- FAULT: motor killed, wait for user acknowledgement ----------- */
    case STATE_FAULT:
        set_duty(0);
        /* Blink LED at ~2 Hz */
        fault_led((now / 250U) & 1U);
        /* Fault clears via motor_clear_fault() or when trigger is
         * released, allowing a retry. */
        if (!trigger_pressed()) {
            motor_clear_fault();
        }
        break;
    }
}

float motor_get_fps(void)
{
    return measured_fps;
}

uint8_t motor_is_stalled(void)
{
    return (state == STATE_FAULT) ? 1U : 0U;
}

void motor_clear_fault(void)
{
    if (state == STATE_FAULT) {
        set_duty(0);
        pid_reset();
        fault_led(0);
        state = STATE_IDLE;
    }
}

/* -----------------------------------------------------------------------
 * Minimal main() — integrate into your own project entry point as needed.
 * ----------------------------------------------------------------------- */

#ifdef MOTOR_CONTROL_STANDALONE

int main(void)
{
    /* If using HSI16 at 16 MHz (default on many L0 boards), no PLL setup
     * is required.  Add your SystemInit / clock config here if needed.  */

    motor_init();

    for (;;) {
        motor_update();
    }
}

#endif /* MOTOR_CONTROL_STANDALONE */
