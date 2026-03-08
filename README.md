# Super 8 Camera

**An open-source, self-repairable Super 8 film camera.**

A fully parametric motion picture camera designed from scratch in CadQuery. Every dimension traces back to a single spec file. Every part is manufacturable. 7 field-swappable modules. 10 FDM-printable replacement parts. A complete repair manual generated from the design itself.

## Key Specifications

| Parameter | Value |
|-----------|-------|
| Film format | Kodak Super 8 (5.79 x 4.01 mm frame) |
| Lens mount | C-mount (25.4 mm, 32 TPI, 17.526 mm FFD) |
| Frame rates | 18 fps, 24 fps (switch-selectable) |
| Shutter | 180-degree rotary disc |
| Body envelope | 135 x 80 x 48 mm |
| Body material | Aluminum 6061-T6, 2.5 mm wall |
| Film gate | Brass C360 (free-machining) |
| Drivetrain | Mabuchi FF-130SH, 2-stage Delrin spur gears (6:1) |
| Power | 4x AA alkaline (6.0 V nominal) |
| Weight | ~691 g with batteries |
| BOM cost | $722 (qty 1) / $345 (qty 100) |

## Module Architecture

The camera is organized into 7 field-swappable modules. Each module can be removed and replaced independently without disassembling the rest of the camera.

| Module | Name | Interface | Swap Level | Swap Time | Printable Parts |
|--------|------|-----------|------------|-----------|-----------------|
| MOD-100 | Film Transport | Thumbscrew | Technician | 2 min | Film Channel |
| MOD-200 | Shutter | Thumbscrew | Technician | 90 s | — |
| MOD-300 | Drivetrain | Thumbscrew | Technician | 3 min | Motor Mount, Gearbox Housing, Gears |
| MOD-400 | Cartridge Bay | Snap-fit | User | 30 s | Cartridge Door |
| MOD-500 | Electronics | JST | Technician | 60 s | PCB Bracket |
| MOD-600 | Power | Snap-fit | User | 15 s | Battery Door |
| MOD-700 | Optics | Dovetail | User | 20 s | Viewfinder |

Modules interconnect via 7 JST connectors (XH 2.5 mm + VH 3.96 mm) with unique pin counts to prevent cross-connection. Each connector is keyed to exactly one module pair.

## Framework for Film

This camera borrows its philosophy from [Framework laptops](https://frame.work): **every single part is replaceable, individually purchasable, and forward-compatible across versions.**

### Every Part is Replaceable

There are no glued, riveted, or permanently bonded assemblies. Every component — from the brass film gate to the battery door hinge pin — can be removed with standard hex keys and replaced with an identical spare. The complete [spare parts catalog](super8cam/business/store_catalog.py) lists 35+ SKUs available individually, from a $3 registration pin to complete pre-assembled modules.

### Interface Specification (Frozen)

The [interface standard](super8cam/specs/interface_standard.py) defines the immutable contract between all modules and the chassis:

| Interface | Spec | Status |
|-----------|------|--------|
| Dovetail rail | 60 deg, 4mm top / 6mm base / 3mm deep | FROZEN v1.0 |
| Thumb screws | M3, 20mm center-to-center spacing | FROZEN v1.0 |
| Module slots | 7 slots with exact X/Y/Z coordinates | FROZEN v1.0 |
| Connectors | J1-J7 pinouts, families, wire colors | FROZEN v1.0 |
| Fasteners | M2 / M2.5 / M3 / 1/4"-20 only | FROZEN v1.0 |

A MOD-100 Film Transport manufactured in 2026 will drop into a MOD-100 slot on a chassis built in 2030. The interface spec version guarantees it.

### Future-Proof: Expansion Slot

The chassis includes a reserved expansion slot (MOD-EXP) with a 10-pin JST-XH connector providing:

```
SDA, SCL, TX, RX, PWM1, PWM2, 3V3, 5V, GND, GND
```

V1 ships with a blank cover plate. This enables community-designed expansion modules:
- Digital frame counter
- Bluetooth sync / remote trigger
- Intervalometer (time-lapse)
- Sound recording module
- GPS location logger
- External light meter interface

The expansion slot position, connector pinout, and dovetail mounting are part of the frozen interface standard.

### Module Map

```
  LEFT HALF (chassis)                    RIGHT HALF
  ┌──────────────────────────────┐┌──────────────────────┐
  │  MOD-700   MOD-200           ││  MOD-400             │
  │  Optics    Shutter           ││  Cartridge Bay       │
  │  ┌─────┐  ┌──────┐          ││  ┌──────────────┐    │
  │  │Lens │  │Disc  │          ││  │Receiver      │    │
  │  │Mount│  │Shaft │  MOD-300 ││  │Door          │    │
  │  └─────┘  └──────┘  Drive   ││  └──────────────┘    │
  │                     ┌─────┐ ││                       │
  │  MOD-100            │Motor│ ││  MOD-EXP              │
  │  Film Transport     │Gears│ ││  (Expansion)          │
  │  ┌──────────────┐   └─────┘ ││  ┌───────────┐       │
  │  │Gate+Claw+Cam │           ││  │ 10-pin XH │       │
  │  │Plate+Channel │  MOD-500  ││  │ blank cap │       │
  │  └──────────────┘  ┌──────┐ ││  └───────────┘       │
  │                    │PCB   │ ││                       │
  │                    │J1-J7 │ ││                       │
  │                    └──────┘ ││                       │
  ├─────────────────────────────┤├──────────────────────-┤
  │           MOD-600  Power (Battery Bay)               │
  └──────────────────────────────┘──────────────────────-┘
```

## Design Philosophy

**Specs-driven.** `master_specs.py` defines every dimension, tolerance, material property, and derived constant. Change a wall thickness or gear ratio in one place and the entire camera regenerates to match.

**Manufacturable.** Parts are designed for real processes: 3-axis CNC aluminum, wire EDM for the claw, CNC brass for the film gate, injection-moldable Delrin gears. GD&T callouts follow ASME Y14.5.

**Validated.** The build pipeline runs timing validation, interference detection, thermal analysis, and kinematic simulation. Problems surface at build time, not on the machine shop floor.

**Self-repairable.** Every part has a replacement procedure, tools list, and cost estimate. The generated repair guide PDF walks through symptom diagnosis, module swap, and reassembly verification.

## Build Instructions

### Prerequisites

- Python 3.10+ (3.12 recommended for CadQuery compatibility)
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
6. **Interference Detection** — Boolean intersection check on critical pairs
7. **Manufacturing Outputs** — BOM, drawings, checklist, wiring diagram, repair guide

All output goes to `export/`. On Windows, set `PYTHONIOENCODING=utf-8` before running.

### Other Build Modes

```bash
python -m super8cam.build --specs          # print specs summary only
python -m super8cam.build --parts-only     # export parts only
python -m super8cam.build --analysis-only  # run analysis only
python -m super8cam.build --report-only    # generate build report only
```

## Directory Structure

```
Super-8-Camera/
  super8cam/                    Python package
    specs/
      master_specs.py           Single source of truth
      modularity.py             Module architecture + connector map + part catalog
      interface_standard.py     FROZEN interface spec (dovetails, slots, pinouts)
    parts/                      23 CadQuery part modules
    assemblies/                 8 sub-assembly modules
      full_camera.py            Master assembly + interference detection
    analysis/                   Engineering validation
      timing_validation.py      Shutter/claw timing check
      tolerance_stackup.py      Flange distance, registration, bearing fits
      kinematics.py             Claw profiles, motor speed, mechanism validation
      thermal.py                Motor heat, film zone temperature
    manufacturing/              Production outputs
      generate_bom.py           BOM with cost rollup (CSV + PDF)
      generate_drawings.py      Engineering drawing PDFs
      generate_checklist.py     Production checklist PDF
      generate_wiring.py        Wiring harness diagram PDF
      repair_guide.py           Repair & maintenance guide PDF
      generate_qr.py            QR codes + compatibility labels for all parts
    business/                   Store and catalog
      store_catalog.py          Shopify-compatible spare parts catalog (35+ SKUs)
    firmware/                   STM32L031K6 bare-metal firmware
      platformio.ini            PlatformIO build config
      src/
        main.c                  Superloop + HSI16 clock + SysTick
        motor_control.c/h       PID speed control via TIM2 PWM
        metering.c/h            Light meter + galvanometer
        encoder.c/h             Optical encoder input capture
        state_machine.c/h       IDLE/RUN/RAMPDOWN/FAULT state machine
        config.h                Tuning constants
        pinmap.h                Complete pin allocation + connector cross-ref
    build.py                    Master build orchestrator
  export/                       Generated outputs (after build)
  pyproject.toml                Package metadata + dependencies
  verify_fixes.py               25-point mechanical verification suite
```

## Generated Documents

After a full build, the `export/` directory contains:

| File | Description |
|------|-------------|
| `repair_guide.pdf` | Multi-page repair manual with symptom diagnosis, procedures, and spare parts order form |
| `wiring_diagram.pdf` | Wire harness diagram with connector table and cut list |
| `bom.csv` / `bom.pdf` | Bill of materials with cost rollup at qty 1/25/100 |
| `production_checklist.pdf` | 111-item manufacturing QC checklist |
| `drawings/*.pdf` | Engineering drawings for critical parts |
| `build_report.txt` | Full build report with all analysis results |
| `*.step` / `*.stl` | Part and assembly CAD files |

## Firmware

The camera firmware targets the **STM32L031K6** (ARM Cortex-M0+, 32 KB flash, 8 KB RAM) using bare-metal CMSIS. An Arduino Nano prototype target is also provided.

```bash
cd super8cam/firmware
pip install platformio
pio run -e super8_stm32l0        # build for STM32
pio run -e super8_nano           # build for Arduino Nano
pio run -e super8_stm32l0 -t upload  # flash via ST-Link
```

See `super8cam/firmware/` for the complete firmware source.

## References

- **Kodak Super 8 Film**: Frame size 5.79 x 4.01 mm, perforation pitch 4.234 mm
- **C-Mount Standard**: 25.4 mm diameter, 32 TPI thread, 17.526 mm flange focal distance
- **ASME Y14.5-2018**: Dimensioning and Tolerancing standard
- **ISO 286-1**: System of limits and fits

## License

This project is licensed under the **CERN Open Hardware Licence Version 2 — Strongly Reciprocal (CERN-OHL-S v2)**.

You may redistribute and modify this project and its documentation under the terms of the CERN-OHL-S v2. This licence requires that derivative works are distributed under the same licence terms, ensuring the hardware remains open.

See [https://ohwr.org/cern_ohl_s_v2.txt](https://ohwr.org/cern_ohl_s_v2.txt) for the full licence text.

## Contributing

Contributions are welcome. Please:

1. Fork the repository and create a feature branch
2. Ensure `python verify_fixes.py` passes all 25 checks
3. Run `python -m super8cam.build --specs` to verify imports
4. Submit a pull request with a clear description of your changes

All mechanical dimensions must come from `master_specs.py`. No magic numbers in part files.

## Acknowledgments

- [CadQuery](https://cadquery.readthedocs.io/) — Parametric CAD scripting
- [Kodak](https://www.kodak.com/en/motion/page/super-8-702) — Super 8 film format
- [PlatformIO](https://platformio.org/) — Embedded firmware toolchain
- [ReportLab](https://www.reportlab.com/) — PDF generation
