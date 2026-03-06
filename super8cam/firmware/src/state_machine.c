/**
 * state_machine.c — Top-level camera state machine.
 *
 * States: IDLE -> RUNNING -> STOPPING -> IDLE
 *                         -> CARTRIDGE_EMPTY -> IDLE
 *
 * Integrates motor_control, metering, and encoder subsystems.
 */

#include "state_machine.h"
#include "motor_control.h"
#include "metering.h"
#include "encoder.h"
#include "config.h"
#include "pinmap.h"
#include "stm32l0xx.h"

extern volatile uint32_t g_tick_ms;

static app_state_t state = APP_IDLE;
static uint32_t stop_start_ms = 0;
static uint8_t  stall_count   = 0;
static uint32_t last_frame_ms = 0;

static inline uint8_t trigger_pressed(void)
{
    return !(PIN_TRIGGER_PORT->IDR & (1U << PIN_TRIGGER_PIN));
}

void state_machine_init(void)
{
    state = APP_IDLE;
    stall_count = 0;
}

void state_machine_update(void)
{
    uint32_t now = g_tick_ms;

    /* Metering always runs (viewfinder preview) */
    meter_update();

    switch (state) {
    case APP_IDLE:
        if (trigger_pressed()) {
            last_frame_ms = now;
            stall_count = 0;
            state = APP_RUNNING;
        }
        break;

    case APP_RUNNING:
        motor_update();

        if (!trigger_pressed()) {
            stop_start_ms = now;
            state = APP_STOPPING;
            break;
        }

        if (motor_is_stalled()) {
            motor_clear_fault();
            state = APP_IDLE;
            break;
        }

        /* Cartridge end detection */
        if ((now - last_frame_ms) > CART_FRAME_TIMEOUT_MS) {
            stall_count++;
            last_frame_ms = now;
            if (stall_count >= CART_EMPTY_FRAME_LIMIT) {
                TIM2->CCR1 = 0;
                state = APP_CARTRIDGE_EMPTY;
            }
        } else if (encoder_has_new_data()) {
            encoder_clear_new_data();
            last_frame_ms = now;
            stall_count = 0;
        }
        break;

    case APP_STOPPING:
        motor_update();
        if (motor_get_fps() < 1.0f || (now - stop_start_ms) > 2000U)
            state = APP_IDLE;
        break;

    case APP_CARTRIDGE_EMPTY:
        if (!trigger_pressed())
            state = APP_IDLE;
        break;
    }
}

app_state_t state_machine_get_state(void) { return state; }
uint32_t state_machine_get_frame_count(void) { return encoder_get_frame_count(); }
