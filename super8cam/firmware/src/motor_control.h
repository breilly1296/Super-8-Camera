/**
 * motor_control.h — PID motor speed controller
 * See config.h and pinmap.h for all parameters.
 */
#ifndef MOTOR_CONTROL_H
#define MOTOR_CONTROL_H

#include <stdint.h>

void motor_init(void);
void motor_update(void);
float motor_get_fps(void);
uint8_t motor_is_stalled(void);
void motor_clear_fault(void);

#endif /* MOTOR_CONTROL_H */
