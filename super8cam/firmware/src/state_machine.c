/**
 * state_machine.c — Top-Level Camera State Machine
 *
 * Orchestrates motor_control, encoder, and metering subsystems.
 * Handles trigger/FPS via EXTI, battery monitoring, cartridge-end
 * detection, and stall recovery.
 *
 * State transitions:
 *   POWER_ON → IDLE                   (after self-test / 100 ms delay)
 *   IDLE → STARTING                   (trigger pressed)
 *   STARTING → RUNNING                (first encoder pulse received)
 *   STARTING → STALL                  (startup timeout)
 *   RUNNING → STOPPING                (trigger released)
 *   RUNNING → STALL                   (no encoder pulses)
 *   RUNNING → CARTRIDGE_EMPTY         (N consecutive missed frames)
 *   STOPPING → IDLE                   (duty reaches 0 or timeout)
 *   STALL → IDLE                      (trigger released)
 *   CARTRIDGE_EMPTY → IDLE            (trigger released)
 *   ANY → LOW_BATTERY                 (Vbat < threshold while running)
 *   LOW_BATTERY → IDLE                (trigger released)
 *
 * Copyright (c) 2026 — released under MIT license.
 */

#include "state_machine.h"
#include "motor_control.h"
#include "metering.h"
#include "encoder.h"
#include "config.h"
#include "pinmap.h"
#include "stm32l0xx.h"

/* Global tick from main.c */
extern volatile uint32_t g_tick_ms;

/* =====================================================================
 * Internal state
 * ===================================================================== */

static app_state_t state           = APP_POWER_ON;
static uint32_t    state_enter_ms  = 0;        /* when we entered current state */
static uint32_t    stop_start_ms   = 0;
static uint8_t     stall_count     = 0;        /* consecutive missed frames     */
static uint32_t    last_frame_ms   = 0;        /* last encoder pulse timestamp  */

/* Battery monitoring */
static uint32_t    vbat_mv         = 6000U;    /* assume healthy until measured */
static uint8_t     low_battery     = 0;
static uint32_t    last_vbat_ms    = 0;

/* =====================================================================
 * Trigger input (reads GPIO directly — debouncing via EXTI in main.c
 * is optional; this polled read is the authoritative source for the
 * state machine)
 * ===================================================================== */

static inline uint8_t trigger_pressed(void)
{
    /* Active low with external pull-up */
    return !(PIN_TRIGGER_PORT->IDR & (1U << PIN_TRIGGER_PIN));
}

/* =====================================================================
 * Battery voltage monitoring
 *
 * Uses the internal VBAT ADC channel with /2 divider on STM32L0.
 * Called at 1 Hz from the state machine update loop.
 * ===================================================================== */

static void vbat_init(void)
{
    /* Enable VBAT channel in ADC common config */
    ADC->CCR |= ADC_CCR_VBATEN;
}

static uint32_t vbat_read(void)
{
    /* Save and switch ADC channel to VBAT */
    uint32_t saved_chselr = ADC1->CHSELR;
    uint32_t saved_smpr   = ADC1->SMPR;

    ADC1->CHSELR = (1U << VBAT_ADC_CHANNEL);
    ADC1->SMPR   = 0x07U;          /* 160.5 cycles for internal channels */

    ADC1->CR |= ADC_CR_ADSTART;
    while (!(ADC1->ISR & ADC_ISR_EOC)) { /* wait */ }
    uint16_t raw = (uint16_t)ADC1->DR;

    /* Restore metering channel config */
    ADC1->CHSELR = saved_chselr;
    ADC1->SMPR   = saved_smpr;

    return ((uint32_t)raw * ADC_VREF_MV * VBAT_DIVIDER) / ADC_RESOLUTION;
}

/* =====================================================================
 * LED helpers (main.c-owned LEDs: low-bat on PB2, cart-empty on PB5)
 * ===================================================================== */

static inline void lowbat_led(uint8_t on)
{
    if (on) PIN_LED_LOWBAT_PORT->BSRR = (1U << PIN_LED_LOWBAT_PIN);
    else    PIN_LED_LOWBAT_PORT->BSRR = (1U << (PIN_LED_LOWBAT_PIN + 16));
}

static inline void cart_led(uint8_t on)
{
    if (on) PIN_LED_CART_PORT->BSRR = (1U << PIN_LED_CART_PIN);
    else    PIN_LED_CART_PORT->BSRR = (1U << (PIN_LED_CART_PIN + 16));
}

/* =====================================================================
 * State transition helper
 * ===================================================================== */

static void enter_state(app_state_t new_state)
{
    state = new_state;
    state_enter_ms = g_tick_ms;
}

/* =====================================================================
 * Cartridge-end detection
 *
 * While RUNNING, if no encoder pulse for CART_FRAME_TIMEOUT_MS we
 * count a "missed frame".  After CART_EMPTY_FRAME_LIMIT consecutive
 * misses, the film is considered exhausted.
 * ===================================================================== */

static uint8_t check_cartridge_end(uint32_t now)
{
    if ((now - last_frame_ms) > CART_FRAME_TIMEOUT_MS) {
        stall_count++;
        last_frame_ms = now;            /* reset window                  */
        if (stall_count >= CART_EMPTY_FRAME_LIMIT)
            return 1;
    } else if (encoder_has_new_data()) {
        /* Fresh pulse — reset miss counter */
        last_frame_ms = now;
        stall_count = 0;
    }
    return 0;
}

/* =====================================================================
 * Public API
 * ===================================================================== */

void state_machine_init(void)
{
    enter_state(APP_POWER_ON);
    stall_count = 0;
    low_battery = 0;
    vbat_init();
}

void state_machine_update(void)
{
    uint32_t now = g_tick_ms;

    /* ---- Battery monitoring (runs in every state) -------------------- */
    if ((now - last_vbat_ms) >= VBAT_SAMPLE_INTERVAL_MS) {
        last_vbat_ms = now;
        vbat_mv = vbat_read();
        low_battery = (vbat_mv < VBAT_LOW_THRESHOLD_MV) ? 1U : 0U;

        if (low_battery)
            lowbat_led((now / WARN_BLINK_PERIOD_MS) & 1U);
        else
            lowbat_led(0);
    }

    /* ---- Metering always runs (viewfinder preview) ------------------- */
    meter_update();

    /* ---- State machine ----------------------------------------------- */
    switch (state) {

    /* ................................................................ */
    case APP_POWER_ON:
        /* Self-test period: wait 100 ms for peripherals to settle,
         * then transition to IDLE. */
        if ((now - state_enter_ms) >= 100U) {
            enter_state(APP_IDLE);
        }
        break;

    /* ................................................................ */
    case APP_IDLE:
        cart_led(0);
        stall_count = 0;

        if (trigger_pressed()) {
            /* Check battery before starting motor */
            if (low_battery) {
                motor_emergency_stop();
                enter_state(APP_LOW_BATTERY);
                break;
            }

            encoder_reset_frame_count();
            last_frame_ms = now;
            motor_start();
            enter_state(APP_STARTING);
        }
        break;

    /* ................................................................ */
    case APP_STARTING:
        motor_update();

        /* Trigger released during startup → abort */
        if (!trigger_pressed()) {
            motor_stop();
            enter_state(APP_STOPPING);
            break;
        }

        /* Motor module handles ramp internally; when it transitions
         * to RUNNING state, we follow. */
        if (motor_get_state() == MOTOR_RUNNING) {
            encoder_clear_new_data();
            enter_state(APP_RUNNING);
            break;
        }

        /* Motor detected stall during startup */
        if (motor_is_stalled()) {
            enter_state(APP_STALL);
            break;
        }
        break;

    /* ................................................................ */
    case APP_RUNNING:
        motor_update();

        /* Trigger released → soft stop */
        if (!trigger_pressed()) {
            motor_stop();
            stop_start_ms = now;
            enter_state(APP_STOPPING);
            break;
        }

        /* Low battery during filming → emergency stop */
        if (low_battery) {
            motor_emergency_stop();
            enter_state(APP_LOW_BATTERY);
            break;
        }

        /* Motor stall */
        if (motor_is_stalled()) {
            enter_state(APP_STALL);
            break;
        }

        /* Cartridge end detection */
        if (check_cartridge_end(now)) {
            motor_emergency_stop();
            enter_state(APP_CARTRIDGE_EMPTY);
            break;
        }

        /* Consume encoder new-data flag after cartridge check uses it */
        if (encoder_has_new_data())
            encoder_clear_new_data();

        break;

    /* ................................................................ */
    case APP_STOPPING:
        motor_update();

        /* Done when motor reaches idle or timeout */
        if (motor_get_state() == MOTOR_IDLE ||
            (now - stop_start_ms) > STOP_TIMEOUT_MS) {
            motor_emergency_stop();     /* ensure clean stop on timeout  */
            enter_state(APP_IDLE);
        }
        break;

    /* ................................................................ */
    case APP_STALL:
        /* Motor already killed by motor_control fault handler.
         * Blink warning LED.  Return to IDLE when trigger released. */
        PIN_LED_WARN_PORT->BSRR =
            ((now / 250U) & 1U)
            ? (1U << PIN_LED_WARN_PIN)
            : (1U << (PIN_LED_WARN_PIN + 16));

        if (!trigger_pressed()) {
            motor_clear_fault();
            PIN_LED_WARN_PORT->BSRR = (1U << (PIN_LED_WARN_PIN + 16));
            enter_state(APP_IDLE);
        }
        break;

    /* ................................................................ */
    case APP_CARTRIDGE_EMPTY:
        /* Motor already killed.  Blink cartridge LED. */
        cart_led((now / WARN_BLINK_PERIOD_MS) & 1U);

        if (!trigger_pressed()) {
            cart_led(0);
            enter_state(APP_IDLE);
        }
        break;

    /* ................................................................ */
    case APP_LOW_BATTERY:
        /* Motor killed.  Blink low-battery LED rapidly. */
        lowbat_led((now / 200U) & 1U);

        if (!trigger_pressed()) {
            lowbat_led(0);
            enter_state(APP_IDLE);
        }
        break;
    }
}

app_state_t state_machine_get_state(void)
{
    return state;
}

uint32_t state_machine_get_frame_count(void)
{
    return encoder_get_frame_count();
}

uint32_t state_machine_get_vbat_mv(void)
{
    return vbat_mv;
}

uint8_t state_machine_is_low_battery(void)
{
    return low_battery;
}

/* State name strings for debug UART */
static const char *state_names[] = {
    "POWER_ON",
    "IDLE",
    "STARTING",
    "RUNNING",
    "STOPPING",
    "STALL",
    "CART_EMPTY",
    "LOW_BATT",
};

const char *state_machine_state_name(void)
{
    if (state <= APP_LOW_BATTERY)
        return state_names[state];
    return "UNKNOWN";
}
