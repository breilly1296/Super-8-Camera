/**
 * motor_control.c — PID closed-loop DC motor speed controller.
 *
 * Architecture:
 *   - Open-loop ramp for first 500 ms (or until first encoder pulse)
 *   - Closed-loop PID with derivative low-pass filter (alpha=0.1)
 *   - Output rate limiting: max 5% duty change per ms
 *   - Soft-stop: ramp down duty, then brake (both H-bridge high) for 50 ms
 *
 * All constants from config.h; all pins from pinmap.h.
 */

#include "motor_control.h"
#include "encoder.h"
#include "config.h"
#include "pinmap.h"
#include "stm32l0xx.h"

extern volatile uint32_t g_tick_ms;

typedef enum {
    MT_IDLE,
    MT_RAMP,        /* open-loop startup */
    MT_RUN,         /* closed-loop PID */
    MT_STOP,        /* soft-stop ramp down */
    MT_BRAKE,       /* H-bridge braking */
    MT_FAULT
} motor_state_t;

static motor_state_t mstate = MT_IDLE;
static float pid_integral  = 0;
static float pid_prev_err  = 0;
static float pid_d_filtered = 0;
static float measured_fps  = 0;
static uint16_t duty       = 0;
static uint16_t target_duty = 0;   /* for rate limiting */
static uint32_t last_pulse_ms = 0;
static uint32_t ramp_start_ms = 0;
static uint32_t brake_start_ms = 0;

static uint32_t read_target_fps(void)
{
    return (PIN_FPS_SEL_PORT->IDR & (1U << PIN_FPS_SEL_PIN)) ? FPS_HIGH : FPS_LOW;
}

static void set_duty_raw(uint16_t d)
{
    if (d > PWM_DUTY_MAX) d = PWM_DUTY_MAX;
    TIM2->CCR1 = d;
    duty = d;
}

/* Rate-limited duty update: max PID_RATE_LIMIT per ms step */
static void set_duty_limited(uint16_t d)
{
    if (d > PWM_DUTY_MAX) d = PWM_DUTY_MAX;
    target_duty = d;

    int16_t delta = (int16_t)target_duty - (int16_t)duty;
    if (delta > (int16_t)PID_RATE_LIMIT)
        d = duty + PID_RATE_LIMIT;
    else if (delta < -(int16_t)PID_RATE_LIMIT)
        d = (duty > PID_RATE_LIMIT) ? duty - PID_RATE_LIMIT : 0;

    set_duty_raw(d);
}

static uint16_t pid_compute(float target, float actual)
{
    float err = target - actual;

    /* Proportional */
    float p = PID_KP * err;

    /* Integral with anti-windup clamp */
    pid_integral += PID_KI * err * (PID_INTERVAL_MS / 1000.0f);
    if (pid_integral >  PID_I_CLAMP) pid_integral =  PID_I_CLAMP;
    if (pid_integral < -PID_I_CLAMP) pid_integral = -PID_I_CLAMP;

    /* Derivative with low-pass filter */
    float d_raw = (err - pid_prev_err) / (PID_INTERVAL_MS / 1000.0f);
    pid_d_filtered = pid_d_filtered * (1.0f - PID_D_ALPHA) + d_raw * PID_D_ALPHA;
    float d = PID_KD * pid_d_filtered;
    pid_prev_err = err;

    float out = (float)duty + p + pid_integral + d;
    if (out < (float)PWM_DUTY_MIN) out = (float)PWM_DUTY_MIN;
    if (out > (float)PWM_DUTY_MAX) out = (float)PWM_DUTY_MAX;
    return (uint16_t)out;
}

static void reset_pid(void)
{
    pid_integral = 0;
    pid_prev_err = 0;
    pid_d_filtered = 0;
    measured_fps = 0;
}

static void motor_enable(void)
{
    PIN_MOTOR_EN_PORT->BSRR = (1U << PIN_MOTOR_EN_PIN);
    PIN_MOTOR_DIR_PORT->BSRR = (1U << (PIN_MOTOR_DIR_PIN + 16)); /* direction low = forward */
}

void motor_init(void)
{
    /* Enable clocks */
    RCC->IOPENR  |= RCC_IOPENR_GPIOAEN | RCC_IOPENR_GPIOBEN;
    RCC->APB1ENR |= RCC_APB1ENR_TIM2EN;

    /* PA4: AF2 = TIM2_CH1 (motor PWM) */
    GPIOA->MODER  = (GPIOA->MODER  & ~(3U << (PIN_PWM_MOTOR_PIN * 2)))
                   |  (2U << (PIN_PWM_MOTOR_PIN * 2));
    GPIOA->AFR[0] = (GPIOA->AFR[0] & ~(0xFU << (PIN_PWM_MOTOR_PIN * 4)))
                   |  (PIN_PWM_MOTOR_AF << (PIN_PWM_MOTOR_PIN * 4));

    /* PA5: AF2 = TIM2_CH2 (needle PWM) */
    GPIOA->MODER  = (GPIOA->MODER  & ~(3U << (PIN_PWM_NEEDLE_PIN * 2)))
                   |  (2U << (PIN_PWM_NEEDLE_PIN * 2));
    GPIOA->AFR[0] = (GPIOA->AFR[0] & ~(0xFU << (PIN_PWM_NEEDLE_PIN * 4)))
                   |  (PIN_PWM_NEEDLE_AF << (PIN_PWM_NEEDLE_PIN * 4));

    /* Motor direction: PB5 output, push-pull */
    GPIOB->MODER = (GPIOB->MODER & ~(3U << (PIN_MOTOR_DIR_PIN * 2)))
                 |  (1U << (PIN_MOTOR_DIR_PIN * 2));

    /* Motor enable: PA12 output, push-pull */
    GPIOA->MODER = (GPIOA->MODER & ~(3U << (PIN_MOTOR_EN_PIN * 2)))
                 |  (1U << (PIN_MOTOR_EN_PIN * 2));
    PIN_MOTOR_EN_PORT->BSRR = (1U << (PIN_MOTOR_EN_PIN + 16)); /* disable */

    /* TIM2: CH1 (motor) + CH2 (needle) PWM mode 1 */
    TIM2->PSC  = PWM_TIM_PRESCALER;
    TIM2->ARR  = PWM_TIM_PERIOD;
    TIM2->CCR1 = 0;
    TIM2->CCR2 = 0;
    TIM2->CCMR1 = (TIM2->CCMR1 & ~0x7F7FU)
                 | TIM_CCMR1_OC1M_2 | TIM_CCMR1_OC1M_1 | TIM_CCMR1_OC1PE
                 | TIM_CCMR1_OC2M_2 | TIM_CCMR1_OC2M_1 | TIM_CCMR1_OC2PE;
    TIM2->CCER |= TIM_CCER_CC1E | TIM_CCER_CC2E;
    TIM2->CR1  |= TIM_CR1_ARPE;
    TIM2->EGR   = TIM_EGR_UG;
    TIM2->CR1  |= TIM_CR1_CEN;

    encoder_init();

    mstate = MT_IDLE;
    duty = 0;
    reset_pid();
    last_pulse_ms = g_tick_ms;
}

void motor_start(void)
{
    if (mstate != MT_IDLE) return;
    motor_enable();
    duty = PWM_DUTY_MIN;
    set_duty_raw(duty);
    ramp_start_ms = g_tick_ms;
    last_pulse_ms = g_tick_ms;
    mstate = MT_RAMP;
}

void motor_stop(void)
{
    if (mstate == MT_IDLE || mstate == MT_STOP || mstate == MT_BRAKE || mstate == MT_FAULT)
        return;
    mstate = MT_STOP;
}

void motor_brake(void)
{
    /* Both H-bridge outputs high for braking */
    set_duty_raw(0);
    PIN_MOTOR_DIR_PORT->BSRR = (1U << PIN_MOTOR_DIR_PIN); /* direction high */
    set_duty_raw(PWM_DUTY_MAX);                             /* PWM high */
    brake_start_ms = g_tick_ms;
    mstate = MT_BRAKE;
}

void motor_disable(void)
{
    set_duty_raw(0);
    PIN_MOTOR_EN_PORT->BSRR = (1U << (PIN_MOTOR_EN_PIN + 16));
    reset_pid();
    mstate = MT_IDLE;
}

void motor_update(void)
{
    static uint32_t next_pid = 0;
    static uint32_t next_ramp = 0;
    uint32_t now = g_tick_ms;

    if (encoder_has_new_data()) {
        last_pulse_ms = now;
    }

    switch (mstate) {
    case MT_IDLE:
        break;

    case MT_RAMP:
        /* Open-loop ramp until first encoder pulse or timeout */
        if (now >= next_ramp) {
            next_ramp = now + RAMP_INTERVAL_MS;
            if (duty < RAMP_INITIAL_DUTY) {
                duty += RAMP_STEP;
                set_duty_raw(duty);
            }
        }
        /* Transition to closed-loop on first encoder pulse */
        if (encoder_has_new_data()) {
            encoder_clear_new_data();
            next_pid = now + PID_INTERVAL_MS;
            mstate = MT_RUN;
        }
        /* Stall if no pulse after 3x stall timeout */
        if ((now - ramp_start_ms) > RAMP_OPEN_LOOP_MS &&
            (now - last_pulse_ms) > STALL_TIMEOUT_MS * 3) {
            set_duty_raw(0);
            PIN_MOTOR_EN_PORT->BSRR = (1U << (PIN_MOTOR_EN_PIN + 16));
            mstate = MT_FAULT;
        }
        break;

    case MT_RUN:
        /* Stall detection */
        if ((now - last_pulse_ms) > STALL_TIMEOUT_MS) {
            set_duty_raw(0);
            PIN_MOTOR_EN_PORT->BSRR = (1U << (PIN_MOTOR_EN_PIN + 16));
            mstate = MT_FAULT;
            break;
        }
        /* PID update at fixed interval */
        if (now >= next_pid) {
            next_pid = now + PID_INTERVAL_MS;
            uint32_t p = encoder_get_period_us();
            measured_fps = p > 0 ? 1e6f / (float)p : 0;
            set_duty_limited(pid_compute((float)read_target_fps(), measured_fps));
        }
        if (encoder_has_new_data()) {
            encoder_clear_new_data();
        }
        break;

    case MT_STOP:
        /* Ramp down duty */
        if (now >= next_ramp) {
            next_ramp = now + STOP_RAMP_INTERVAL_MS;
            duty = (duty > STOP_RAMP_STEP) ? duty - STOP_RAMP_STEP : 0;
            set_duty_raw(duty);
            if (duty == 0) {
                motor_brake();
            }
        }
        /* Timeout fallback */
        if ((now - last_pulse_ms) > STOP_TIMEOUT_MS) {
            motor_brake();
        }
        break;

    case MT_BRAKE:
        if ((now - brake_start_ms) >= BRAKE_DURATION_MS) {
            motor_disable();
        }
        break;

    case MT_FAULT:
        set_duty_raw(0);
        break;
    }
}

float    motor_get_fps(void)     { return measured_fps; }
uint8_t  motor_is_stalled(void)  { return mstate == MT_FAULT; }
uint16_t motor_get_duty(void)    { return duty; }

void motor_clear_fault(void)
{
    if (mstate == MT_FAULT) {
        set_duty_raw(0);
        PIN_MOTOR_EN_PORT->BSRR = (1U << (PIN_MOTOR_EN_PIN + 16));
        reset_pid();
        mstate = MT_IDLE;
    }
}
