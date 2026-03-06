/**
 * main.c — Super 8 Camera Main Firmware Application
 *
 * Top-level state machine integrating all subsystems:
 *   - motor_control: PID-driven DC motor for film transport
 *   - metering:      photodiode ADC → EV → f-stop → galvanometer + LEDs
 *
 * State machine:
 *   IDLE → RUNNING → STOPPING → IDLE
 *                  → CARTRIDGE_EMPTY → IDLE
 *
 * Additional responsibilities handled here:
 *   - Trigger button via EXTI falling-edge interrupt
 *   - FPS toggle switch via EXTI interrupt (change on the fly)
 *   - Frame counter (encoder pulses)
 *   - Cartridge-end detection (no film advance for N frames)
 *   - Battery voltage monitoring (Vbat via ADC)
 *   - Unified SysTick for all subsystems
 *
 * Target: STM32L0xx (STM32L072 or similar) at 16 MHz HSI.
 *
 * Pin allocation (consolidated across all modules):
 *   PA0  — TIM2 CH1   motor PWM output
 *   PA1  — FPS select switch (EXTI1, low=18fps, high=24fps)
 *   PA2  — Trigger button (EXTI2, active low, external pull-up)
 *   PA3  — Fault / warning LED (active high)
 *   PA4  — TIM22 CH1  galvanometer PWM
 *   PA5  — Green exposure LED
 *   PA6  — Red exposure LED
 *   PA7  — ADC_IN7    photodiode / TIA output (metering)
 *   PB0  — DIP switch bit 0 (ASA select)
 *   PB1  — DIP switch bit 1 (ASA select)
 *   PB2  — Low-battery warning LED (active high)
 *   PB4  — TIM21 CH1  encoder input capture
 *   PB5  — Cartridge-empty warning LED (active high)
 *   VBAT — ADC_IN18   internal Vbat channel (or external divider on ADC_IN8)
 *
 * Copyright (c) 2026 — released under MIT license.
 */

#include "stm32l0xx.h"
#include "motor_control.h"
#include "metering.h"
#include <stdint.h>

/* =======================================================================
 * Configuration
 * ======================================================================= */

/* Battery monitoring */
#define VBAT_ADC_CHANNEL        18U         /* internal VBAT (or use 8 for PA8)   */
#define VBAT_SAMPLE_INTERVAL_MS 1000U       /* check battery once per second      */
#define VBAT_LOW_THRESHOLD_MV   4200U       /* 4xAA: 4 × 1.05 V = 4.2 V minimum */
#define VBAT_ADC_VREF_MV        3300U
#define VBAT_ADC_RESOLUTION     4096U
/* The internal VBAT channel reads through a /2 divider on L0 series */
#define VBAT_DIVIDER            2U

/* Cartridge-end detection */
#define CART_EMPTY_FRAME_LIMIT  5U          /* consecutive stalled frames          */
#define CART_FRAME_TIMEOUT_MS   250U        /* max time per frame at 18fps ~55 ms  */
                                            /* generous margin for slow starts     */

/* Warning LED blink rate */
#define WARN_BLINK_PERIOD_MS    500U

/* Debounce for trigger and FPS switch */
#define DEBOUNCE_MS             30U

/* LED pins for main.c-owned indicators */
#define LOW_BATT_LED_PIN        2U          /* PB2 */
#define CART_EMPTY_LED_PIN      5U          /* PB5 */

/* =======================================================================
 * Shared millisecond tick
 *
 * SysTick is owned by main.c.  motor_control.c and metering.c both
 * declare __attribute__((weak)) SysTick_Handlers; this strong definition
 * wins and feeds the tick to all modules via the global symbol.
 * ======================================================================= */

volatile uint32_t g_tick_ms = 0;

void SysTick_Handler(void)
{
    g_tick_ms++;
}

static inline uint32_t millis(void) { return g_tick_ms; }

/* =======================================================================
 * Application state machine
 * ======================================================================= */

typedef enum {
    APP_IDLE,               /* motor off, metering active for preview       */
    APP_RUNNING,            /* filming: motor + metering + frame counting   */
    APP_STOPPING,           /* trigger released, motor ramping down         */
    APP_CARTRIDGE_EMPTY     /* no film advance detected — motor killed      */
} app_state_t;

static volatile app_state_t app_state = APP_IDLE;

/* Trigger and FPS switch state (set by EXTI ISRs) */
static volatile uint8_t  trigger_pressed  = 0;
static volatile uint8_t  trigger_released = 0;  /* edge flag */
static volatile uint8_t  fps_changed      = 0;
static volatile uint32_t trigger_edge_ms  = 0;
static volatile uint32_t fps_edge_ms      = 0;

/* Frame counter */
static volatile uint32_t frame_count      = 0;
static volatile uint32_t last_frame_ms    = 0;

/* Cartridge-end tracking */
static uint8_t  stall_frame_count = 0;

/* Battery */
static uint32_t vbat_mv           = 6000U;  /* assume healthy until first read */
static uint8_t  low_battery       = 0;

/* =======================================================================
 * EXTI interrupt handlers
 * ======================================================================= */

/**
 * EXTI line 2 — trigger button (PA2), falling edge = pressed.
 * We also detect the release (rising edge) by enabling both edges.
 */
void EXTI2_3_IRQHandler(void)
{
    if (EXTI->PR & (1U << 2)) {
        EXTI->PR = (1U << 2);                   /* clear pending             */

        uint32_t now = g_tick_ms;
        if ((now - trigger_edge_ms) < DEBOUNCE_MS)
            return;                              /* bounce — ignore           */
        trigger_edge_ms = now;

        /* Read current pin level: low = pressed, high = released */
        if (!(GPIOA->IDR & (1U << 2))) {
            trigger_pressed = 1;
        } else {
            trigger_pressed = 0;
            trigger_released = 1;                /* edge flag for state machine */
        }
    }
}

/**
 * EXTI line 1 — FPS toggle switch (PA1), both edges.
 */
void EXTI0_1_IRQHandler(void)
{
    if (EXTI->PR & (1U << 1)) {
        EXTI->PR = (1U << 1);

        uint32_t now = g_tick_ms;
        if ((now - fps_edge_ms) < DEBOUNCE_MS)
            return;
        fps_edge_ms = now;
        fps_changed = 1;
    }
}

/**
 * TIM21 capture — we chain into the motor's encoder ISR but also
 * count frames here for the main application.
 *
 * NOTE: The real encoder ISR lives in motor_control.c (TIM21_IRQHandler).
 * To count frames without duplicating interrupt ownership, we hook into
 * the motor module.  One clean approach: motor_control.c calls a weak
 * callback after each capture.  Here we provide the strong definition.
 *
 * If your build doesn't use weak callbacks, an alternative is to read
 * the frame count from the motor module.  We define the callback here:
 */
void motor_encoder_pulse_callback(void)
{
    frame_count++;
    last_frame_ms = g_tick_ms;
}

/* =======================================================================
 * GPIO & EXTI initialisation (main.c-owned pins only)
 *
 * Subsystem-specific GPIOs are initialised by motor_init() and
 * meter_init().  Here we set up EXTI, battery LED, and cartridge LED.
 * ======================================================================= */

static void main_gpio_init(void)
{
    RCC->IOPENR |= RCC_IOPENR_GPIOAEN | RCC_IOPENR_GPIOBEN;

    /* PB2: low-battery LED — output push-pull */
    GPIOB->MODER = (GPIOB->MODER & ~(3U << (LOW_BATT_LED_PIN * 2)))
                  | (1U << (LOW_BATT_LED_PIN * 2));

    /* PB5: cartridge-empty LED — output push-pull */
    GPIOB->MODER = (GPIOB->MODER & ~(3U << (CART_EMPTY_LED_PIN * 2)))
                  | (1U << (CART_EMPTY_LED_PIN * 2));

    /* Turn both off initially */
    GPIOB->BSRR = (1U << (LOW_BATT_LED_PIN + 16))
                | (1U << (CART_EMPTY_LED_PIN + 16));
}

static void exti_init(void)
{
    /* Enable SYSCFG clock for EXTI mux */
    RCC->APB2ENR |= RCC_APB2ENR_SYSCFGEN;

    /* --- PA2 trigger: EXTI2, both edges (detect press AND release) --- */
    /* EXTI2 → GPIOA (SYSCFG_EXTICR1 bits [11:8] = 0000 for PA) */
    SYSCFG->EXTICR[0] = (SYSCFG->EXTICR[0] & ~(0xFU << 8)) | (0x0U << 8);

    EXTI->IMR  |=  (1U << 2);               /* unmask line 2               */
    EXTI->RTSR |=  (1U << 2);               /* rising edge  (release)      */
    EXTI->FTSR |=  (1U << 2);               /* falling edge (press)        */

    NVIC_EnableIRQ(EXTI2_3_IRQn);
    NVIC_SetPriority(EXTI2_3_IRQn, 2);

    /* --- PA1 FPS switch: EXTI1, both edges --- */
    SYSCFG->EXTICR[0] = (SYSCFG->EXTICR[0] & ~(0xFU << 4)) | (0x0U << 4);

    EXTI->IMR  |=  (1U << 1);
    EXTI->RTSR |=  (1U << 1);
    EXTI->FTSR |=  (1U << 1);

    NVIC_EnableIRQ(EXTI0_1_IRQn);
    NVIC_SetPriority(EXTI0_1_IRQn, 3);
}

/* =======================================================================
 * Clock configuration — HSI16 at 16 MHz
 * ======================================================================= */

static void clock_init(void)
{
    /* Enable HSI16 */
    RCC->CR |= RCC_CR_HSION;
    while (!(RCC->CR & RCC_CR_HSIRDY)) { /* wait */ }

    /* Select HSI16 as system clock */
    RCC->CFGR = (RCC->CFGR & ~RCC_CFGR_SW) | RCC_CFGR_SW_HSI;
    while ((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_HSI) { /* wait */ }
}

static void systick_init(void)
{
    SysTick->LOAD = 16000U - 1U;            /* 16 MHz / 16000 = 1 kHz      */
    SysTick->VAL  = 0;
    SysTick->CTRL = SysTick_CTRL_CLKSOURCE_Msk
                  | SysTick_CTRL_TICKINT_Msk
                  | SysTick_CTRL_ENABLE_Msk;
}

/* =======================================================================
 * Battery voltage monitoring
 *
 * Uses the internal VBAT ADC channel (or an external divider).
 * The STM32L0 internal channel reads VBAT/2 through a built-in divider.
 * ======================================================================= */

static void vbat_adc_init(void)
{
    /* ADC clock already enabled by meter_init().
     * Enable the VBAT channel in ADC_CCR. */
    ADC->CCR |= ADC_CCR_VBATEN;
}

static uint32_t vbat_read_mv(void)
{
    /* Temporarily switch ADC channel to VBAT, take one reading, switch back.
     * This is a blocking read — acceptable at 1 Hz. */

    /* Save current channel selection */
    uint32_t saved_chselr = ADC1->CHSELR;

    /* Select VBAT channel */
    ADC1->CHSELR = (1U << VBAT_ADC_CHANNEL);

    /* Longer sample time for internal channels: max setting */
    uint32_t saved_smpr = ADC1->SMPR;
    ADC1->SMPR = 0x07U;                     /* 160.5 cycles                 */

    /* Start conversion */
    ADC1->CR |= ADC_CR_ADSTART;
    while (!(ADC1->ISR & ADC_ISR_EOC)) { /* wait */ }
    uint16_t raw = (uint16_t)ADC1->DR;

    /* Restore metering channel config */
    ADC1->CHSELR = saved_chselr;
    ADC1->SMPR   = saved_smpr;

    /* Convert: mv = raw * VREF / resolution * divider */
    uint32_t mv = ((uint32_t)raw * VBAT_ADC_VREF_MV * VBAT_DIVIDER) / VBAT_ADC_RESOLUTION;
    return mv;
}

/* =======================================================================
 * LED helpers
 * ======================================================================= */

static inline void low_batt_led(uint8_t on)
{
    if (on) GPIOB->BSRR = (1U << LOW_BATT_LED_PIN);
    else    GPIOB->BSRR = (1U << (LOW_BATT_LED_PIN + 16));
}

static inline void cart_empty_led(uint8_t on)
{
    if (on) GPIOB->BSRR = (1U << CART_EMPTY_LED_PIN);
    else    GPIOB->BSRR = (1U << (CART_EMPTY_LED_PIN + 16));
}

/* =======================================================================
 * Cartridge-end detection
 *
 * If the motor is running but no encoder pulses arrive for
 * CART_FRAME_TIMEOUT_MS, we count it as a "missed frame".  After
 * CART_EMPTY_FRAME_LIMIT consecutive misses, the cartridge is empty.
 * ======================================================================= */

static uint8_t check_cartridge_end(void)
{
    uint32_t now = millis();

    if ((now - last_frame_ms) > CART_FRAME_TIMEOUT_MS) {
        stall_frame_count++;
        last_frame_ms = now;                 /* reset window for next check  */

        if (stall_frame_count >= CART_EMPTY_FRAME_LIMIT)
            return 1;                        /* cartridge is empty           */
    } else {
        /* Got a pulse recently — reset the counter */
        stall_frame_count = 0;
    }
    return 0;
}

/* =======================================================================
 * Motor subsystem wrappers
 *
 * motor_control.c has its own internal state machine.  From main.c we
 * call motor_update() which handles ramp/PID/stop internally.  But the
 * main state machine needs to START and STOP the motor explicitly.
 *
 * We provide thin wrappers that poke the motor into the right mode.
 * In a real project you'd add motor_start() / motor_stop() to the
 * motor_control API.  Here we simulate by checking the trigger state
 * that motor_control.c reads, or by calling motor_update() in the
 * appropriate context.
 *
 * Since motor_control.c reads the trigger GPIO directly, and we control
 * the trigger via EXTI, the motor will respond naturally when the
 * trigger is physically pressed/released.  Our state machine layers
 * additional logic on top (frame counting, cartridge detection, etc.)
 * and can force-stop the motor by clearing the trigger state or
 * calling motor_clear_fault().
 * ======================================================================= */

/**
 * Force the motor to stop immediately (e.g. on cartridge end).
 * We do this by driving the PWM duty to zero directly.
 * This bypasses motor_control's soft-stop for emergency situations.
 */
static void motor_emergency_stop(void)
{
    /* Kill PWM immediately */
    TIM2->CCR1 = 0;
    motor_clear_fault();
}

/* =======================================================================
 * Main application state machine
 * ======================================================================= */

static void app_run(void)
{
    static uint32_t last_vbat_ms       = 0;
    static uint32_t stop_started_ms    = 0;
    static uint32_t cart_warn_start_ms = 0;

    uint32_t now = millis();

    /* ---- Battery monitoring (runs in all states) ---------------------- */
    if ((now - last_vbat_ms) >= VBAT_SAMPLE_INTERVAL_MS) {
        last_vbat_ms = now;
        vbat_mv = vbat_read_mv();
        low_battery = (vbat_mv < VBAT_LOW_THRESHOLD_MV) ? 1 : 0;

        /* Blink low-battery LED */
        if (low_battery)
            low_batt_led((now / WARN_BLINK_PERIOD_MS) & 1U);
        else
            low_batt_led(0);
    }

    /* ---- Metering runs continuously (preview in viewfinder) ----------- */
    meter_update();

    /* ---- State machine ------------------------------------------------ */
    switch (app_state) {

    /* ................................................................ */
    case APP_IDLE:
        cart_empty_led(0);
        stall_frame_count = 0;

        /* Wait for trigger press */
        if (trigger_pressed) {
            frame_count   = 0;
            last_frame_ms = now;
            app_state     = APP_RUNNING;
        }
        break;

    /* ................................................................ */
    case APP_RUNNING:
        /* Motor control runs its own PID + ramp-up internally */
        motor_update();

        /* Check for trigger release */
        if (trigger_released) {
            trigger_released = 0;
            stop_started_ms  = now;
            app_state        = APP_STOPPING;
            break;
        }

        /* Check for motor stall (handled by motor_control.c) */
        if (motor_is_stalled()) {
            motor_emergency_stop();
            app_state = APP_IDLE;
            break;
        }

        /* Check for cartridge end */
        if (check_cartridge_end()) {
            motor_emergency_stop();
            cart_warn_start_ms = now;
            app_state = APP_CARTRIDGE_EMPTY;
            break;
        }

        /* FPS change during filming: motor_control reads the GPIO
         * directly, so the PID target updates automatically.  We just
         * clear the flag. */
        if (fps_changed)
            fps_changed = 0;

        break;

    /* ................................................................ */
    case APP_STOPPING:
        /* Let motor_control handle the soft deceleration ramp.
         * motor_update() will see trigger_pressed == 0 and ramp down. */
        motor_update();

        /* Wait until the motor is back to idle (duty reaches 0).
         * motor_get_fps() will drop to ~0 once stopped. */
        if (motor_get_fps() < 1.0f || (now - stop_started_ms) > 2000U) {
            /* Motor has stopped or timeout — return to idle */
            app_state = APP_IDLE;
        }
        break;

    /* ................................................................ */
    case APP_CARTRIDGE_EMPTY:
        /* Motor already killed.  Blink cartridge warning LED.
         * Return to IDLE when trigger is released. */
        cart_empty_led((now / WARN_BLINK_PERIOD_MS) & 1U);

        if (!trigger_pressed) {
            cart_empty_led(0);
            app_state = APP_IDLE;
        }
        break;
    }
}

/* =======================================================================
 * Entry point
 * ======================================================================= */

int main(void)
{
    /* ---- Clock ---- */
    clock_init();
    systick_init();

    /* ---- GPIO & interrupts ---- */
    main_gpio_init();
    exti_init();

    /* ---- Subsystems ---- */
    motor_init();
    meter_init();

    /* ---- Battery ADC channel ---- */
    vbat_adc_init();

    /* ---- Superloop ---- */
    for (;;) {
        app_run();
    }
}

/* =======================================================================
 * Default / unused interrupt stubs
 *
 * Catch unexpected interrupts during development.  In production, these
 * map to the infinite-loop default handler provided by the startup file.
 * ======================================================================= */

void HardFault_Handler(void)
{
    /* Kill motor, light fault LED, hang */
    TIM2->CCR1 = 0;
    GPIOA->BSRR = (1U << 3);               /* PA3 fault LED on            */
    for (;;) { __WFI(); }
}

void NMI_Handler(void)         { for (;;) { __WFI(); } }
void SVC_Handler(void)         { for (;;) { __WFI(); } }
void PendSV_Handler(void)      { for (;;) { __WFI(); } }
