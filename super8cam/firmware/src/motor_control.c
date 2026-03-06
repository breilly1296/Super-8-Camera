/**
 * motor_control.c — PID closed-loop DC motor speed controller.
 * All constants from config.h; all pins from pinmap.h.
 */

#include "motor_control.h"
#include "encoder.h"
#include "config.h"
#include "pinmap.h"
#include "stm32l0xx.h"

extern volatile uint32_t g_tick_ms;

typedef enum { ST_IDLE, ST_RAMP, ST_RUN, ST_STOP, ST_FAULT } motor_state_t;

static motor_state_t mstate = ST_IDLE;
static float pid_integral = 0, pid_prev_err = 0, measured_fps = 0;
static uint16_t duty = 0;
static uint32_t last_pulse_ms = 0;

static uint32_t read_target_fps(void)
{
    return (PIN_FPS_SEL_PORT->IDR & (1U << PIN_FPS_SEL_PIN)) ? FPS_HIGH : FPS_LOW;
}

static void set_duty(uint16_t d)
{
    if (d > PWM_DUTY_MAX) d = PWM_DUTY_MAX;
    TIM2->CCR1 = d;
    duty = d;
}

static uint16_t pid_compute(float target, float actual)
{
    float err = target - actual;
    float p = PID_KP * err;
    pid_integral += PID_KI * err * (PID_INTERVAL_MS / 1000.0f);
    if (pid_integral >  PID_I_CLAMP) pid_integral =  PID_I_CLAMP;
    if (pid_integral < -PID_I_CLAMP) pid_integral = -PID_I_CLAMP;
    float d = PID_KD * (err - pid_prev_err) / (PID_INTERVAL_MS / 1000.0f);
    pid_prev_err = err;
    float out = (float)duty + p + pid_integral + d;
    if (out < PWM_DUTY_MIN) out = PWM_DUTY_MIN;
    if (out > PWM_DUTY_MAX) out = PWM_DUTY_MAX;
    return (uint16_t)out;
}

void motor_init(void)
{
    RCC->IOPENR  |= RCC_IOPENR_GPIOAEN;
    RCC->APB1ENR |= RCC_APB1ENR_TIM2EN;

    GPIOA->MODER  = (GPIOA->MODER  & ~(3U << (PIN_PWM_MOTOR_PIN * 2)))
                   |  (2U << (PIN_PWM_MOTOR_PIN * 2));
    GPIOA->AFR[0] = (GPIOA->AFR[0] & ~(0xFU << (PIN_PWM_MOTOR_PIN * 4)))
                   |  (PIN_PWM_MOTOR_AF << (PIN_PWM_MOTOR_PIN * 4));

    TIM2->PSC  = PWM_TIM_PRESCALER;
    TIM2->ARR  = PWM_TIM_PERIOD;
    TIM2->CCR1 = 0;
    TIM2->CCMR1 = (TIM2->CCMR1 & ~0x7FU)
                 | TIM_CCMR1_OC1M_2 | TIM_CCMR1_OC1M_1 | TIM_CCMR1_OC1PE;
    TIM2->CCER |= TIM_CCER_CC1E;
    TIM2->CR1  |= TIM_CR1_ARPE;
    TIM2->EGR   = TIM_EGR_UG;
    TIM2->CR1  |= TIM_CR1_CEN;

    encoder_init();
    mstate = ST_IDLE;
    duty = 0;
    pid_integral = pid_prev_err = measured_fps = 0;
    last_pulse_ms = g_tick_ms;
}

void motor_update(void)
{
    static uint32_t next_pid = 0, next_ramp = 0;
    uint32_t now = g_tick_ms;

    if (encoder_has_new_data()) {
        last_pulse_ms = now;
    }

    switch (mstate) {
    case ST_IDLE:
        if (PIN_TRIGGER_PORT->IDR & (1U << PIN_TRIGGER_PIN)) break; /* not pressed */
        duty = PWM_DUTY_MIN; set_duty(duty);
        next_ramp = now + RAMP_INTERVAL_MS;
        last_pulse_ms = now;
        mstate = ST_RAMP;
        break;
    case ST_RAMP:
        if (now >= next_ramp) {
            next_ramp = now + RAMP_INTERVAL_MS;
            if (duty < PWM_DUTY_MAX * 40 / 100) { duty += RAMP_STEP; set_duty(duty); }
        }
        if (encoder_has_new_data()) {
            encoder_clear_new_data();
            next_pid = now + PID_INTERVAL_MS;
            mstate = ST_RUN;
        }
        if ((now - last_pulse_ms) > STALL_TIMEOUT_MS * 3) {
            set_duty(0); mstate = ST_FAULT;
        }
        break;
    case ST_RUN:
        if ((now - last_pulse_ms) > STALL_TIMEOUT_MS) {
            set_duty(0); mstate = ST_FAULT; break;
        }
        if (now >= next_pid) {
            next_pid = now + PID_INTERVAL_MS;
            uint32_t p = encoder_get_period_us();
            measured_fps = p > 0 ? 1e6f / p : 0;
            set_duty(pid_compute((float)read_target_fps(), measured_fps));
        }
        if (PIN_TRIGGER_PORT->IDR & (1U << PIN_TRIGGER_PIN)) {
            next_ramp = now + 8; mstate = ST_STOP;
        }
        break;
    case ST_STOP:
        if (now >= next_ramp) {
            next_ramp = now + 8;
            duty = (duty > 8) ? duty - 8 : 0;
            set_duty(duty);
            if (duty == 0) { pid_integral = pid_prev_err = 0; mstate = ST_IDLE; }
        }
        break;
    case ST_FAULT:
        set_duty(0);
        break;
    }
}

float motor_get_fps(void) { return measured_fps; }
uint8_t motor_is_stalled(void) { return mstate == ST_FAULT; }
void motor_clear_fault(void) { if (mstate == ST_FAULT) { set_duty(0); pid_integral = pid_prev_err = 0; mstate = ST_IDLE; } }
