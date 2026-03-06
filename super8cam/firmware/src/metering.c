/**
 * metering.c — Photodiode ADC -> EV -> f-stop -> galvanometer + LEDs.
 * All constants from config.h; all pins from pinmap.h.
 * See the root-level metering.c for the full implementation.
 * This is the refactored version using centralized config.
 */

#include "metering.h"
#include "config.h"
#include "pinmap.h"
#include "stm32l0xx.h"
#include <math.h>

extern volatile uint32_t g_tick_ms;

static float current_ev = 0, current_fstop = 0;
static uint16_t current_asa = 100;
static uint16_t filter_buf[METER_FILTER_SIZE];
static uint8_t filter_idx = 0;
static uint32_t filter_sum = 0;
static uint8_t filter_full = 0;
static uint32_t last_sample_ms = 0;

static const uint16_t asa_table[] = { 50, 100, 200, 500 };

/* Calibration LUT: mV -> EV at ISO 100 */
static const struct { uint16_t mv; float ev; } cal[] = {
    {10,1},{30,2},{70,4},{130,6},{230,7},{400,8},{650,9},
    {950,10},{1350,11},{1800,12},{2300,13},{2800,14},{3250,17},
};
#define CAL_LEN (sizeof(cal)/sizeof(cal[0]))

static uint16_t adc_read(void)
{
    ADC1->CR |= ADC_CR_ADSTART;
    while (!(ADC1->ISR & ADC_ISR_EOC));
    return (uint16_t)ADC1->DR;
}

static uint16_t filter_push(uint16_t raw)
{
    filter_sum -= filter_buf[filter_idx];
    filter_buf[filter_idx] = raw;
    filter_sum += raw;
    if (++filter_idx >= METER_FILTER_SIZE) { filter_idx = 0; filter_full = 1; }
    return (uint16_t)(filter_sum / (filter_full ? METER_FILTER_SIZE : filter_idx));
}

static float lut_interp(uint32_t mv)
{
    if (mv <= cal[0].mv) return cal[0].ev;
    if (mv >= cal[CAL_LEN-1].mv) return cal[CAL_LEN-1].ev;
    for (unsigned i = 1; i < CAL_LEN; i++) {
        if (mv <= cal[i].mv) {
            float f = (float)(mv - cal[i-1].mv) / (cal[i].mv - cal[i-1].mv);
            return cal[i-1].ev + f * (cal[i].ev - cal[i-1].ev);
        }
    }
    return cal[CAL_LEN-1].ev;
}

void meter_init(void)
{
    RCC->APB2ENR |= RCC_APB2ENR_ADCEN;
    GPIOA->MODER |= (3U << (PIN_ADC_METER_PIN * 2));
    if (ADC1->CR & ADC_CR_ADEN) { ADC1->CR |= ADC_CR_ADDIS; while (ADC1->CR & ADC_CR_ADEN); }
    ADC1->CR |= ADC_CR_ADCAL; while (ADC1->CR & ADC_CR_ADCAL);
    ADC1->CFGR1 &= ~(ADC_CFGR1_RES | ADC_CFGR1_ALIGN);
    ADC1->SMPR = 0x05U;
    ADC1->CHSELR = (1U << PIN_ADC_METER_CHANNEL);
    ADC1->ISR |= ADC_ISR_ADRDY;
    ADC1->CR |= ADC_CR_ADEN;
    while (!(ADC1->ISR & ADC_ISR_ADRDY));

    /* Galvanometer PWM TIM22 */
    RCC->APB2ENR |= RCC_APB2ENR_TIM22EN;
    GPIOA->MODER = (GPIOA->MODER & ~(3U << (PIN_PWM_NEEDLE_PIN*2))) | (2U << (PIN_PWM_NEEDLE_PIN*2));
    GPIOA->AFR[0] = (GPIOA->AFR[0] & ~(0xFU << (PIN_PWM_NEEDLE_PIN*4))) | (PIN_PWM_NEEDLE_AF << (PIN_PWM_NEEDLE_PIN*4));
    TIM22->PSC = 15; TIM22->ARR = 999; TIM22->CCR1 = 0;
    TIM22->CCMR1 = (TIM22->CCMR1 & ~0x7FU) | TIM_CCMR1_OC1M_2 | TIM_CCMR1_OC1M_1 | TIM_CCMR1_OC1PE;
    TIM22->CCER |= TIM_CCER_CC1E; TIM22->CR1 |= TIM_CR1_ARPE;
    TIM22->EGR = TIM_EGR_UG; TIM22->CR1 |= TIM_CR1_CEN;

    /* LEDs */
    GPIOA->MODER = (GPIOA->MODER & ~(3U<<(PIN_LED_GREEN_PIN*2))) | (1U<<(PIN_LED_GREEN_PIN*2));
    GPIOA->MODER = (GPIOA->MODER & ~(3U<<(PIN_LED_RED_PIN*2))) | (1U<<(PIN_LED_RED_PIN*2));
}

void meter_update(void)
{
    uint32_t now = g_tick_ms;
    if ((now - last_sample_ms) < (1000U / METER_SAMPLE_HZ)) return;
    last_sample_ms = now;

    uint16_t avg = filter_push(adc_read());
    uint32_t mv = ((uint32_t)avg * ADC_VREF_MV) / ADC_RESOLUTION;
    float ev100 = lut_interp(mv);

    uint8_t bits = 0;
    if (PIN_DIP0_PORT->IDR & (1U << PIN_DIP0_PIN)) bits |= 1;
    if (PIN_DIP1_PORT->IDR & (1U << PIN_DIP1_PIN)) bits |= 2;
    current_asa = asa_table[bits];

    uint8_t fps = (PIN_FPS_SEL_PORT->IDR & (1U << PIN_FPS_SEL_PIN)) ? 24 : 18;
    float shutter = (fps == 24) ? (1.0f/48) : (1.0f/36);
    float ev = ev100 + log2f((float)current_asa / 100.0f);
    current_ev = ev;
    float nsq = powf(2.0f, ev) * shutter;
    current_fstop = (nsq > 0) ? sqrtf(nsq) : 0;

    /* Galvanometer */
    float f_min = 1.4f, f_max = 22.0f;
    float frac = 0;
    if (current_fstop > f_min && current_fstop < f_max)
        frac = (log2f(current_fstop) - log2f(f_min)) / (log2f(f_max) - log2f(f_min));
    else if (current_fstop >= f_max) frac = 1.0f;
    TIM22->CCR1 = (uint16_t)(frac * 999);

    /* LEDs */
    if (current_fstop >= f_min) {
        GPIOA->BSRR = (1U << PIN_LED_GREEN_PIN);
        GPIOA->BSRR = (1U << (PIN_LED_RED_PIN + 16));
    } else {
        GPIOA->BSRR = (1U << (PIN_LED_GREEN_PIN + 16));
        GPIOA->BSRR = ((now / 200) & 1) ? (1U << PIN_LED_RED_PIN) : (1U << (PIN_LED_RED_PIN+16));
    }
}

float meter_get_ev(void) { return current_ev; }
float meter_get_fstop(void) { return current_fstop; }
uint16_t meter_get_asa(void) { return current_asa; }
