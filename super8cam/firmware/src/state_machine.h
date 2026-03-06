/**
 * state_machine.h — Top-Level Camera State Machine
 *
 * Eight states governing the complete camera operation:
 *
 *   POWER_ON ──→ IDLE ──→ STARTING ──→ RUNNING ──→ STOPPING ──→ IDLE
 *                  │                       │
 *                  │                       ├──→ STALL ──→ IDLE
 *                  │                       │
 *                  │                       └──→ CARTRIDGE_EMPTY ──→ IDLE
 *                  │
 *                  └──→ LOW_BATTERY (any state, motor killed)
 *
 * Integrates motor_control, encoder, and metering subsystems.
 */

#ifndef STATE_MACHINE_H
#define STATE_MACHINE_H

#include <stdint.h>

typedef enum {
    APP_POWER_ON,           /* init / self-test at boot                 */
    APP_IDLE,               /* motor off, metering active for preview   */
    APP_STARTING,           /* motor ramp-up, waiting for first encoder */
    APP_RUNNING,            /* filming: PID active + frame counting     */
    APP_STOPPING,           /* trigger released, soft deceleration      */
    APP_STALL,              /* motor stall detected — fault state       */
    APP_CARTRIDGE_EMPTY,    /* no film advance — motor killed           */
    APP_LOW_BATTERY,        /* battery below threshold — motor killed   */
} app_state_t;

/** One-time init (called after all subsystems are initialized). */
void state_machine_init(void);

/** Call from the superloop on every tick. */
void state_machine_update(void);

/** Current application state. */
app_state_t state_machine_get_state(void);

/** Total frames filmed since last trigger press. */
uint32_t state_machine_get_frame_count(void);

/** Battery voltage in millivolts (most recent reading). */
uint32_t state_machine_get_vbat_mv(void);

/** Non-zero if battery is below LOW threshold. */
uint8_t state_machine_is_low_battery(void);

/** String name of the current state (for debug output). */
const char *state_machine_state_name(void);

#endif /* STATE_MACHINE_H */
