/**
 * encoder.h — Optical Encoder Interface (TIM21 Input Capture)
 *
 * One-slot-per-revolution disc on the main shaft.  Each capture interrupt
 * measures the period between rising edges, giving one pulse per frame.
 *
 * Features:
 *   - 1 µs resolution (16 MHz / 16 prescaler)
 *   - 4-sample moving average for jitter rejection
 *   - Frame counter (incremented in ISR)
 *   - Stall detection via timeout
 *
 * Hardware: PB4 / TIM21_CH1 (AF6)
 */

#ifndef ENCODER_H
#define ENCODER_H

#include <stdint.h>

/** One-time hardware init: TIM21 input capture, GPIO, NVIC. */
void encoder_init(void);

/** Averaged pulse period in microseconds (0 if no data yet). */
uint32_t encoder_get_period_us(void);

/** Instantaneous period from last capture (unfiltered). */
uint32_t encoder_get_raw_period_us(void);

/** Computed FPS from averaged period (0.0 if stalled or no data). */
float encoder_get_fps(void);

/** Total frames counted since last reset. */
uint32_t encoder_get_frame_count(void);

/** Reset the frame counter to zero. */
void encoder_reset_frame_count(void);

/** Non-zero if a new capture arrived since last clear. */
uint8_t encoder_has_new_data(void);

/** Clear the new-data flag (call after consuming the data). */
void encoder_clear_new_data(void);

/** Millisecond timestamp of the most recent encoder pulse. */
uint32_t encoder_get_last_pulse_ms(void);

/**
 * Non-zero if no encoder pulse received within timeout_ms.
 * Caller passes the current tick and desired timeout.
 */
uint8_t encoder_is_stalled(uint32_t now_ms, uint32_t timeout_ms);

#endif /* ENCODER_H */
