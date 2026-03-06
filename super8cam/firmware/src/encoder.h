/**
 * encoder.h — Optical encoder interface (TIM21 input capture)
 */
#ifndef ENCODER_H
#define ENCODER_H

#include <stdint.h>

void encoder_init(void);
uint32_t encoder_get_period_us(void);
uint8_t encoder_has_new_data(void);
void encoder_clear_new_data(void);
uint32_t encoder_get_frame_count(void);

#endif /* ENCODER_H */
