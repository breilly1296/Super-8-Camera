/**
 * encoder.c — Optical Encoder via TIM21 CH1 Input Capture
 *
 * Signal chain:
 *   Slotted disc on main shaft → photointerrupter → TIM21 CC1
 *     → ISR computes period → 4-sample moving average → fps
 *
 * One slot per revolution = one pulse per frame.
 * Timer runs at 1 MHz (1 µs ticks).  16-bit counter wraps at 65 536 µs.
 * At 18 fps: ~55 556 µs period — fits in 16-bit with margin.
 *
 * Copyright (c) 2026 — released under MIT license.
 */

#include "encoder.h"
#include "config.h"
#include "pinmap.h"
#include "stm32l0xx.h"

/* Global tick from main.c */
extern volatile uint32_t g_tick_ms;

/* =====================================================================
 * ISR-written state (volatile)
 * ===================================================================== */

static volatile uint32_t enc_raw_period  = 0;   /* latest raw period (µs)   */
static volatile uint32_t enc_last_cap    = 0;   /* previous capture value    */
static volatile uint8_t  enc_new_data    = 0;   /* flag: fresh capture       */
static volatile uint32_t enc_frame_count = 0;   /* total frames              */
static volatile uint32_t enc_last_pulse  = 0;   /* tick_ms of last pulse     */

/* =====================================================================
 * 4-sample moving average
 * ===================================================================== */

static volatile uint32_t enc_avg_buf[ENC_AVG_SIZE];
static volatile uint8_t  enc_avg_idx  = 0;
static volatile uint8_t  enc_avg_full = 0;

/** Push a raw period into the ring buffer and return the average. */
static uint32_t avg_push(uint32_t val)
{
    enc_avg_buf[enc_avg_idx] = val;
    enc_avg_idx++;
    if (enc_avg_idx >= ENC_AVG_SIZE) {
        enc_avg_idx = 0;
        enc_avg_full = 1;
    }

    uint8_t count = enc_avg_full ? ENC_AVG_SIZE : enc_avg_idx;
    uint32_t sum = 0;
    for (uint8_t i = 0; i < count; i++)
        sum += enc_avg_buf[i];
    return sum / count;
}

/* =====================================================================
 * Averaged period (written by ISR via avg_push)
 * ===================================================================== */

static volatile uint32_t enc_avg_period = 0;

/* =====================================================================
 * TIM21 Capture/Compare ISR
 * ===================================================================== */

void TIM21_IRQHandler(void)
{
    if (TIM21->SR & TIM_SR_CC1IF) {
        TIM21->SR = ~TIM_SR_CC1IF;             /* clear interrupt flag      */

        uint32_t cap = TIM21->CCR1;
        uint32_t diff;

        /* 16-bit wrap-around handling */
        if (cap >= enc_last_cap)
            diff = cap - enc_last_cap;
        else
            diff = (0xFFFFU - enc_last_cap) + cap + 1U;

        enc_last_cap   = cap;
        enc_raw_period = diff;
        enc_avg_period = avg_push(diff);
        enc_new_data   = 1;
        enc_frame_count++;
        enc_last_pulse = g_tick_ms;
    }
}

/* =====================================================================
 * Hardware Init
 * ===================================================================== */

void encoder_init(void)
{
    /* Enable clocks */
    RCC->IOPENR  |= RCC_IOPENR_GPIOBEN;
    RCC->APB2ENR |= RCC_APB2ENR_TIM21EN;

    /* PB4: alternate function mode */
    PIN_ENC_PORT->MODER = (PIN_ENC_PORT->MODER & ~(3U << (PIN_ENC_PIN * 2)))
                        | (2U << (PIN_ENC_PIN * 2));

    /* PB4: AF6 = TIM21_CH1 */
    PIN_ENC_PORT->AFR[0] = (PIN_ENC_PORT->AFR[0] & ~(0xFU << (PIN_ENC_PIN * 4)))
                          | (PIN_ENC_AF << (PIN_ENC_PIN * 4));

    /* TIM21: free-running at 1 MHz, 16-bit */
    TIM21->PSC  = ENC_TIM_PRESCALER;
    TIM21->ARR  = 0xFFFF;

    /* CH1: input capture mapped to TI1, no filter, no prescaler */
    TIM21->CCMR1 = (TIM21->CCMR1 & ~0xFFU) | TIM_CCMR1_CC1S_0;

    /* Rising edge capture */
    TIM21->CCER &= ~(TIM_CCER_CC1P | TIM_CCER_CC1NP);
    TIM21->CCER |= TIM_CCER_CC1E;

    /* Enable capture interrupt */
    TIM21->DIER |= TIM_DIER_CC1IE;
    NVIC_EnableIRQ(TIM21_IRQn);
    NVIC_SetPriority(TIM21_IRQn, 1);           /* high priority for timing */

    /* Force update and start */
    TIM21->EGR  = TIM_EGR_UG;
    TIM21->CR1 |= TIM_CR1_CEN;

    /* Zero state */
    enc_raw_period  = 0;
    enc_avg_period  = 0;
    enc_last_cap    = 0;
    enc_new_data    = 0;
    enc_frame_count = 0;
    enc_avg_idx     = 0;
    enc_avg_full    = 0;
    enc_last_pulse  = g_tick_ms;

    for (uint8_t i = 0; i < ENC_AVG_SIZE; i++)
        enc_avg_buf[i] = 0;
}

/* =====================================================================
 * Public API
 * ===================================================================== */

uint32_t encoder_get_period_us(void)
{
    return enc_avg_period;
}

uint32_t encoder_get_raw_period_us(void)
{
    return enc_raw_period;
}

float encoder_get_fps(void)
{
    uint32_t p = enc_avg_period;
    if (p == 0) return 0.0f;
    return 1000000.0f / (float)p;
}

uint32_t encoder_get_frame_count(void)
{
    return enc_frame_count;
}

void encoder_reset_frame_count(void)
{
    enc_frame_count = 0;
}

uint8_t encoder_has_new_data(void)
{
    return enc_new_data;
}

void encoder_clear_new_data(void)
{
    enc_new_data = 0;
}

uint32_t encoder_get_last_pulse_ms(void)
{
    return enc_last_pulse;
}

uint8_t encoder_is_stalled(uint32_t now_ms, uint32_t timeout_ms)
{
    return ((now_ms - enc_last_pulse) > timeout_ms) ? 1U : 0U;
}
