/**
 * encoder.h — Optical encoder interface (TIM1 input capture)
 *
 * One slot per revolution = one pulse per frame.
 * Provides period measurement with 4-sample running average,
 * frame counting, FPS calculation, and stall detection.
 */
#ifndef ENCODER_H
#define ENCODER_H

#include <stdint.h>

void     encoder_init(void);
uint32_t encoder_get_period_us(void);
float    encoder_get_fps(void);
uint8_t  encoder_has_new_data(void);
void     encoder_clear_new_data(void);
uint32_t encoder_get_frame_count(void);
uint8_t  encoder_is_stalled(void);

#endif /* ENCODER_H */
