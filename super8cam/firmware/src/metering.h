/**
 * metering.h — Light metering subsystem
 */
#ifndef METERING_H
#define METERING_H

#include <stdint.h>

void meter_init(void);
void meter_update(void);
float meter_get_ev(void);
float meter_get_fstop(void);
uint16_t meter_get_asa(void);

#endif /* METERING_H */
