# Super 8 Camera Firmware

Bare-register CMSIS firmware for the STM32L031K6 controlling all camera
subsystems: motor drive, metering, and operator interface.

## Architecture

```
main.c
 ├── clock_init()       HSI16 at 16 MHz
 ├── systick_init()     1 ms global tick (g_tick_ms)
 ├── uart_init()        USART2 115200 baud debug output
 ├── motor_init()       TIM2 PWM + encoder (TIM21 IC)
 ├── meter_init()       ADC + TIM22 galvo PWM + LEDs
 ├── state_machine_init()
 └── superloop:
      ├── state_machine_update()
      ├── debug_print()         every 500 ms
      └── __WFI()               low-power sleep
```

### Module Dependency

```
config.h  pinmap.h          (constants, no code)
    ↓         ↓
encoder.c/.h                (TIM21 input capture, 4-sample avg)
    ↓
motor_control.c/.h          (TIM2 PWM, PID, ramp, stall)
    ↓
metering.c/.h               (ADC, EV calc, galvo, LEDs)
    ↓
state_machine.c/.h          (8-state FSM, battery, cartridge)
    ↓
main.c                      (init, superloop, UART debug)
```

### State Machine

```
POWER_ON → IDLE → STARTING → RUNNING → STOPPING → IDLE
                                │
                                ├→ STALL → IDLE
                                ├→ CARTRIDGE_EMPTY → IDLE
                                └→ LOW_BATTERY → IDLE
```

| State           | Motor   | Metering | Entry Condition                   |
|-----------------|---------|----------|-----------------------------------|
| POWER_ON        | off     | off      | Boot / reset                      |
| IDLE            | off     | preview  | Default state                     |
| STARTING        | ramp-up | active   | Trigger pressed                   |
| RUNNING         | PID     | active   | First encoder pulse               |
| STOPPING        | ramp-dn | active   | Trigger released                  |
| STALL           | killed  | active   | No encoder pulse within 200 ms    |
| CARTRIDGE_EMPTY | killed  | active   | 5 consecutive missed frames       |
| LOW_BATTERY     | killed  | active   | Vbat < 4200 mV                   |

## Pin Map

| Pin  | Mode | Function                              |
|------|------|---------------------------------------|
| PA0  | AF2  | TIM2_CH1 — Motor PWM output           |
| PA1  | IN   | FPS select switch (low=18, high=24)   |
| PA2  | IN   | Trigger button (active low)           |
| PA3  | OUT  | Fault/warning LED                     |
| PA4  | AF4  | TIM22_CH1 — Galvanometer needle PWM   |
| PA5  | OUT  | Green LED (exposure OK)               |
| PA6  | OUT  | Red LED (underexposed)                |
| PA7  | ANA  | ADC_IN7 — Photodiode / TIA            |
| PA9  | AF4  | USART2_TX — Debug UART                |
| PA10 | AF4  | USART2_RX — Debug UART                |
| PA13 | AF0  | SWDIO (reserved)                      |
| PA14 | AF0  | SWCLK (reserved)                      |
| PB0  | IN   | DIP bit 0 (ASA select)                |
| PB1  | IN   | DIP bit 1 (ASA select)                |
| PB2  | OUT  | Low-battery LED                       |
| PB4  | AF6  | TIM21_CH1 — Encoder input capture     |
| PB5  | OUT  | Cartridge-empty LED                   |
| PB6  | IN   | Film door switch (optional)           |
| PB7  | OUT  | Motor direction (optional)            |

## PID Tuning

| Parameter        | Value  | Notes                              |
|------------------|--------|------------------------------------|
| Kp               | 1.8    | Proportional gain                  |
| Ki               | 0.9    | Integral gain                      |
| Kd               | 0.05   | Derivative gain                    |
| Update interval  | 20 ms  | 50 Hz PID rate                     |
| Anti-windup      | ±400   | Integral clamp (duty units)        |
| D filter alpha   | 0.3    | Low-pass on derivative term        |
| Rate limit       | ±50    | Max duty change per PID cycle      |

## Build & Flash

### Prerequisites

- [PlatformIO CLI](https://platformio.org/install/cli) or VS Code extension
- ST-Link V2 programmer (built into Nucleo board)

### Commands

```bash
# Build for STM32L031K6 (production)
pio run -e super8_stm32l0

# Flash via ST-Link
pio run -e super8_stm32l0 -t upload

# Monitor debug UART (115200 baud)
pio device monitor -b 115200

# Build for Arduino Nano (prototype)
pio run -e super8_nano

# Flash Nano via USB
pio run -e super8_nano -t upload
```

### Debug Output Format

At 500 ms intervals on USART2 (115200, 8N1):

```
STATE    FPS_TGT  FPS_ACT  DUTY  EV    f/STOP  ASA  VBAT     FRAMES
RUNNING  24       23.8     487   12.3  f/8.0   100  5840mV   142
```

## Calibration

### Light Meter

1. Set DIP to ASA 100 (01), FPS to 24
2. Point camera at an 18% grey card under known illumination
3. Note the UART `EV` output
4. Adjust the `cal_table[]` entries in `metering.c` to match your
   reference meter readings
5. Repeat at multiple light levels (EV 4 through EV 14)

### Motor PID

1. Flash firmware, connect UART
2. Set FPS switch to 18, press trigger
3. Watch `FPS_ACT` column for oscillation:
   - Oscillating → reduce Kp
   - Sluggish response → increase Kp
   - Steady-state error → increase Ki
   - Overshoot on start → increase Kd or reduce Kp
4. Repeat at 24 fps

### Battery Threshold

The default `VBAT_LOW_THRESHOLD_MV = 4200` corresponds to 4×1.05V per
cell (alkaline end-of-life).  For NiMH cells (1.0V cutoff), lower to
4000 mV.  Edit in `config.h`.

## Hardware Notes

- **Motor driver**: N-channel MOSFET (IRLML6344) driven by PWM on PA0.
  Gate driven directly from GPIO (3.3V logic level compatible).
- **Encoder**: Slotted optical switch (e.g., GP1A57HRJ00F) with 3.3V
  pull-up on output.  One slot per revolution = one pulse per frame.
- **Photodiode**: BPW34 with 1 MΩ TIA (OPA340).  Output 0–3.3V maps
  to approximately EV 1–17.
- **Galvanometer**: Moving-coil meter driven by filtered PWM.  Add a
  10 kΩ series resistor and 10 µF cap for smoothing.
