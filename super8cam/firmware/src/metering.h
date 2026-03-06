/**
 * metering.h — Light Metering Subsystem
 *
 * Signal chain:
 *   BPW34 photodiode → transimpedance amplifier → ADC_IN7 (100 Hz)
 *     → 16-sample rolling average → millivolts
 *     → calibration LUT interpolation → EV (at ISO 100)
 *     → f-stop calculation for selected ASA + shutter speed
 *     → PWM to galvanometer needle + over/under LEDs
 *
 * Hardware:
 *   PA7  — ADC_IN7   photodiode / TIA output
 *   PA4  — TIM22 CH1 galvanometer PWM
 *   PA5  — green LED  (exposure achievable)
 *   PA6  — red LED    (underexposed)
 *   PB0  — DIP bit 0  (ASA select)
 *   PB1  — DIP bit 1  (ASA select)
 *   PA1  — FPS select (shared with motor)
 */

#ifndef METERING_H
#define METERING_H

#include <stdint.h>

/** One-time init: ADC calibration, TIM22 PWM, GPIO for LEDs + DIP. */
void meter_init(void);

/**
 * Call from superloop every tick.  Internally rate-limits ADC sampling
 * to METER_SAMPLE_HZ (100 Hz = every 10 ms).
 */
void meter_update(void);

/** Most recent filtered ADC voltage in millivolts. */
uint32_t meter_get_mv(void);

/** Computed exposure value (adjusted for ASA). */
float meter_get_ev(void);

/** Required f-stop for correct exposure. */
float meter_get_fstop(void);

/** Currently selected ASA from DIP switch. */
uint16_t meter_get_asa(void);

/** Current FPS read from the FPS select switch. */
uint8_t meter_get_fps(void);

#endif /* METERING_H */
