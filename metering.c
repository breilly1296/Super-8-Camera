/**
 * metering.c — Super 8 Camera Light Meter / Exposure Calculator
 *
 * Signal chain:
 *   BPW34 photodiode → transimpedance amp → ADC CH0 (100 Hz)
 *     → 16-sample rolling average → voltage
 *     → calibration LUT interpolation → EV (exposure value)
 *     → f-stop calculation for selected ASA + shutter speed
 *     → PWM to galvanometer needle + over/under LEDs
 *
 * Target: STM32L0xx at 16 MHz, bare-register access.
 *
 * Copyright (c) 2026 — released under MIT license.
 */

#include "metering.h"
#include "stm32l0xx.h"
#include <math.h>

/* -----------------------------------------------------------------------
 * Millisecond tick (may be shared with motor_control.c via a common
 * SysTick — here we declare a weak handler so it works standalone too)
 * ----------------------------------------------------------------------- */

static volatile uint32_t sys_tick_ms = 0;

/* Weak attribute: if motor_control.c provides SysTick_Handler, that one
 * wins and should increment our tick too.  For standalone use this fires. */
__attribute__((weak))
void SysTick_Handler(void)
{
    sys_tick_ms++;
}

static inline uint32_t millis(void) { return sys_tick_ms; }

/* -----------------------------------------------------------------------
 * Film speed table — indexed by 2-bit DIP switch value
 * ----------------------------------------------------------------------- */

static const uint16_t asa_table[ASA_COUNT] = {
    50,     /* DIP 00 */
    100,    /* DIP 01 */
    200,    /* DIP 10 */
    500,    /* DIP 11 */
};

/* -----------------------------------------------------------------------
 * Calibration lookup table: ADC millivolts → EV
 *
 * Populate this from a known-light calibration session.  The table must
 * be monotonically increasing in mV (brighter light → higher voltage
 * from the TIA).  Linear interpolation between entries.
 *
 * These default values assume a BPW34 + 1 MΩ TIA with a gain that maps
 * roughly 0–3.3 V over the range EV 1 to EV 17.  Adjust after
 * calibrating with a reference meter.
 * ----------------------------------------------------------------------- */

typedef struct {
    uint16_t mv;    /* ADC voltage in millivolts */
    float    ev;    /* corresponding exposure value (EV at ISO 100) */
} cal_point_t;

static const cal_point_t cal_table[CAL_TABLE_SIZE] = {
    {   10,   1.0f },    /* very dim — near darkness               */
    {   30,   2.0f },
    {   70,   4.0f },
    {  130,   6.0f },
    {  230,   7.0f },
    {  400,   8.0f },    /* indoor, well lit                       */
    {  650,   9.0f },
    {  950,  10.0f },
    { 1350,  11.0f },
    { 1800,  12.0f },    /* overcast daylight                      */
    { 2300,  13.0f },
    { 2800,  14.0f },    /* direct sunlight                        */
    { 3250,  17.0f },    /* sensor near saturation                 */
};

/* -----------------------------------------------------------------------
 * Standard f-stop scale (1/3 stop increments for needle resolution)
 *
 * We store f-number × 10 so we can use integer comparisons for the
 * galvanometer range mapping while keeping 1/3-stop granularity.
 * ----------------------------------------------------------------------- */

static const uint16_t fstop_scale_x10[] = {
    14, 16, 18,     /* f/1.4  f/1.6  f/1.8  */
    20, 22, 25,     /* f/2    f/2.2  f/2.5  */
    28, 32, 35,     /* f/2.8  f/3.2  f/3.5  */
    40, 45, 50,     /* f/4    f/4.5  f/5    */
    56, 63, 71,     /* f/5.6  f/6.3  f/7.1  */
    80, 90, 100,    /* f/8    f/9    f/10   */
   110, 130, 160,   /* f/11   f/13   f/16   */
   180, 200, 220,   /* f/18   f/20   f/22   */
};

#define FSTOP_SCALE_LEN  (sizeof(fstop_scale_x10) / sizeof(fstop_scale_x10[0]))

/* -----------------------------------------------------------------------
 * Rolling average filter
 * ----------------------------------------------------------------------- */

static uint16_t filter_buf[METER_FILTER_SIZE];
static uint8_t  filter_idx  = 0;
static uint32_t filter_sum  = 0;
static uint8_t  filter_full = 0;   /* set once buffer has been filled once */

static void filter_reset(void)
{
    for (uint8_t i = 0; i < METER_FILTER_SIZE; i++)
        filter_buf[i] = 0;
    filter_idx  = 0;
    filter_sum  = 0;
    filter_full = 0;
}

/** Push a new raw ADC reading into the filter; return filtered value. */
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
    return (uint16_t)(filter_sum / count);
}

/* -----------------------------------------------------------------------
 * Module state
 * ----------------------------------------------------------------------- */

static uint32_t last_sample_ms = 0;
static uint32_t filtered_mv    = 0;
static float    current_ev     = 0.0f;
static float    current_fstop  = 0.0f;
static uint16_t current_asa    = 100;

/* -----------------------------------------------------------------------
 * ADC helpers (bare register, single-conversion on ADC_IN0)
 * ----------------------------------------------------------------------- */

static void adc_init(void)
{
    /* Enable ADC clock */
    RCC->APB2ENR |= RCC_APB2ENR_ADCEN;

    /* PA0 as analog (MODER = 11) */
    GPIOA->MODER |= (3U << (METER_ADC_CHANNEL * 2));

    /* Ensure ADC is disabled before configuring */
    if (ADC1->CR & ADC_CR_ADEN) {
        ADC1->CR |= ADC_CR_ADDIS;
        while (ADC1->CR & ADC_CR_ADEN) { /* wait */ }
    }

    /* Calibrate the ADC */
    ADC1->CR |= ADC_CR_ADCAL;
    while (ADC1->CR & ADC_CR_ADCAL) { /* wait */ }

    /* 12-bit resolution (default), right-aligned */
    ADC1->CFGR1 &= ~(ADC_CFGR1_RES | ADC_CFGR1_ALIGN);

    /* Sample time: 79.5 ADC clock cycles — good for high-impedance TIA */
    ADC1->SMPR = 0x05U;    /* SMP = 101 → 79.5 cycles */

    /* Select channel 0 */
    ADC1->CHSELR = (1U << METER_ADC_CHANNEL);

    /* Enable the ADC */
    ADC1->ISR |= ADC_ISR_ADRDY;        /* clear ready flag */
    ADC1->CR  |= ADC_CR_ADEN;
    while (!(ADC1->ISR & ADC_ISR_ADRDY)) { /* wait */ }
}

/** Start a single conversion and return the 12-bit result. */
static uint16_t adc_read(void)
{
    ADC1->CR |= ADC_CR_ADSTART;
    while (!(ADC1->ISR & ADC_ISR_EOC)) { /* wait */ }
    return (uint16_t)ADC1->DR;
}

/* -----------------------------------------------------------------------
 * GPIO init: galvanometer PWM, LEDs, DIP switch, FPS select
 * ----------------------------------------------------------------------- */

static void gpio_init(void)
{
    RCC->IOPENR |= RCC_IOPENR_GPIOAEN | RCC_IOPENR_GPIOBEN;

    /* PA4: TIM22 CH1 alternate function (AF4), push-pull */
    GPIOA->MODER  = (GPIOA->MODER  & ~(3U << (GALVO_PIN * 2)))
                   |  (2U << (GALVO_PIN * 2));
    GPIOA->AFR[0] = (GPIOA->AFR[0] & ~(0xFU << (GALVO_PIN * 4)))
                   |  (GALVO_AF << (GALVO_PIN * 4));

    /* PA5: green LED — output push-pull */
    GPIOA->MODER  = (GPIOA->MODER  & ~(3U << (GREEN_LED_PIN * 2)))
                   |  (1U << (GREEN_LED_PIN * 2));

    /* PA6: red LED — output push-pull */
    GPIOA->MODER  = (GPIOA->MODER  & ~(3U << (RED_LED_PIN * 2)))
                   |  (1U << (RED_LED_PIN * 2));

    /* PB0, PB1: DIP switch inputs with pull-down */
    GPIOB->MODER &= ~((3U << (DIP_BIT0_PIN * 2)) | (3U << (DIP_BIT1_PIN * 2)));
    GPIOB->PUPDR  = (GPIOB->PUPDR & ~((3U << (DIP_BIT0_PIN * 2)) |
                                        (3U << (DIP_BIT1_PIN * 2))))
                   |  (2U << (DIP_BIT0_PIN * 2))
                   |  (2U << (DIP_BIT1_PIN * 2));

    /* PA1: FPS select — input with pull-down (may already be configured
     * by motor_control.c; safe to set again) */
    GPIOA->MODER &= ~(3U << (FPS_SEL_PIN * 2));
    GPIOA->PUPDR  = (GPIOA->PUPDR & ~(3U << (FPS_SEL_PIN * 2)))
                   |  (2U << (FPS_SEL_PIN * 2));
}

/* -----------------------------------------------------------------------
 * Galvanometer PWM (TIM22 CH1)
 * ----------------------------------------------------------------------- */

static void galvo_pwm_init(void)
{
    RCC->APB2ENR |= RCC_APB2ENR_TIM22EN;

    TIM22->PSC  = GALVO_PWM_PRESCALER;
    TIM22->ARR  = GALVO_PWM_PERIOD;
    TIM22->CCR1 = 0;

    /* CH1: PWM mode 1 (OC1M = 110), preload enable */
    TIM22->CCMR1 = (TIM22->CCMR1 & ~0x7FU)
                  | TIM_CCMR1_OC1M_2 | TIM_CCMR1_OC1M_1
                  | TIM_CCMR1_OC1PE;

    TIM22->CCER |= TIM_CCER_CC1E;
    TIM22->CR1  |= TIM_CR1_ARPE;
    TIM22->EGR   = TIM_EGR_UG;
    TIM22->CR1  |= TIM_CR1_CEN;
}

/** Set galvanometer needle position: 0 = full left (f/1.4), 999 = full right (f/22). */
static void galvo_set(uint16_t duty)
{
    if (duty > GALVO_PWM_PERIOD)
        duty = GALVO_PWM_PERIOD;
    TIM22->CCR1 = duty;
}

/* -----------------------------------------------------------------------
 * LED control
 * ----------------------------------------------------------------------- */

static inline void green_led(uint8_t on)
{
    if (on) GPIOA->BSRR = (1U << GREEN_LED_PIN);
    else    GPIOA->BSRR = (1U << (GREEN_LED_PIN + 16));
}

static inline void red_led(uint8_t on)
{
    if (on) GPIOA->BSRR = (1U << RED_LED_PIN);
    else    GPIOA->BSRR = (1U << (RED_LED_PIN + 16));
}

/* -----------------------------------------------------------------------
 * Input readers
 * ----------------------------------------------------------------------- */

/** Read 2-bit DIP switch on PB0:PB1 and return ASA value. */
static uint16_t read_asa(void)
{
    uint8_t bits = 0;
    if (GPIOB->IDR & (1U << DIP_BIT0_PIN)) bits |= 1U;
    if (GPIOB->IDR & (1U << DIP_BIT1_PIN)) bits |= 2U;
    return asa_table[bits];
}

/** Read FPS select switch.  Returns 18 or 24. */
static uint8_t read_fps(void)
{
    return (GPIOA->IDR & (1U << FPS_SEL_PIN)) ? 24U : 18U;
}

/* -----------------------------------------------------------------------
 * Calibration: voltage → EV (linear interpolation in LUT)
 *
 * The table maps ADC millivolts to EV at ISO 100.  For other film
 * speeds we apply the standard offset:
 *   EV_actual = EV_100 + log2(ASA / 100)
 *
 * This gives us an EV that accounts for film sensitivity — a higher
 * ASA effectively makes the scene "brighter" by the same amount.
 * ----------------------------------------------------------------------- */

static float lut_mv_to_ev100(uint32_t mv)
{
    /* Clamp to table bounds */
    if (mv <= cal_table[0].mv)
        return cal_table[0].ev;
    if (mv >= cal_table[CAL_TABLE_SIZE - 1].mv)
        return cal_table[CAL_TABLE_SIZE - 1].ev;

    /* Find the bracketing segment and interpolate */
    for (uint8_t i = 1; i < CAL_TABLE_SIZE; i++) {
        if (mv <= cal_table[i].mv) {
            float frac = (float)(mv - cal_table[i - 1].mv) /
                         (float)(cal_table[i].mv - cal_table[i - 1].mv);
            return cal_table[i - 1].ev + frac * (cal_table[i].ev - cal_table[i - 1].ev);
        }
    }
    return cal_table[CAL_TABLE_SIZE - 1].ev;
}

/* -----------------------------------------------------------------------
 * Exposure math
 *
 * The fundamental exposure equation:
 *   EV = log2(N² / t)
 * where N = f-number, t = shutter time in seconds.
 *
 * Solving for N:
 *   N = sqrt(2^EV × t)
 *
 * EV here is the *scene* EV adjusted for film speed:
 *   EV_scene = EV_100 + log2(ASA / 100)
 * ----------------------------------------------------------------------- */

static float compute_fstop(float ev100, uint16_t asa, float shutter_s)
{
    /* Adjust EV for film speed */
    float ev = ev100 + log2f((float)asa / 100.0f);

    /* N = sqrt(2^EV * t) */
    float n_squared = powf(2.0f, ev) * shutter_s;
    if (n_squared < 0.0f) n_squared = 0.0f;
    return sqrtf(n_squared);
}

/* -----------------------------------------------------------------------
 * Map an f-stop value to galvanometer PWM duty (0 .. GALVO_PWM_PERIOD)
 *
 * We use a log2 mapping so that each whole stop occupies equal needle
 * travel, matching how photographers think about aperture.
 *
 *   needle% = (log2(f) - log2(f_min)) / (log2(f_max) - log2(f_min))
 * ----------------------------------------------------------------------- */

static uint16_t fstop_to_galvo(float fstop)
{
    const float f_min = (float)FSTOP_MIN_X10 / 10.0f;  /* 1.4  */
    const float f_max = (float)FSTOP_MAX_X10 / 10.0f;  /* 22.0 */

    if (fstop <= f_min) return 0;
    if (fstop >= f_max) return GALVO_PWM_PERIOD;

    float log_min   = log2f(f_min);
    float log_max   = log2f(f_max);
    float log_f     = log2f(fstop);
    float fraction  = (log_f - log_min) / (log_max - log_min);

    return (uint16_t)(fraction * (float)GALVO_PWM_PERIOD);
}

/* -----------------------------------------------------------------------
 * Public API
 * ----------------------------------------------------------------------- */

void meter_init(void)
{
    /* SysTick — only configure if not already running (motor_control may own it) */
    if (!(SysTick->CTRL & SysTick_CTRL_ENABLE_Msk)) {
        SysTick->LOAD = 16000U - 1U;
        SysTick->VAL  = 0;
        SysTick->CTRL = SysTick_CTRL_CLKSOURCE_Msk |
                        SysTick_CTRL_TICKINT_Msk    |
                        SysTick_CTRL_ENABLE_Msk;
    }

    gpio_init();
    adc_init();
    galvo_pwm_init();
    filter_reset();

    green_led(0);
    red_led(0);
    galvo_set(0);

    last_sample_ms = millis();
}

void meter_update(void)
{
    uint32_t now = millis();
    uint32_t sample_interval_ms = 1000U / METER_SAMPLE_HZ;  /* 10 ms */

    /* ---- ADC sampling at METER_SAMPLE_HZ ----------------------------- */
    if ((now - last_sample_ms) < sample_interval_ms)
        return;
    last_sample_ms = now;

    /* Read ADC and push through rolling average filter */
    uint16_t raw     = adc_read();
    uint16_t avg_raw = filter_push(raw);

    /* Convert to millivolts: mv = raw * VREF / resolution */
    filtered_mv = ((uint32_t)avg_raw * ADC_VREF_MV) / ADC_RESOLUTION;

    /* ---- EV computation ---------------------------------------------- */
    float ev100 = lut_mv_to_ev100(filtered_mv);

    /* ---- Read user selections ---------------------------------------- */
    current_asa = read_asa();
    uint8_t fps = read_fps();

    /* Shutter speed depends on frame rate.  With a 180° shutter:
     *   18 fps → each frame exposed for 1/36 s
     *   24 fps → each frame exposed for 1/48 s */
    float shutter_s = (fps == 24U) ? SHUTTER_24FPS : SHUTTER_18FPS;

    /* ---- f-stop calculation ------------------------------------------ */
    current_fstop = compute_fstop(ev100, current_asa, shutter_s);
    current_ev    = ev100 + log2f((float)current_asa / 100.0f);

    /* ---- Galvanometer needle ----------------------------------------- */
    uint16_t galvo_duty = fstop_to_galvo(current_fstop);
    galvo_set(galvo_duty);

    /* ---- Exposure warning LEDs --------------------------------------- */

    /* Determine how far off the computed f-stop is from the usable range.
     * "Under-exposed by N stops" means the scene needs N more stops of
     * light than the lens can provide (f-stop below f/1.4).
     *
     *   stops_under = log2(f_min / f_actual)     (positive if under)
     *
     * Over f/22 could indicate overexposure but the brief says only
     * warn on underexposure. */

    float f_min = (float)FSTOP_MIN_X10 / 10.0f;

    if (current_fstop < f_min) {
        /* Underexposed: computed f-stop is wider than f/1.4 */
        float stops_under = log2f(f_min / current_fstop);

        if (stops_under > UNDER_WARN_EV) {
            /* Severely underexposed — blink red */
            green_led(0);
            uint8_t blink = ((now % RED_BLINK_PERIOD_MS) < (RED_BLINK_PERIOD_MS / 2));
            red_led(blink);
        } else {
            /* Slightly under but within 2 stops — steady red */
            green_led(0);
            red_led(1);
        }
    } else {
        /* Exposure is achievable — green */
        green_led(1);
        red_led(0);
    }
}

uint32_t meter_get_mv(void)
{
    return filtered_mv;
}

float meter_get_ev(void)
{
    return current_ev;
}

float meter_get_fstop(void)
{
    return current_fstop;
}

uint16_t meter_get_asa(void)
{
    return current_asa;
}

/* -----------------------------------------------------------------------
 * Standalone main — define METERING_STANDALONE to build as a self-
 * contained binary for testing the metering subsystem alone.
 * ----------------------------------------------------------------------- */

#ifdef METERING_STANDALONE

int main(void)
{
    meter_init();
    for (;;) {
        meter_update();
    }
}

#endif /* METERING_STANDALONE */
