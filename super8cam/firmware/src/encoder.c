/**
 * encoder.c — Optical encoder via TIM21 CH1 input capture.
 *
 * One slot per revolution = one pulse per frame.
 * Measures pulse-to-pulse period in microseconds.
 */

#include "encoder.h"
#include "pinmap.h"
#include "config.h"
#include "stm32l0xx.h"

static volatile uint32_t enc_period_us = 0;
static volatile uint32_t enc_last_cap  = 0;
static volatile uint8_t  enc_new_data  = 0;
static volatile uint32_t frame_count   = 0;

void encoder_init(void)
{
    RCC->IOPENR  |= RCC_IOPENR_GPIOBEN;
    RCC->APB2ENR |= RCC_APB2ENR_TIM21EN;

    /* PB4: TIM21_CH1 AF6 */
    GPIOB->MODER  = (GPIOB->MODER  & ~(3U << (PIN_ENC_PIN * 2)))
                   |  (2U << (PIN_ENC_PIN * 2));
    GPIOB->AFR[0] = (GPIOB->AFR[0] & ~(0xFU << (PIN_ENC_PIN * 4)))
                   |  (PIN_ENC_AF << (PIN_ENC_PIN * 4));

    TIM21->PSC  = ENC_TIM_PRESCALER;
    TIM21->ARR  = 0xFFFF;
    TIM21->CCMR1 = (TIM21->CCMR1 & ~0xFFU) | TIM_CCMR1_CC1S_0;
    TIM21->CCER &= ~(TIM_CCER_CC1P | TIM_CCER_CC1NP);
    TIM21->CCER |=  TIM_CCER_CC1E;
    TIM21->DIER |= TIM_DIER_CC1IE;
    NVIC_EnableIRQ(TIM21_IRQn);
    NVIC_SetPriority(TIM21_IRQn, 1);
    TIM21->EGR  = TIM_EGR_UG;
    TIM21->CR1 |= TIM_CR1_CEN;
}

void TIM21_IRQHandler(void)
{
    if (TIM21->SR & TIM_SR_CC1IF) {
        TIM21->SR = ~TIM_SR_CC1IF;
        uint32_t cap = TIM21->CCR1;
        uint32_t diff = (cap >= enc_last_cap)
                      ? (cap - enc_last_cap)
                      : (0xFFFFU - enc_last_cap + cap + 1U);
        enc_last_cap  = cap;
        enc_period_us = diff;
        enc_new_data  = 1;
        frame_count++;
    }
}

uint32_t encoder_get_period_us(void) { return enc_period_us; }
uint8_t  encoder_has_new_data(void)  { return enc_new_data; }
void     encoder_clear_new_data(void){ enc_new_data = 0; }
uint32_t encoder_get_frame_count(void){ return frame_count; }
