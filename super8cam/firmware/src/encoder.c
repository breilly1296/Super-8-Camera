/**
 * encoder.c — Optical encoder via TIM1 CH1 input capture on PA8.
 *
 * One slot per revolution = one pulse per frame.
 * Measures pulse-to-pulse period in microseconds with 4-sample
 * running average for smoothing.  Timer overflow sets stall flag.
 */

#include "encoder.h"
#include "pinmap.h"
#include "config.h"
#include "stm32l0xx.h"

static volatile uint32_t enc_period_us  = 0;
static volatile uint32_t enc_last_cap   = 0;
static volatile uint8_t  enc_new_data   = 0;
static volatile uint32_t frame_count    = 0;
static volatile uint8_t  enc_stalled    = 0;

/* 4-sample running average buffer */
static volatile uint32_t avg_buf[ENC_AVG_SIZE];
static volatile uint8_t  avg_idx  = 0;
static volatile uint8_t  avg_fill = 0;

static uint32_t avg_compute(uint32_t new_val)
{
    avg_buf[avg_idx] = new_val;
    if (++avg_idx >= ENC_AVG_SIZE) avg_idx = 0;
    if (avg_fill < ENC_AVG_SIZE) avg_fill++;

    uint32_t sum = 0;
    for (uint8_t i = 0; i < avg_fill; i++)
        sum += avg_buf[i];
    return sum / avg_fill;
}

void encoder_init(void)
{
    RCC->IOPENR  |= RCC_IOPENR_GPIOAEN;
    RCC->APB2ENR |= RCC_APB2ENR_TIM1EN;    /* TIM1 on APB2 */

    /* PA8: AF2 = TIM1_CH1 (AFR[1] for pins 8-15) */
    GPIOA->MODER  = (GPIOA->MODER  & ~(3U << (PIN_ENC_PIN * 2)))
                   |  (2U << (PIN_ENC_PIN * 2));
    GPIOA->AFR[1] = (GPIOA->AFR[1] & ~(0xFU << ((PIN_ENC_PIN - 8U) * 4)))
                   |  (PIN_ENC_AF << ((PIN_ENC_PIN - 8U) * 4));

    TIM1->PSC  = ENC_TIM_PRESCALER;        /* 1 us tick at 16 MHz */
    TIM1->ARR  = 0xFFFF;
    TIM1->CCMR1 = (TIM1->CCMR1 & ~0xFFU) | TIM_CCMR1_CC1S_0; /* IC1 on TI1 */
    TIM1->CCER &= ~(TIM_CCER_CC1P | TIM_CCER_CC1NP);          /* rising edge */
    TIM1->CCER |=  TIM_CCER_CC1E;

    /* Enable capture interrupt and update (overflow) interrupt */
    TIM1->DIER |= TIM_DIER_CC1IE | TIM_DIER_UIE;
    NVIC_EnableIRQ(TIM1_CC_IRQn);
    NVIC_SetPriority(TIM1_CC_IRQn, 1);

    TIM1->EGR  = TIM_EGR_UG;
    TIM1->SR   = 0;                        /* clear pending flags */
    TIM1->CR1 |= TIM_CR1_CEN;

    enc_stalled = 0;
    avg_idx = 0;
    avg_fill = 0;
}

void TIM1_CC_IRQHandler(void)
{
    /* Input capture on channel 1 */
    if (TIM1->SR & TIM_SR_CC1IF) {
        TIM1->SR = ~TIM_SR_CC1IF;
        uint32_t cap = TIM1->CCR1;
        uint32_t diff = (cap >= enc_last_cap)
                      ? (cap - enc_last_cap)
                      : (0xFFFFU - enc_last_cap + cap + 1U);
        enc_last_cap  = cap;
        enc_period_us = avg_compute(diff);
        enc_new_data  = 1;
        enc_stalled   = 0;
        frame_count++;
    }

    /* Timer overflow = no pulse for full counter cycle -> stall */
    if (TIM1->SR & TIM_SR_UIF) {
        TIM1->SR = ~TIM_SR_UIF;
        enc_stalled = 1;
    }
}

uint32_t encoder_get_period_us(void)  { return enc_period_us; }
float    encoder_get_fps(void)        { return enc_period_us > 0 ? 1e6f / (float)enc_period_us : 0.0f; }
uint8_t  encoder_has_new_data(void)   { return enc_new_data; }
void     encoder_clear_new_data(void) { enc_new_data = 0; }
uint32_t encoder_get_frame_count(void){ return frame_count; }
uint8_t  encoder_is_stalled(void)     { return enc_stalled; }
