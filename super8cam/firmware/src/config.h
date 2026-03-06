/**
 * config.h — Firmware configuration constants
 *
 * Single source of truth for all tunable parameters.
 * Derived from super8cam.specs.master_specs where applicable.
 */

#ifndef CONFIG_H
#define CONFIG_H

/* ---- Clock ---- */
#define SYS_CLOCK_HZ            16000000U   /* HSI16 */
#define SYSTICK_RELOAD          (SYS_CLOCK_HZ / 1000U - 1U)  /* 1 ms tick */

/* ---- Frame rates ---- */
#define FPS_LOW                 18U
#define FPS_HIGH                24U

/* ---- PID motor controller ---- */
#define PID_KP                  1.8f
#define PID_KI                  0.9f
#define PID_KD                  0.05f
#define PID_I_CLAMP             400.0f
#define PID_INTERVAL_MS         20U
#define PID_D_ALPHA             0.1f        /* derivative low-pass filter */
#define PID_RATE_LIMIT          5U          /* max duty change per ms */

/* ---- PWM (motor, TIM2 CH1) ---- */
#define PWM_TIM_PRESCALER       15U         /* 16 MHz / 16 = 1 MHz tick */
#define PWM_TIM_PERIOD          999U        /* 1 MHz / 1000 = 1 kHz PWM */
#define PWM_DUTY_MIN            50U
#define PWM_DUTY_MAX            999U

/* ---- Startup ramp (open-loop phase) ---- */
#define RAMP_STEP               5U
#define RAMP_INTERVAL_MS        10U
#define RAMP_OPEN_LOOP_MS       500U        /* open-loop before first encoder pulse */
#define RAMP_INITIAL_DUTY       (PWM_DUTY_MAX * 40U / 100U)

/* ---- Soft-stop / braking ---- */
#define STOP_RAMP_STEP          8U
#define STOP_RAMP_INTERVAL_MS   8U
#define BRAKE_DURATION_MS       50U         /* H-bridge both-high braking */
#define STOP_TIMEOUT_MS         2000U

/* ---- Stall detection ---- */
#define STALL_TIMEOUT_MS        200U
#define STALL_BLINK_COUNT       3U
#define STALL_BLINK_MS          200U

/* ---- Encoder (TIM1 CH1 input capture) ---- */
#define ENC_TIM_PRESCALER       15U         /* 1 us tick */
#define ENC_AVG_SIZE            4U          /* running average window */

/* ---- ADC / Metering ---- */
#define METER_ADC_CHANNEL       0U          /* PA0 = ADC_IN0 */
#define BATT_ADC_CHANNEL        1U          /* PA1 = ADC_IN1 */
#define METER_SAMPLE_HZ         100U
#define METER_FILTER_SIZE       16U
#define ADC_VREF_MV             3300U
#define ADC_RESOLUTION          4096U

/* Metering calibration LUT: ADC counts -> EV at ISO 100 (8 points) */
#define METER_CAL_LEN           8U
#define METER_CAL_ADC           { 0, 585, 1170, 1755, 2340, 2925, 3510, 4095 }
#define METER_CAL_EV            { 2.0f, 4.14f, 6.29f, 8.43f, 10.57f, 12.71f, 14.86f, 17.0f }

/* ASA film speed table */
#define ASA_TABLE               { 50, 100, 200, 500 }
#define ASA_EV_OFFSET_TABLE     { -1.0f, 0.0f, 1.0f, 2.32f } /* log2(ASA/100) */

/* f-stop to needle PWM (% of 999) */
#define FSTOP_MIN               1.4f
#define FSTOP_MAX               22.0f

/* Exposure status threshold */
#define EV_OK_THRESHOLD         0.5f        /* +/- EV for green LED */

/* ---- Galvanometer PWM (TIM2 CH2) ---- */
#define NEEDLE_PWM_PERIOD       999U

/* ---- Battery monitoring ---- */
#define VBAT_DIVIDER_RATIO      2U          /* 2:1 voltage divider */
#define VBAT_WARNING_MV         4200U
#define VBAT_SHUTDOWN_MV        3600U

/* ---- Cartridge end detection ---- */
#define CART_EMPTY_FRAME_LIMIT  5U
#define CART_FRAME_TIMEOUT_MS   250U

/* ---- UART debug ---- */
#define UART_BAUD               115200U
#define UART_DEBUG_INTERVAL_MS  500U

/* ---- Self-test ---- */
#define SELFTEST_TIMEOUT_MS     500U

#endif /* CONFIG_H */
