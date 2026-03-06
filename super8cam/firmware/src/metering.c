/**
 * metering.c — Photodiode ADC → EV → f-stop → Galvanometer + LEDs
 *
 * Exposure math:
 *   EV_100 = lut_interp(adc_mv)         calibration lookup
 *   EV     = EV_100 + log2(ASA / 100)   adjust for film speed
 *   N      = sqrt(2^EV × t)             required f-number
 *
 * Galvanometer mapping uses log2 scale so each whole stop gets equal
 * needle travel.
 *
 * All constants from config.h; all pins from pinmap.h.
 *
 * Copyright (c) 2026 — released under MIT license.
 */

#include "metering.h"
#include "config.h"
#include "pinmap.h"
#include "stm32l0xx.h"
#include <math.h>

/* Global tick from main.c */
extern volatile uint32_t g_tick_ms;

/* =====================================================================
 * Film speed table — indexed by 2-bit DIP switch value
 * ===================================================================== */

static const uint16_t asa_table[ASA_COUNT] = {
    50,     /* DIP 00 — Kodak Vision3 50D  */
    100,    /* DIP 01 — standard           */
    200,    /* DIP 10 — Kodak Vision3 200T */
    500,    /* DIP 11 — high speed         */
};

/* =====================================================================
 * Calibration LUT: ADC millivolts → EV at ISO 100
 *
 * Populate from a known-light session with a BPW34 + 1 MΩ TIA.
 * Table must be monotonically increasing in mV.  Linear interpolation
 * between entries.
 * ===================================================================== */

typedef struct {
    uint16_t mv;
    float    ev;
} cal_point_t;

static const cal_point_t cal_table[CAL_TABLE_SIZE] = {
    {   10,   1.0f },       /* near darkness                          */
    {   30,   2.0f },
    {   70,   4.0f },
    {  130,   6.0f },
    {  230,   7.0f },
    {  400,   8.0f },       /* indoor, well lit                       */
    {  650,   9.0f },
    {  950,  10.0f },
    { 1350,  11.0f },
    { 1800,  12.0f },       /* overcast daylight                      */
    { 2300,  13.0f },
    { 2800,  14.0f },       /* direct sunlight                        */
    { 3250,  17.0f },       /* sensor near saturation                 */
};

/* =====================================================================
 * Rolling average filter (16 samples)
 * ===================================================================== */

static uint16_t filter_buf[METER_FILTER_SIZE];
static uint8_t  filter_idx  = 0;
static uint32_t filter_sum  = 0;
static uint8_t  filter_full = 0;

static void filter_reset(void)
{
    for (uint8_t i = 0; i < METER_FILTER_SIZE; i++)
        filter_buf[i] = 0;
    filter_idx  = 0;
    filter_sum  = 0;
    filter_full = 0;
}

static uint16_t filter_push(uint16_t raw)
{
    filter_sum -= filter_buf[filter_idx];
    filter_buf[filter_idx] = raw;
    filter_sum += raw;
    filter_idx++;
    if (filter_idx >= METER_FILTER_SIZE) {
        filter_idx  = 0;
        filter_full = 1;
    }
    uint8_t count = filter_full ? METER_FILTER_SIZE : filter_idx;
    if (count == 0) count = 1;      /* safety: avoid /0 on first call    */
    return (uint16_t)(filter_sum / count);
}

/* =====================================================================
 * Module state
 * ===================================================================== */

static uint32_t last_sample_ms = 0;
static uint32_t filtered_mv    = 0;
static float    current_ev     = 0.0f;
static float    current_fstop  = 0.0f;
static uint16_t current_asa    = 100;
static uint8_t  current_fps_val = 18;

/* =====================================================================
 * ADC helpers (bare register, single-conversion)
 * ===================================================================== */

static void adc_init(void)
{
    RCC->APB2ENR |= RCC_APB2ENR_ADCEN;

    /* PA7: analog mode (MODER = 11) */
    PIN_ADC_METER_PORT->MODER |= (3U << (PIN_ADC_METER_PIN * 2));

    /* Ensure ADC is disabled before configuring */
    if (ADC1->CR & ADC_CR_ADEN) {
        ADC1->CR |= ADC_CR_ADDIS;
        while (ADC1->CR & ADC_CR_ADEN) { /* wait */ }
    }

    /* Calibrate */
    ADC1->CR |= ADC_CR_ADCAL;
    while (ADC1->CR & ADC_CR_ADCAL) { /* wait */ }

    /* 12-bit resolution, right-aligned */
    ADC1->CFGR1 &= ~(ADC_CFGR1_RES | ADC_CFGR1_ALIGN);

    /* Sample time: 79.5 cycles — suitable for high-impedance TIA */
    ADC1->SMPR = 0x05U;

    /* Select metering channel */
    ADC1->CHSELR = (1U << PIN_ADC_METER_CHANNEL);

    /* Enable ADC */
    ADC1->ISR |= ADC_ISR_ADRDY;
    ADC1->CR  |= ADC_CR_ADEN;
    while (!(ADC1->ISR & ADC_ISR_ADRDY)) { /* wait */ }
}

static uint16_t adc_read(void)
{
    ADC1->CR |= ADC_CR_ADSTART;
    while (!(ADC1->ISR & ADC_ISR_EOC)) { /* wait */ }
    return (uint16_t)ADC1->DR;
}

/* =====================================================================
 * GPIO init: galvanometer PWM, exposure LEDs, DIP switch
 * ===================================================================== */

static void meter_gpio_init(void)
{
    RCC->IOPENR |= RCC_IOPENR_GPIOAEN | RCC_IOPENR_GPIOBEN;

    /* PA4: TIM22 CH1 alternate function (AF4) — galvanometer */
    PIN_PWM_NEEDLE_PORT->MODER =
        (PIN_PWM_NEEDLE_PORT->MODER & ~(3U << (PIN_PWM_NEEDLE_PIN * 2)))
        | (2U << (PIN_PWM_NEEDLE_PIN * 2));
    PIN_PWM_NEEDLE_PORT->AFR[0] =
        (PIN_PWM_NEEDLE_PORT->AFR[0] & ~(0xFU << (PIN_PWM_NEEDLE_PIN * 4)))
        | (PIN_PWM_NEEDLE_AF << (PIN_PWM_NEEDLE_PIN * 4));

    /* PA5: green LED — output push-pull */
    PIN_LED_GREEN_PORT->MODER =
        (PIN_LED_GREEN_PORT->MODER & ~(3U << (PIN_LED_GREEN_PIN * 2)))
        | (1U << (PIN_LED_GREEN_PIN * 2));

    /* PA6: red LED — output push-pull */
    PIN_LED_RED_PORT->MODER =
        (PIN_LED_RED_PORT->MODER & ~(3U << (PIN_LED_RED_PIN * 2)))
        | (1U << (PIN_LED_RED_PIN * 2));

    /* PB0, PB1: DIP switch — input with pull-down */
    PIN_DIP0_PORT->MODER &= ~(3U << (PIN_DIP0_PIN * 2));
    PIN_DIP1_PORT->MODER &= ~(3U << (PIN_DIP1_PIN * 2));
    PIN_DIP0_PORT->PUPDR =
        (PIN_DIP0_PORT->PUPDR & ~(3U << (PIN_DIP0_PIN * 2)))
        | (2U << (PIN_DIP0_PIN * 2));
    PIN_DIP1_PORT->PUPDR =
        (PIN_DIP1_PORT->PUPDR & ~(3U << (PIN_DIP1_PIN * 2)))
        | (2U << (PIN_DIP1_PIN * 2));
}

/* =====================================================================
 * Galvanometer PWM (TIM22 CH1)
 * ===================================================================== */

static void galvo_init(void)
{
    RCC->APB2ENR |= RCC_APB2ENR_TIM22EN;

    TIM22->PSC  = GALVO_PWM_PRESCALER;
    TIM22->ARR  = GALVO_PWM_PERIOD;
    TIM22->CCR1 = 0;

    TIM22->CCMR1 = (TIM22->CCMR1 & ~0x7FU)
                  | TIM_CCMR1_OC1M_2 | TIM_CCMR1_OC1M_1
                  | TIM_CCMR1_OC1PE;

    TIM22->CCER |= TIM_CCER_CC1E;
    TIM22->CR1  |= TIM_CR1_ARPE;
    TIM22->EGR   = TIM_EGR_UG;
    TIM22->CR1  |= TIM_CR1_CEN;
}

static void galvo_set(uint16_t duty)
{
    if (duty > GALVO_PWM_PERIOD) duty = GALVO_PWM_PERIOD;
    TIM22->CCR1 = duty;
}

/* =====================================================================
 * LED control
 * ===================================================================== */

static inline void green_led(uint8_t on)
{
    if (on) PIN_LED_GREEN_PORT->BSRR = (1U << PIN_LED_GREEN_PIN);
    else    PIN_LED_GREEN_PORT->BSRR = (1U << (PIN_LED_GREEN_PIN + 16));
}

static inline void red_led(uint8_t on)
{
    if (on) PIN_LED_RED_PORT->BSRR = (1U << PIN_LED_RED_PIN);
    else    PIN_LED_RED_PORT->BSRR = (1U << (PIN_LED_RED_PIN + 16));
}

/* =====================================================================
 * Input readers
 * ===================================================================== */

static uint16_t read_asa(void)
{
    uint8_t bits = 0;
    if (PIN_DIP0_PORT->IDR & (1U << PIN_DIP0_PIN)) bits |= 1U;
    if (PIN_DIP1_PORT->IDR & (1U << PIN_DIP1_PIN)) bits |= 2U;
    return asa_table[bits];
}

static uint8_t read_fps(void)
{
    return (PIN_FPS_SEL_PORT->IDR & (1U << PIN_FPS_SEL_PIN)) ? 24U : 18U;
}

/* =====================================================================
 * Calibration: voltage → EV (linear interpolation in LUT)
 * ===================================================================== */

static float lut_mv_to_ev100(uint32_t mv)
{
    if (mv <= cal_table[0].mv)
        return cal_table[0].ev;
    if (mv >= cal_table[CAL_TABLE_SIZE - 1].mv)
        return cal_table[CAL_TABLE_SIZE - 1].ev;

    for (uint8_t i = 1; i < CAL_TABLE_SIZE; i++) {
        if (mv <= cal_table[i].mv) {
            float frac = (float)(mv - cal_table[i - 1].mv) /
                         (float)(cal_table[i].mv - cal_table[i - 1].mv);
            return cal_table[i - 1].ev +
                   frac * (cal_table[i].ev - cal_table[i - 1].ev);
        }
    }
    return cal_table[CAL_TABLE_SIZE - 1].ev;
}

/* =====================================================================
 * Exposure math
 *
 *   EV_scene = EV_100 + log2(ASA / 100)
 *   N = sqrt(2^EV × t)
 * ===================================================================== */

static float compute_fstop(float ev100, uint16_t asa, float shutter_s)
{
    float ev = ev100 + log2f((float)asa / 100.0f);
    float n_squared = powf(2.0f, ev) * shutter_s;
    if (n_squared < 0.0f) n_squared = 0.0f;
    return sqrtf(n_squared);
}

/* =====================================================================
 * f-stop → galvanometer duty (log2 mapping)
 * ===================================================================== */

static uint16_t fstop_to_galvo(float fstop)
{
    const float f_min = (float)FSTOP_MIN_X10 / 10.0f;
    const float f_max = (float)FSTOP_MAX_X10 / 10.0f;

    if (fstop <= f_min) return 0;
    if (fstop >= f_max) return GALVO_PWM_PERIOD;

    float log_min = log2f(f_min);
    float log_max = log2f(f_max);
    float log_f   = log2f(fstop);
    float frac    = (log_f - log_min) / (log_max - log_min);

    return (uint16_t)(frac * (float)GALVO_PWM_PERIOD);
}

/* =====================================================================
 * Public API
 * ===================================================================== */

void meter_init(void)
{
    meter_gpio_init();
    adc_init();
    galvo_init();
    filter_reset();

    green_led(0);
    red_led(0);
    galvo_set(0);

    last_sample_ms = g_tick_ms;
}

void meter_update(void)
{
    uint32_t now = g_tick_ms;
    uint32_t interval = 1000U / METER_SAMPLE_HZ;       /* 10 ms            */

    if ((now - last_sample_ms) < interval)
        return;
    last_sample_ms = now;

    /* ---- ADC sample + filter ---------------------------------------- */
    uint16_t raw     = adc_read();
    uint16_t avg_raw = filter_push(raw);
    filtered_mv = ((uint32_t)avg_raw * ADC_VREF_MV) / ADC_RESOLUTION;

    /* ---- EV computation --------------------------------------------- */
    float ev100 = lut_mv_to_ev100(filtered_mv);

    /* ---- Read user selections --------------------------------------- */
    current_asa     = read_asa();
    current_fps_val = read_fps();
    float shutter_s = (current_fps_val == 24U) ? SHUTTER_24FPS : SHUTTER_18FPS;

    /* ---- f-stop calculation ----------------------------------------- */
    current_fstop = compute_fstop(ev100, current_asa, shutter_s);
    current_ev    = ev100 + log2f((float)current_asa / 100.0f);

    /* ---- Galvanometer needle ---------------------------------------- */
    galvo_set(fstop_to_galvo(current_fstop));

    /* ---- Exposure warning LEDs -------------------------------------- */
    float f_min = (float)FSTOP_MIN_X10 / 10.0f;

    if (current_fstop < f_min) {
        /* Underexposed: computed f-stop wider than f/1.4 */
        float stops_under = log2f(f_min / current_fstop);
        green_led(0);

        if (stops_under > UNDER_WARN_EV) {
            /* Severely under — blink red */
            red_led(((now / (LED_BLINK_PERIOD_MS / 2)) & 1U));
        } else {
            /* Slightly under — steady red */
            red_led(1);
        }
    } else {
        /* Exposure achievable — green */
        green_led(1);
        red_led(0);
    }
}

uint32_t meter_get_mv(void)    { return filtered_mv; }
float    meter_get_ev(void)    { return current_ev; }
float    meter_get_fstop(void) { return current_fstop; }
uint16_t meter_get_asa(void)   { return current_asa; }
uint8_t  meter_get_fps(void)   { return current_fps_val; }
