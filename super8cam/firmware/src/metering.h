/**
 * metering.h — Light metering and battery monitoring subsystem.
 *
 * Signal chain: photodiode ADC -> EV (calibration LUT) -> f-stop ->
 *               galvanometer PWM + exposure status LEDs.
 * Also reads battery voltage via ADC with 2:1 divider.
 */
#ifndef METERING_H
#define METERING_H

#include <stdint.h>

void     meter_init(void);
void     meter_update(void);
float    meter_get_ev(void);
float    meter_get_fstop(void);
uint16_t meter_get_asa(void);
uint16_t meter_get_battery_mv(void);
uint8_t  meter_is_low_battery(void);
uint8_t  meter_is_shutdown_battery(void);

#endif /* METERING_H */
