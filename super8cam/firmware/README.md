# Super 8 Camera Firmware

STM32L031K6 bare-register firmware for the Super 8 camera control board.

## Architecture

- `config.h` / `pinmap.h` — all constants and pin assignments (single source)
- `motor_control` — PID closed-loop DC motor speed control via TIM2 PWM
- `encoder` — optical encoder input capture via TIM21
- `metering` — photodiode ADC → EV → f-stop → galvanometer PWM + LEDs
- `state_machine` — top-level IDLE→RUNNING→STOPPING→CARTRIDGE_EMPTY→IDLE

## Build

```bash
pio run                # build
pio run -t upload      # flash via ST-Link
```

## Pin Map

See `pinmap.h` for the complete pin assignment table.
