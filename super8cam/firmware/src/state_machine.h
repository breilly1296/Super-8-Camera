/**
 * state_machine.h — Top-level camera state machine
 */
#ifndef STATE_MACHINE_H
#define STATE_MACHINE_H

#include <stdint.h>

typedef enum {
    APP_IDLE,
    APP_RUNNING,
    APP_STOPPING,
    APP_CARTRIDGE_EMPTY,
} app_state_t;

void state_machine_init(void);
void state_machine_update(void);
app_state_t state_machine_get_state(void);
uint32_t state_machine_get_frame_count(void);

#endif /* STATE_MACHINE_H */
