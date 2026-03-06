/**
 * state_machine.c — Top-level camera state machine.
 *
 * 8 states:
 *   POWER_ON         Self-test on startup
 *   IDLE             Waiting for trigger, metering active
 *   STARTING         Motor ramp 0 -> target over ~300 ms
 *   RUNNING          Closed-loop filming
 *   STOPPING         Brake motor, wait for claw cycle completion
 *   STALL            Motor stall detected (blink red 3x)
 *   CARTRIDGE_EMPTY  Encoder shows no advance for 5 frames
 *   LOW_BATTERY      Voltage below shutdown threshold
 */

#include "state_machine.h"
#include "motor_control.h"
#include "metering.h"
#include "encoder.h"
#include "config.h"
#include "pinmap.h"
#include "stm32l0xx.h"

extern volatile uint32_t g_tick_ms;

static app_state_t state = APP_POWER_ON;
static uint32_t state_enter_ms  = 0;
static uint8_t  stall_count     = 0;
static uint32_t last_frame_ms   = 0;
static uint8_t  stall_blinks    = 0;
static uint32_t blink_timer_ms  = 0;

static inline uint8_t trigger_pressed(void)
{
    return !(PIN_TRIGGER_PORT->IDR & (1U << PIN_TRIGGER_PIN));
}

static inline uint8_t cartridge_present(void)
{
    return !(PIN_CART_DET_PORT->IDR & (1U << PIN_CART_DET_PIN));
}

static void enter_state(app_state_t new_state)
{
    state = new_state;
    state_enter_ms = g_tick_ms;
}

void state_machine_init(void)
{
    enter_state(APP_POWER_ON);
    stall_count = 0;
}

void state_machine_update(void)
{
    uint32_t now = g_tick_ms;

    /* Metering always runs (viewfinder preview + battery monitoring) */
    meter_update();

    /* Global low-battery check (except during POWER_ON self-test) */
    if (state != APP_POWER_ON && state != APP_LOW_BATTERY) {
        if (meter_is_shutdown_battery()) {
            motor_disable();
            enter_state(APP_LOW_BATTERY);
            return;
        }
    }

    switch (state) {

    case APP_POWER_ON:
        /* Self-test: wait for systems to stabilize */
        if ((now - state_enter_ms) >= SELFTEST_TIMEOUT_MS) {
            /* Brief green LED flash to indicate ready */
            PIN_LED_GREEN_PORT->BSRR = (1U << PIN_LED_GREEN_PIN);
            enter_state(APP_IDLE);
        }
        break;

    case APP_IDLE:
        /* Turn off green after 500 ms post-power-on */
        if ((now - state_enter_ms) > 500U) {
            PIN_LED_GREEN_PORT->BSRR = (1U << (PIN_LED_GREEN_PIN + 16));
        }

        if (trigger_pressed() && cartridge_present()) {
            last_frame_ms = now;
            stall_count = 0;
            motor_start();
            enter_state(APP_STARTING);
        }
        break;

    case APP_STARTING:
        motor_update();

        /* Transition to RUNNING once we get encoder feedback */
        if (encoder_has_new_data()) {
            encoder_clear_new_data();
            last_frame_ms = now;
            enter_state(APP_RUNNING);
            break;
        }

        /* Trigger released during startup -> abort */
        if (!trigger_pressed()) {
            motor_stop();
            enter_state(APP_STOPPING);
            break;
        }

        /* Stall during startup */
        if (motor_is_stalled()) {
            motor_clear_fault();
            stall_blinks = 0;
            blink_timer_ms = now;
            enter_state(APP_STALL);
        }
        break;

    case APP_RUNNING:
        motor_update();

        /* Trigger released -> begin stop sequence */
        if (!trigger_pressed()) {
            motor_stop();
            enter_state(APP_STOPPING);
            break;
        }

        /* Stall detection */
        if (motor_is_stalled()) {
            motor_clear_fault();
            stall_blinks = 0;
            blink_timer_ms = now;
            enter_state(APP_STALL);
            break;
        }

        /* Cartridge end detection: no new frames for too long */
        if ((now - last_frame_ms) > CART_FRAME_TIMEOUT_MS) {
            stall_count++;
            last_frame_ms = now;
            if (stall_count >= CART_EMPTY_FRAME_LIMIT) {
                motor_disable();
                enter_state(APP_CARTRIDGE_EMPTY);
                break;
            }
        }

        /* Track encoder pulses */
        if (encoder_has_new_data()) {
            encoder_clear_new_data();
            last_frame_ms = now;
            stall_count = 0;
        }
        break;

    case APP_STOPPING:
        motor_update();

        /* Done when motor reaches idle or timeout */
        if (motor_get_fps() < 1.0f || (now - state_enter_ms) > STOP_TIMEOUT_MS) {
            motor_disable();
            enter_state(APP_IDLE);
        }
        break;

    case APP_STALL:
        /* Blink red LED 3 times */
        if (stall_blinks < STALL_BLINK_COUNT * 2) {
            if ((now - blink_timer_ms) >= STALL_BLINK_MS) {
                blink_timer_ms = now;
                stall_blinks++;
                if (stall_blinks & 1) {
                    PIN_LED_RED_PORT->BSRR = (1U << PIN_LED_RED_PIN);
                } else {
                    PIN_LED_RED_PORT->BSRR = (1U << (PIN_LED_RED_PIN + 16));
                }
            }
        } else {
            /* Blink sequence done, wait for trigger release */
            PIN_LED_RED_PORT->BSRR = (1U << (PIN_LED_RED_PIN + 16));
            if (!trigger_pressed()) {
                enter_state(APP_IDLE);
            }
        }
        break;

    case APP_CARTRIDGE_EMPTY:
        /* Solid red LED until trigger released */
        PIN_LED_RED_PORT->BSRR = (1U << PIN_LED_RED_PIN);
        if (!trigger_pressed()) {
            PIN_LED_RED_PORT->BSRR = (1U << (PIN_LED_RED_PIN + 16));
            enter_state(APP_IDLE);
        }
        break;

    case APP_LOW_BATTERY:
        /* Fast red blink, no recovery until power cycle */
        PIN_LED_RED_PORT->BSRR = ((now / 100) & 1)
                                ? (1U << PIN_LED_RED_PIN)
                                : (1U << (PIN_LED_RED_PIN + 16));
        PIN_LED_GREEN_PORT->BSRR = (1U << (PIN_LED_GREEN_PIN + 16));
        break;
    }
}

app_state_t state_machine_get_state(void) { return state; }
uint32_t state_machine_get_frame_count(void) { return encoder_get_frame_count(); }

const char* state_machine_get_state_name(void)
{
    static const char* names[] = {
        "POWER_ON", "IDLE", "STARTING", "RUNNING",
        "STOPPING", "STALL", "CART_EMPTY", "LOW_BATT"
    };
    return (state <= APP_LOW_BATTERY) ? names[state] : "???";
}
