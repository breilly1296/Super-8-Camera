/**
 * state_machine.h — Top-level camera state machine.
 *
 * States: POWER_ON -> IDLE -> STARTING -> RUNNING -> STOPPING -> IDLE
 *                                      -> STALL -> IDLE
 *                                      -> CARTRIDGE_EMPTY -> IDLE
 *                          -> LOW_BATTERY (from any state)
 */
#ifndef STATE_MACHINE_H
#define STATE_MACHINE_H

#include <stdint.h>

typedef enum {
    APP_POWER_ON,
    APP_IDLE,
    APP_STARTING,
    APP_RUNNING,
    APP_STOPPING,
    APP_STALL,
    APP_CARTRIDGE_EMPTY,
    APP_LOW_BATTERY
} app_state_t;

void        state_machine_init(void);
void        state_machine_update(void);
app_state_t state_machine_get_state(void);
uint32_t    state_machine_get_frame_count(void);
const char* state_machine_get_state_name(void);

#endif /* STATE_MACHINE_H */
