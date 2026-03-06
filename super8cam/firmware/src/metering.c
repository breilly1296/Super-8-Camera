/**
 * metering.c — Photodiode ADC -> EV -> f-stop -> galvanometer + LEDs.
 *
 * 8-point calibration LUT (ADC 0 -> EV 2, ADC 4095 -> EV 17).
 * f-stop to needle PWM mapping via log2 scale.
 * Exposure status: green LED if within +/- 0.5 EV, red blink otherwise.
 * Battery monitoring via ADC channel 1 with 2:1 voltage divider.
 */

#include "metering.h"
#include "config.h"
#include "pinmap.h"
#include "stm32l0xx.h"
#include <math.h>

extern volatile uint32_t g_tick_ms;

static float    current_ev    = 0;
static float    current_fstop = 0;
static uint16_t current_asa   = 100;
static uint16_t battery_mv    = 0;

/* Moving average filter for metering ADC */
static uint16_t filter_buf[METER_FILTER_SIZE];
static uint8_t  filter_idx  = 0;
static uint32_t filter_sum  = 0;
static uint8_t  filter_full = 0;
static uint32_t last_sample_ms = 0;

/* Calibration LUT */
static const uint16_t cal_adc[METER_CAL_LEN] = METER_CAL_ADC;
static const float    cal_ev[METER_CAL_LEN]  = METER_CAL_EV;

/* ASA table */
static const uint16_t asa_table[]    = ASA_TABLE;
static const float    asa_ev_off[]   = ASA_EV_OFFSET_TABLE;

static uint16_t adc_read_channel(uint32_t channel)
{
    ADC1->CHSELR = (1U << channel);
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
    uint8_t count = filter_full ? METER_FILTER_SIZE : filter_idx;
    return (count > 0) ? (uint16_t)(filter_sum / count) : raw;
}

static float lut_interp(uint16_t adc_val)
{
    if (adc_val <= cal_adc[0]) return cal_ev[0];
    if (adc_val >= cal_adc[METER_CAL_LEN - 1]) return cal_ev[METER_CAL_LEN - 1];
    for (uint8_t i = 1; i < METER_CAL_LEN; i++) {
        if (adc_val <= cal_adc[i]) {
            float f = (float)(adc_val - cal_adc[i-1]) / (float)(cal_adc[i] - cal_adc[i-1]);
            return cal_ev[i-1] + f * (cal_ev[i] - cal_ev[i-1]);
        }
    }
    return cal_ev[METER_CAL_LEN - 1];
}

/* Map f-stop to needle PWM (0-999) on log2 scale */
static uint16_t fstop_to_pwm(float fstop)
{
    if (fstop <= FSTOP_MIN) return 0;
    if (fstop >= FSTOP_MAX) return NEEDLE_PWM_PERIOD;
    float frac = (log2f(fstop) - log2f(FSTOP_MIN))
               / (log2f(FSTOP_MAX) - log2f(FSTOP_MIN));
    return (uint16_t)(frac * (float)NEEDLE_PWM_PERIOD);
}

void meter_init(void)
{
    /* Enable ADC clock */
    RCC->APB2ENR |= RCC_APB2ENR_ADCEN;

    /* PA0 (meter) and PA1 (battery) as analog */
    GPIOA->MODER |= (3U << (PIN_ADC_METER_PIN * 2));
    GPIOA->MODER |= (3U << (PIN_ADC_BATT_PIN * 2));

    /* ADC calibration and init */
    if (ADC1->CR & ADC_CR_ADEN) {
        ADC1->CR |= ADC_CR_ADDIS;
        while (ADC1->CR & ADC_CR_ADEN);
    }
    ADC1->CR |= ADC_CR_ADCAL;
    while (ADC1->CR & ADC_CR_ADCAL);

    ADC1->CFGR1 &= ~(ADC_CFGR1_RES | ADC_CFGR1_ALIGN);  /* 12-bit, right-aligned */
    ADC1->SMPR = 0x05U;  /* 39.5 ADC clock cycles sampling */
    ADC1->ISR |= ADC_ISR_ADRDY;
    ADC1->CR |= ADC_CR_ADEN;
    while (!(ADC1->ISR & ADC_ISR_ADRDY));

    /* LEDs: PB6 (red) and PB7 (green) as output */
    GPIOB->MODER = (GPIOB->MODER & ~(3U << (PIN_LED_RED_PIN * 2)))
                 |  (1U << (PIN_LED_RED_PIN * 2));
    GPIOB->MODER = (GPIOB->MODER & ~(3U << (PIN_LED_GREEN_PIN * 2)))
                 |  (1U << (PIN_LED_GREEN_PIN * 2));
}

void meter_update(void)
{
    uint32_t now = g_tick_ms;
    if ((now - last_sample_ms) < (1000U / METER_SAMPLE_HZ)) return;
    last_sample_ms = now;

    /* Read and filter metering ADC */
    uint16_t avg = filter_push(adc_read_channel(PIN_ADC_METER_CHANNEL));
    float ev100 = lut_interp(avg);

    /* Read film speed DIP switches */
    uint8_t bits = 0;
    if (PIN_DIP0_PORT->IDR & (1U << PIN_DIP0_PIN)) bits |= 1;
    if (PIN_DIP1_PORT->IDR & (1U << PIN_DIP1_PIN)) bits |= 2;
    current_asa = asa_table[bits];

    /* Compute EV adjusted for ASA */
    float ev = ev100 + asa_ev_off[bits];
    current_ev = ev;

    /* Compute f-stop from EV and shutter speed */
    uint8_t fps = (PIN_FPS_SEL_PORT->IDR & (1U << PIN_FPS_SEL_PIN)) ? FPS_HIGH : FPS_LOW;
    float shutter = (fps == FPS_HIGH) ? (1.0f / 48.0f) : (1.0f / 36.0f);
    float nsq = powf(2.0f, ev) * shutter;
    current_fstop = (nsq > 0) ? sqrtf(nsq) : 0;

    /* Update galvanometer needle via TIM2 CH2 */
    TIM2->CCR2 = fstop_to_pwm(current_fstop);

    /* Exposure status LEDs */
    if (current_fstop >= FSTOP_MIN && current_fstop <= FSTOP_MAX) {
        /* In range: green on, red off */
        PIN_LED_GREEN_PORT->BSRR = (1U << PIN_LED_GREEN_PIN);
        PIN_LED_RED_PORT->BSRR   = (1U << (PIN_LED_RED_PIN + 16));
    } else {
        /* Out of range: red blink at 2.5 Hz, green off */
        PIN_LED_GREEN_PORT->BSRR = (1U << (PIN_LED_GREEN_PIN + 16));
        PIN_LED_RED_PORT->BSRR   = ((now / 200) & 1)
                                  ? (1U << PIN_LED_RED_PIN)
                                  : (1U << (PIN_LED_RED_PIN + 16));
    }

    /* Battery voltage (every 10th sample to reduce ADC switching) */
    static uint8_t batt_div = 0;
    if (++batt_div >= 10) {
        batt_div = 0;
        uint16_t batt_raw = adc_read_channel(PIN_ADC_BATT_CHANNEL);
        uint32_t batt_adc_mv = ((uint32_t)batt_raw * ADC_VREF_MV) / ADC_RESOLUTION;
        battery_mv = (uint16_t)(batt_adc_mv * VBAT_DIVIDER_RATIO);
    }
}

float    meter_get_ev(void)              { return current_ev; }
float    meter_get_fstop(void)           { return current_fstop; }
uint16_t meter_get_asa(void)             { return current_asa; }
uint16_t meter_get_battery_mv(void)      { return battery_mv; }
uint8_t  meter_is_low_battery(void)      { return battery_mv > 0 && battery_mv < VBAT_WARNING_MV; }
uint8_t  meter_is_shutdown_battery(void) { return battery_mv > 0 && battery_mv < VBAT_SHUTDOWN_MV; }
