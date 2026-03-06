# Super 8 Camera Firmware

Bare-register C firmware for the Super 8 camera control board.
Primary target: **STM32L031K6** (Nucleo-L031K6).
Prototype target: **Arduino Nano** (ATmega328P).

## Architecture

```
main.c
  ├── clock_init()          HSI16, no PLL
  ├── gpio_init()           Pull-ups on inputs
  ├── uart_init()           USART2 TX on PA2, 115200 baud
  ├── motor_init()          TIM2 CH1/CH2 PWM + encoder init
  ├── meter_init()          ADC calibration + LED GPIO
  ├── state_machine_init()  Enter POWER_ON state
  └── superloop
        ├── state_machine_update()
        ├── debug_output()  UART telemetry every 500 ms
        └── __WFI()         Sleep in IDLE state
```

### State Machine (8 states)

```
POWER_ON ──> IDLE ──> STARTING ──> RUNNING ──> STOPPING ──> IDLE
                          │            │
                          │            ├──> STALL ──> IDLE
                          │            └──> CARTRIDGE_EMPTY ──> IDLE
                          │
                          └──> LOW_BATTERY (from any state, no recovery)
```

### Modules

| File | Purpose |
|------|---------|
| `config.h` | All tunable constants (PID gains, PWM, ADC cal, thresholds) |
| `pinmap.h` | GPIO/ADC/timer pin assignments (single source of truth) |
| `encoder.c/.h` | TIM1 CH1 input capture, 4-sample running average, stall flag |
| `motor_control.c/.h` | PID with derivative filter, rate limiting, open-loop ramp, soft-stop + brake |
| `metering.c/.h` | ADC -> 8-point calibration LUT -> EV -> f-stop -> galvanometer PWM + LEDs, battery monitor |
| `state_machine.c/.h` | Top-level 8-state FSM integrating all subsystems |
| `main.c` | Peripheral init, superloop, UART debug telemetry |

## Pin Assignments

| Pin | Function | Peripheral |
|-----|----------|------------|
| PA0 | Metering photodiode | ADC_IN0 |
| PA1 | Battery voltage (2:1 divider) | ADC_IN1 |
| PA2 | UART TX (debug) | USART2_TX |
| PA4 | Motor PWM | TIM2_CH1 (AF2) |
| PA5 | Needle galvanometer PWM | TIM2_CH2 (AF2) |
| PA8 | Encoder input capture | TIM1_CH1 (AF2) |
| PA11 | Cartridge detect | GPIO input (pull-up) |
| PA12 | Motor enable (H-bridge) | GPIO output |
| PB0 | Trigger button | GPIO input (pull-up, active low) |
| PB1 | FPS select | GPIO input (pull-up) |
| PB3 | Film speed DIP bit 0 | GPIO input (pull-up) |
| PB4 | Film speed DIP bit 1 | GPIO input (pull-up) |
| PB5 | Motor direction (H-bridge IN2) | GPIO output |
| PB6 | Warning LED (red) | GPIO output |
| PB7 | OK LED (green) | GPIO output |

## Build & Flash

```bash
# STM32 target (production)
pio run -e super8_stm32l0              # build
pio run -e super8_stm32l0 -t upload    # flash via ST-Link

# Arduino Nano target (prototype)
pio run -e super8_nano                 # build
pio run -e super8_nano -t upload       # flash via USB
```

## UART Debug Output

At 115200 baud, every 500 ms:
```
RUNNING fps=18.1 duty=423 ev=11.2 f/5.6 asa=100 bat=5800mV frm=342
```

## Calibration Procedure

1. **Metering LUT**: Expose photodiode to known EV levels (2-17). Read raw ADC
   values. Update `METER_CAL_ADC` and `METER_CAL_EV` arrays in `config.h`.

2. **PID Tuning**: With camera loaded, adjust `PID_KP`, `PID_KI`, `PID_KD` in
   `config.h`. Monitor UART output for fps stability. Target: ±0.5 fps at
   steady state.

3. **Galvanometer**: Adjust `FSTOP_MIN`/`FSTOP_MAX` in `config.h` to match
   the needle's mechanical range. The PWM maps linearly in log2(f-stop) space.

4. **Battery Thresholds**: Measure actual battery voltage at the ADC pin with
   a multimeter. Adjust `VBAT_DIVIDER_RATIO` if the resistor divider ratio
   differs from 2:1. Set `VBAT_WARNING_MV` and `VBAT_SHUTDOWN_MV` to match
   your battery chemistry.

5. **Stall Detection**: If false stalls occur during startup, increase
   `STALL_TIMEOUT_MS` or `RAMP_OPEN_LOOP_MS` in `config.h`.
