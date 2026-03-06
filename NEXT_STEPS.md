# Next Steps: From Digital Files to Physical Camera

This document outlines the 12-step path from the current parametric CAD model to a working Super 8 camera shooting real film.

---

## Step 1: Import into Fusion 360 and Review

**Import `export/full_camera.step` into Fusion 360.**

- Check all 48 solids imported cleanly (no missing faces, degenerate geometry)
- Verify part-to-part interfaces: screw boss alignment, bearing pocket depths, shaft fits
- Run Fusion 360's native interference analysis to cross-check against our build report
- Review the 9 flagged interferences and adjust datum offsets in assembly positioning
- Section-view the film path end-to-end: cartridge receiver through gate to take-up

**Key fixes needed before prototyping:**
- Resolve shutter-vs-gate interference (64 mm^3 overlap) — likely need 0.5 mm axial offset
- Resolve cam-vs-gate interference (487 mm^3) — cam housing needs clearance pocket
- Adjust motor mount and PCB bracket positions to clear body shell interior
- Fix viewfinder-vs-top-plate overlap (27 mm^3) — lower viewfinder tube or add top plate cutout

**Deliverable:** Annotated Fusion 360 project file with all interferences resolved.

---

## Step 2: 3D Print Fit-Check Prototypes

**Print the body shells, film gate, and cartridge receiver in PLA or PETG.**

- Use the STL files in `export/` directly — they're already watertight meshes
- Print at 0.2 mm layer height for dimensional accuracy
- Key fit checks:
  - Does a real Super 8 cartridge seat and latch in the receiver?
  - Does the film channel guide the film strip without binding?
  - Does the C-mount thread adapter screw in and bottom out at correct flange distance?
  - Do the body halves mate flush with the M2.5 screw pattern aligned?
  - Is there enough finger clearance on the trigger?
- Measure critical dimensions with calipers and compare to specs

**Deliverable:** Fit-check report with photos and measurements. List of geometry corrections.

---

## Step 3: CNC the Brass Film Gate

**This is the highest-precision part. Machine it first to validate the process.**

- Material: Brass C360 (free-machining, excellent dimensional stability)
- Send `export/film_gate.step` plus `export/drawings/film_gate.pdf` to CNC shop
- Critical dimensions:
  - Aperture: 5.79 x 4.01 mm +/- 0.005 mm
  - Registration pin hole: 0.813 +0.000/-0.005 mm
  - Claw slot: 1.5 x 3.0 mm with 0.1 mm radii
  - Surface finish: Ra 0.4 um on film-contact surfaces
- Request first-article inspection report with CMM data

**Deliverable:** Inspected brass film gate with FAI report.

---

## Step 4: Machine the Claw and Registration Pin

**Wire EDM or Swiss-turn the claw mechanism from AISI 4140 steel.**

- Claw tip must match perforation geometry: 1.143 x 0.914 mm engagement
- Pulldown stroke: exactly 4.234 mm (one perf pitch)
- Registration pin: 0.813 mm diameter, ground finish
- Heat treat to Rc 45-50 for wear resistance
- These parts mate with the brass gate — verify fit together before assembly

**Deliverable:** Functional claw + pin set, verified against gate.

---

## Step 5: Machine the Cam, Shaft, and Gears

**The drivetrain defines film-advance timing.**

- Main shaft: AISI 4140, 6 sections, 4mm bearing journals (k6 tolerance for press fit)
- Pulldown cam: AISI 4140 face cam with modified trapezoidal profile — CNC 4-axis or wire EDM the cam track
- Gears: Delrin 150 (acetal). Module 0.5 and 0.8 spur gears can be CNC'd or hobbed
  - Stage 1: 10T pinion / 50T gear (5:1)
  - Stage 2: 12T pinion / 36T gear (3:1)
  - Total ratio: 15:1 (NOTE: may need reducing to ~6:1 per motor speed analysis)
- Order 694ZZ and 683ZZ bearings (standard sizes, available from any bearing supplier)

**Deliverable:** Complete drivetrain subassembly, manually rotatable to verify cam motion.

---

## Step 6: CNC the Body Shells

**Machine left and right body halves from 6061-T6 billet.**

- Wall thickness: 2.5 mm throughout
- Internal pockets for motor mount, PCB, battery holder
- M2.5 threaded bosses for shell assembly (12 screws)
- 1/4-20 Helicoil insert pocket on bottom plate (tripod mount)
- Hard anodize after machining (Type III, 0.025 mm buildup — account for in tolerances)
- Also machine: top plate, bottom plate, battery door, cartridge door

**Deliverable:** Anodized body shell set. All doors open/close. Battery compartment fits 4x AA.

---

## Step 7: Build the Control PCB

**The firmware is written but the PCB needs layout.**

- Schematic is specified in `master_specs.py` (PCB dataclass) but not yet captured in KiCad
- Key components:
  - STM32L031K6 (LQFP-32)
  - GP1A57HRJ00F optical encoder
  - IRLML6344 motor MOSFET
  - BPW34 photodiode (light meter)
  - 100 uA galvanometer meter movement
  - 2-position DIP switch (film speed)
  - FPS toggle switch
- Board outline: 40 x 25 mm, 4-layer FR4 with ENIG finish
- Flash the firmware using ST-Link V2 and PlatformIO

**Deliverable:** Assembled and flashed PCB. Motor spins, encoder reads, meter needle deflects.

---

## Step 8: Prototype Assembly

**Assemble all subsystems into the body for the first time.**

- Follow the 111-item production checklist (`export/production_checklist.pdf`)
- Assembly order:
  1. Press bearings into gearbox housing and body shell bearing pockets
  2. Install main shaft with gears into gearbox
  3. Mount motor to motor bracket, mesh pinion with stage 1 gear
  4. Install claw mechanism and registration pin in film gate
  5. Mount film gate to left body shell
  6. Install shutter disc on shaft
  7. Mount PCB and connect wiring harness
  8. Install cartridge receiver in right body shell
  9. Join body halves
  10. Install top plate, bottom plate, doors
  11. Thread C-mount lens adapter

**Deliverable:** Fully assembled prototype camera. Holds together. Mechanism turns by hand.

---

## Step 9: Bench Test the Mechanism

**Power up and validate without film.**

- Connect 4x AA batteries
- Toggle to 18 fps, press trigger — verify motor starts and stabilizes
- Measure shaft speed with optical tachometer (target: 1080 RPM at shaft = 18 fps)
- Toggle to 24 fps — verify 1440 RPM
- Check PID settling time (spec: < 200 ms to +/- 1%)
- Listen for gear noise, vibration, binding
- Verify shutter clears gate at all rotation angles (strobe test)
- Check claw engagement/retraction through gate slot
- Measure current draw (spec: ~270 mA at 24 fps)

**Deliverable:** Bench test report with speed, current, and vibration data.

---

## Step 10: Shoot the First Roll of Film

**Load a Kodak Super 8 cartridge and expose 50 feet of film.**

- Use a well-lit outdoor scene (ISO 200 Kodak Vision3 200T or 500T)
- Verify:
  - Cartridge seats and latches correctly
  - Film feeds smoothly through gate
  - Claw engages perforations without tearing
  - Registration pin stabilizes frame during exposure
  - Shutter timing gives correct exposure (meter needle at center)
  - Camera runs at constant speed for full 50 ft (about 2.5 min at 24 fps)
- Send exposed cartridge to a film lab for processing and scanning
  - Recommended: Kodak Film Lab Atlanta, Pro8mm, or Spectra Film & Video
- Review scanned footage for:
  - Frame steadiness (registration accuracy)
  - Exposure consistency
  - Edge sharpness (flange distance correctness)
  - Scratches or emulsion damage (pressure plate / gate finish issues)

**Deliverable:** Processed and scanned first roll. Frame grabs showing registration quality.

---

## Step 11: Iterate on Findings

**Fix whatever the first roll reveals.**

Common issues and likely fixes:
- **Unsteady frames**: Tighten registration pin tolerance, add pin pre-load spring
- **Exposure variation**: Tune PID gains for more stable speed, check shutter balance
- **Soft focus**: Shim lens mount to adjust flange distance (the stack-up analysis flagged this)
- **Film scratches**: Re-lap film gate surfaces to Ra 0.2 um, check pressure plate force
- **Torn perforations**: Reduce claw engagement force, verify pulldown cam profile
- **Motor stalling**: Reduce gear ratio from 15:1 to ~6:1, or switch to higher-torque motor
- **Overheating**: Add thermal break between motor mount and gate (the analysis showed 3.8 C rise — manageable, but margin is thin at 24 fps continuous)

**Deliverable:** Rev 2 parts list and updated STEP files.

---

## Step 12: Document and Share

**Prepare for community release or crowdfunding.**

- Create render images and assembly animation (Fusion 360 or Blender)
- Write detailed assembly guide with photos from Step 8
- Document the BOM with supplier links and lead times
- Create a KiCad project with schematic, PCB layout, and Gerber files
- Record a demo video with footage shot on the camera
- Publish to GitHub with CERN-OHL-S v2 license
- Consider a Crowd Supply or Kickstarter campaign if there's interest
  - Qty 25 cost: $467/camera
  - Qty 100 cost: $345/camera
  - Realistic retail price with margin: $599-799

**Deliverable:** Public repository, demo video, and (optionally) a crowdfunding campaign page.

---

## Summary Timeline (Estimated)

| Step | Duration | Depends On |
|------|----------|------------|
| 1. Fusion 360 review | 1-2 weeks | -- |
| 2. 3D print fit check | 1 week | Step 1 |
| 3. CNC brass gate | 2-3 weeks | Step 1 |
| 4. Claw + reg pin | 2-3 weeks | Step 3 |
| 5. Drivetrain | 2-3 weeks | Step 1 |
| 6. Body shells | 3-4 weeks | Step 2 |
| 7. Control PCB | 3-4 weeks | Step 1 |
| 8. Assembly | 1 week | Steps 3-7 |
| 9. Bench test | 1 week | Step 8 |
| 10. First roll | 1-2 weeks | Step 9 |
| 11. Iteration | 2-4 weeks | Step 10 |
| 12. Documentation | 2-3 weeks | Step 11 |

**Critical path: ~16-20 weeks from design freeze to first footage.**
