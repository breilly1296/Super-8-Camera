# Super 8 Camera

A fully parametric, open-source Super 8 motion picture camera designed from scratch in CadQuery. Every dimension traces back to a single spec file. Every part is manufacturable. The goal: a camera you can actually build, load with Kodak Super 8 film, and shoot with.

## Design Philosophy

**Specs-driven.** All 838 lines of `master_specs.py` define every dimension, tolerance, material property, and derived constant. No magic numbers anywhere else in the codebase. Change a wall thickness or gear ratio in one place and the entire camera — parts, assemblies, analysis, BOM — regenerates to match.

**Manufacturable.** Parts are designed for real processes: 3-axis CNC aluminum, wire EDM for the claw, CNC brass for the film gate, injection-moldable Delrin gears. GD&T callouts follow ASME Y14.5. Tolerance stack-ups are computed, not assumed.

**Validated.** The build pipeline doesn't just export STEP files — it runs timing validation, interference detection, thermal analysis, and kinematic simulation. Problems surface at build time, not on the machine shop floor.

## Key Specifications

| Parameter | Value |
|-----------|-------|
| Film format | Kodak Super 8 (5.79 x 4.01 mm frame) |
| Lens mount | C-mount (25.4 mm, 32 TPI, 17.526 mm FFD) |
| Frame rates | 18 fps, 24 fps (switch-selectable) |
| Shutter | 180-degree rotary disc |
| Body envelope | 148 x 88 x 52 mm |
| Body material | Aluminum 6061-T6, 2.5 mm wall |
| Film gate | Brass C360 (free-machining) |
| Drivetrain | Mabuchi FF-130SH, 2-stage Delrin spur gears |
| Power | 4x AA alkaline (6.0 V nominal) |
| Weight | ~691 g with batteries |
| BOM cost | $722 (qty 1) / $345 (qty 100) |

## Rendered Assembly

To view the full camera assembly:

1. Open `export/full_camera.step` in any CAD viewer (FreeCAD, Fusion 360, eDrawings, CAD Assistant)
2. The file contains 48 solids representing all 27 machined/molded parts plus fasteners and bearings
3. Individual part files are also in `export/` as both STEP and STL

For a quick visual without CAD software, open any of the 7 engineering drawing PDFs in `export/drawings/`.

## Directory Structure

```
Super-8-Camera/
  super8cam/                    Python package (the entire parametric model)
    specs/
      master_specs.py           Single source of truth (838 lines)
    parts/                      27 CadQuery part modules
      film_gate.py              Precision brass aperture with channel and rails
      main_shaft.py             6-section stepped shaft
      shutter_disc.py           Half-disc with balance features
      claw_mechanism.py         Spring-loaded pulldown claw
      gears.py                  2-stage spur gears (Delrin)
      body_left.py              Left body shell (CNC aluminum)
      body_right.py             Right body shell
      cam_follower.py           Face cam with modified trapezoidal profile
      ...                       (19 more part modules)
    assemblies/                 8 sub-assembly modules
      full_camera.py            Master assembly + interference detection
      film_transport.py         Gate + claw + registration pin
      drivetrain.py             Motor + gears + shaft + bearings
      shutter_assembly.py       Disc + shaft + bearings
      optical_path.py           Lens mount + gate aperture + viewfinder
      film_path.py              Channel + cartridge receiver
      power_system.py           Battery holder + wiring
      electronics.py            PCB + encoder + photodiode
    analysis/                   Engineering validation
      timing_validation.py      7-rule shutter/claw timing check (360 deg)
      tolerance_stackup.py      Flange distance, registration, bearing fits
      kinematics.py             Claw profiles, motor speed, mechanism validation
      thermal.py                Motor heat, film zone temperature, expansion
    manufacturing/              Production outputs
      gdt_standards.py          ISO 286-1 tolerance bands, GD&T symbols
      generate_bom.py           48-item BOM with cost rollup (CSV + PDF)
      generate_drawings.py      7 engineering drawing PDFs
      generate_checklist.py     111-item production checklist PDF
    firmware/                   STM32L031K6 bare-metal firmware
      platformio.ini            PlatformIO build config (STM32 + Arduino Nano)
      src/
        main.c                  Superloop + HSI16 clock + SysTick
        motor_control.c/h       PID speed control via TIM2 PWM
        metering.c/h            CdS/photodiode light meter + galvanometer
        encoder.c/h             Optical encoder input capture (TIM21)
        state_machine.c/h       IDLE/RUN/RAMPDOWN/FAULT state machine
        config.h                Tuning constants (PID gains, ASA table)
        pinmap.h                Complete STM32L031K6 pin allocation
    build.py                    Master build orchestrator (7-phase pipeline)
  export/                       Generated outputs (after build)
    *.step, *.stl               27 part files + 8 assembly files
    full_camera.step            Complete camera assembly (4.4 MB)
    bom.csv, bom.pdf            Bill of materials
    production_checklist.pdf    111-item manufacturing checklist
    build_report.txt            Full build report with analysis results
    drawings/                   7 engineering drawing PDFs
  platformio.ini                Root PlatformIO config (for firmware)
  Makefile                      Build shortcuts
```

## Build Instructions

### Prerequisites

- Python 3.12 (CadQuery is not yet compatible with 3.13+)
- [Miniforge3](https://github.com/conda-forge/miniforge) (recommended for CadQuery)

### Setup

```bash
# Create conda environment with CadQuery and dependencies
conda create -n super8 python=3.12 cadquery numpy scipy matplotlib reportlab -c conda-forge -y
conda activate super8

# Install the package
cd Super-8-Camera
pip install -e .
```

### Run the Build

```bash
python -m super8cam.build
```

This executes the 7-phase pipeline:

1. **Specifications** — Prints master specs from `master_specs.py`
2. **Validation** — Timing rules, tolerance stack-ups, bearing fits
3. **Analysis** — Kinematics, motor speed check, thermal
4. **Parts Export** — Builds and exports all 27 parts (STEP + STL)
5. **Assemblies Export** — Builds and exports 8 assemblies (STEP)
6. **Interference Detection** — Boolean intersection check on 14 critical pairs
7. **Manufacturing Outputs** — BOM, drawings, checklist, build report

Build takes ~90 seconds. All output goes to `export/`.

On Windows, set `PYTHONIOENCODING=utf-8` before running (GD&T Unicode symbols require it).

## Using the STEP Files

The exported STEP files (AP214 format) are compatible with:

- **Fusion 360** — Import directly. Use for design review, rendering, CAM toolpath generation
- **FreeCAD** — Open with Part workbench. Full BREP geometry preserved
- **SolidWorks / Inventor** — Standard STEP import
- **Slicer software** — Use the STL files for 3D printing fit-check prototypes
- **CAM software** — STEP files contain exact BREP geometry for CNC toolpath generation

The `full_camera.step` assembly contains all parts positioned at their correct datum locations. Individual part STEP files can be sent directly to a machine shop.

## Firmware

The camera firmware targets the **STM32L031K6** (ARM Cortex-M0+, 32 KB flash, 8 KB RAM) using bare-metal CMSIS — no HAL, no RTOS. An Arduino Nano prototype target is also provided for bench testing.

### Building Firmware

```bash
# Install PlatformIO CLI
pip install platformio

# Build for STM32 (production)
cd super8cam/firmware
pio run -e super8_stm32l0

# Build for Arduino Nano (prototype)
pio run -e super8_nano

# Flash via ST-Link
pio run -e super8_stm32l0 -t upload
```

### Firmware Architecture

- **Superloop** with 1 ms SysTick tick — no RTOS overhead
- **PID motor control** via TIM2 PWM at 20 kHz
- **Optical encoder** input capture on TIM21 for closed-loop speed regulation
- **Light metering** via ADC with EV-to-galvanometer lookup table
- **State machine**: IDLE -> RUN -> RAMPDOWN -> FAULT with watchdog

## References

- **Kodak Super 8 Film**: [Kodak Super 8 specifications](https://www.kodak.com/en/motion/page/super-8-702) — Frame size 5.79 x 4.01 mm, perforation pitch 4.234 mm
- **C-Mount Standard**: 25.4 mm diameter, 32 TPI thread, 17.526 mm flange focal distance
- **ASME Y14.5-2018**: Dimensioning and Tolerancing standard (GD&T callouts in drawings)
- **ISO 286-1**: System of limits and fits (tolerance band calculations)

## License

This project is licensed under the **CERN Open Hardware Licence Version 2 — Strongly Reciprocal (CERN-OHL-S v2)**.

You may redistribute and modify this project and its documentation under the terms of the CERN-OHL-S v2. This licence requires that derivative works are distributed under the same licence terms, ensuring the hardware remains open.

See [https://ohwr.org/cern_ohl_s_v2.txt](https://ohwr.org/cern_ohl_s_v2.txt) for the full licence text.

## Known Limitations and Future Work

**Analysis warnings (design iteration needed):**

- **Timing**: Registration pin not engaged when shutter opens (Rule 2). Cam phasing needs adjustment — shift claw engage phase earlier by ~20 degrees.
- **Interference**: 9 of 14 checked part pairs show geometric overlap. Assembly datum offsets need refinement in `full_camera.py`. Individual parts are geometrically correct.
- **Flange distance stack-up**: Nominal 10.5 mm vs. 17.526 mm target. Tolerance contributor list in `tolerance_stackup.py` needs additional spacer/mount contributors.
- **Motor speed**: FF-130SH at 15:1 ratio exceeds rated RPM. Gear ratio should be reduced to ~6:1 or motor swapped for higher-speed unit.
- **Registration accuracy**: Worst-case 0.0605 mm exceeds professional spec. Tighter pin/hole tolerances or guided claw redesign needed.

**Not yet implemented:**

- Light-seal groove geometry on body shells
- Cartridge latch/release mechanism
- Viewfinder optics (prism path)
- Film-speed DIP switch pocket on PCB bracket
- KiCad schematic and PCB layout (control board is spec'd but not routed)
- Surface finish callouts on engineering drawings (Ra values defined in specs, not yet rendered)
