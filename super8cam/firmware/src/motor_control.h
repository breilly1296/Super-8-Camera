/**
 * motor_control.h — PID motor speed controller with open-loop startup,
 * derivative filtering, output rate limiting, and soft-stop braking.
 */
#ifndef MOTOR_CONTROL_H
#define MOTOR_CONTROL_H

#include <stdint.h>

void    motor_init(void);
void    motor_update(void);
void    motor_start(void);
void    motor_stop(void);
void    motor_brake(void);
void    motor_disable(void);
float   motor_get_fps(void);
uint8_t motor_is_stalled(void);
void    motor_clear_fault(void);
uint16_t motor_get_duty(void);

#endif /* MOTOR_CONTROL_H */
