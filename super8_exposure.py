#!/usr/bin/env python3
"""Super 8 Camera Exposure & Metering Circuit Calculator

Calculates:
  1. Effective shutter speed at each frame rate for a 180-degree rotary shutter
  2. EV table: required f-stop for common Super 8 film stocks across EV 5-15
  3. Metering photodiode circuit: photocurrent range and transimpedance
     amplifier gain to map the scene illuminance range to a 0-3.3V ADC input

Consistent with the drivetrain parameters in super8_drivetrain.py.
"""

import math


# ---------------------------------------------------------------------------
# Camera parameters
# ---------------------------------------------------------------------------
FRAME_RATES = [18, 24]
SHUTTER_ANGLE_DEG = 180

# ---------------------------------------------------------------------------
# Film stocks  (name, EI/ISO speed)
# ---------------------------------------------------------------------------
FILM_STOCKS = [
    ("Kodak Vision3 50D",  50),
    ("Kodak Vision3 200T", 200),
    ("Kodak Vision3 500T", 500),
    ("Kodak Tri-X Rev.",   200),
]

# ---------------------------------------------------------------------------
# Lighting conditions (label, EV at ISO 100)
# ---------------------------------------------------------------------------
EV_RANGE = list(range(15, 4, -1))  # EV 15 down to EV 5

EV_LABELS = {
    15: "Bright sun, snow/sand",
    14: "Bright sun, distinct shadows",
    13: "Slight overcast",
    12: "Overcast / open shade",
    11: "Heavy overcast",
    10: "Sunset / shade",
    9:  "Bright interior",
    8:  "Normal interior",
    7:  "Dim interior",
    6:  "Dim interior / dusk",
    5:  "Very dim / candlelight",
}

# Standard f-stop scale (1/3-stop increments for display)
FSTOP_SCALE = [
    1.0, 1.1, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.5, 2.8,
    3.2, 3.5, 4.0, 4.5, 5.0, 5.6, 6.3, 7.1, 8.0, 9.0,
    10, 11, 13, 14, 16, 18, 20, 22, 25, 29, 32,
]

# ---------------------------------------------------------------------------
# Metering photodiode: Osram BPW34
# ---------------------------------------------------------------------------
PHOTODIODE_RESPONSIVITY = 0.55   # A/W at 850nm peak
# For visible-light metering the effective responsivity is lower.
# BPW34 at ~550nm (photopic peak) is roughly 0.3 A/W.
PHOTODIODE_VIS_RESPONSIVITY = 0.30  # A/W effective for visible light

# Approximate scene irradiance at the photodiode (through a small aperture
# / cosine corrector) for EV 5 to EV 15.
# Illuminance in lux for each EV (at ISO 100):
#   Lux ~= 2.5 * 2^EV  (incident light meter approximation)
# The photodiode sees irradiance through a small acceptance window.
# With a typical metering lens (f/2 acceptance, ~5mm^2 active area),
# the optical power on the sensor is:
#   P = E_v * K_factor * A_sensor
# where K_factor converts lux to W/m^2 for photopic light (~1/683).
SENSOR_AREA_M2 = 7.5e-6          # 7.5 mm^2 BPW34 active area
LUMINOUS_EFFICACY = 683.0         # lm/W (photopic peak definition)
# Metering lens/window transmission factor
OPTICS_TRANSMISSION = 0.25        # accounts for small aperture, filter, etc.

# ADC parameters (STM32L0)
ADC_VREF = 3.3                    # V
ADC_BITS = 12
ADC_COUNTS = 2**ADC_BITS          # 4096


# ---------------------------------------------------------------------------
# Exposure calculations
# ---------------------------------------------------------------------------

def shutter_speed(fps, shutter_angle):
    """Effective shutter speed as a fraction of a second.

    T_shutter = (shutter_angle / 360) / fps
    """
    return (shutter_angle / 360.0) / fps


def ev_for_iso(ev100, iso):
    """Convert EV at ISO 100 to EV at a different ISO.

    EV_s = EV_100 + log2(ISO / 100)
    """
    return ev100 + math.log2(iso / 100.0)


def fstop_from_ev_and_tv(ev_s, t_shutter):
    """Compute the f-number from exposure value and shutter time.

    EV_s = log2(N^2 / t)  =>  N = sqrt(2^EV_s * t)
    """
    n_squared = (2**ev_s) * t_shutter
    if n_squared <= 0:
        return 0.0
    return math.sqrt(n_squared)


def nearest_fstop_str(n):
    """Return the nearest standard f-stop as a display string."""
    if n < FSTOP_SCALE[0]:
        return f"<f/{FSTOP_SCALE[0]}"
    if n > FSTOP_SCALE[-1]:
        return f">f/{FSTOP_SCALE[-1]}"
    closest = min(FSTOP_SCALE, key=lambda f: abs(f - n))
    if closest == int(closest):
        return f"f/{int(closest)}"
    return f"f/{closest}"


# ---------------------------------------------------------------------------
# Metering circuit calculations
# ---------------------------------------------------------------------------

def lux_from_ev(ev100):
    """Approximate scene illuminance in lux from EV at ISO 100.

    Standard incident-light relationship: E_v = 2.5 * 2^EV
    """
    return 2.5 * (2**ev100)


def photocurrent_A(lux):
    """Photocurrent from BPW34 given scene illuminance in lux.

    Optical power on sensor:
        P = (lux / luminous_efficacy) * sensor_area * optics_transmission

    Photocurrent:
        I = P * responsivity
    """
    irradiance_w_m2 = lux / LUMINOUS_EFFICACY  # W/m^2
    power_w = irradiance_w_m2 * SENSOR_AREA_M2 * OPTICS_TRANSMISSION
    return power_w * PHOTODIODE_VIS_RESPONSIVITY


# ---------------------------------------------------------------------------
# Console output
# ---------------------------------------------------------------------------

def print_shutter_speeds():
    sep = "=" * 72
    print(sep)
    print("  SUPER 8 EXPOSURE & METERING CALCULATOR")
    print(sep)
    print()
    print(f"  Rotary shutter opening: {SHUTTER_ANGLE_DEG} deg")
    print()
    print("  Effective shutter speeds:")
    print("  " + "-" * 40)
    for fps in FRAME_RATES:
        t = shutter_speed(fps, SHUTTER_ANGLE_DEG)
        recip = 1.0 / t
        print(f"    {fps:>2} fps:  1/{recip:.0f} s  ({t*1000:.2f} ms)")
    print()


def print_ev_table():
    print("  EV EXPOSURE TABLE  (required f-stop)")
    print("  Shutter speeds: 18 fps = 1/36 s, 24 fps = 1/48 s")
    print()

    for fps in FRAME_RATES:
        t = shutter_speed(fps, SHUTTER_ANGLE_DEG)

        # Header row with film stock names
        hdr_stocks = "".join(f"  {name[:18]:>18}" for name, _ in FILM_STOCKS)
        print(f"  @ {fps} fps (1/{1/t:.0f} s):")
        print(f"    {'EV':>3}  {'Scene':^24}{hdr_stocks}")
        print("    " + "-" * (3 + 2 + 24 + 20 * len(FILM_STOCKS)))

        for ev100 in EV_RANGE:
            label = EV_LABELS.get(ev100, "")
            cols = []
            for _, iso in FILM_STOCKS:
                ev_s = ev_for_iso(ev100, iso)
                n = fstop_from_ev_and_tv(ev_s, t)
                cols.append(f"  {nearest_fstop_str(n):>18}")

            print(f"    {ev100:>3}  {label:<24}{''.join(cols)}")

        print()


def print_metering_circuit():
    print("  METERING PHOTODIODE CIRCUIT ANALYSIS")
    print("  " + "-" * 50)
    print(f"    Sensor:           BPW34 Si photodiode")
    print(f"    Active area:      {SENSOR_AREA_M2*1e6:.1f} mm^2")
    print(f"    Vis responsivity: {PHOTODIODE_VIS_RESPONSIVITY} A/W")
    print(f"    Optics factor:    {OPTICS_TRANSMISSION}")
    print(f"    ADC:              {ADC_BITS}-bit, {ADC_VREF} V ref")
    print()

    # Compute photocurrent at extremes
    ev_min, ev_max = min(EV_RANGE), max(EV_RANGE)
    lux_min = lux_from_ev(ev_min)
    lux_max = lux_from_ev(ev_max)
    i_min = photocurrent_A(lux_min)
    i_max = photocurrent_A(lux_max)

    print(f"    {'EV':>3}  {'Lux':>10}  {'Photocurrent':>14}  {'TIA Vout':>10}")
    print("    " + "-" * 45)

    # We need a transimpedance gain (R_f) that maps i_max -> ~ADC_VREF
    # and i_min -> a readable voltage (at least a few mV).
    # V_out = I_photo * R_f
    # R_f = V_target / I_max, targeting ~90% of ADC range at EV 15
    v_target = ADC_VREF * 0.90
    r_f = v_target / i_max

    for ev100 in EV_RANGE:
        lux = lux_from_ev(ev100)
        i_photo = photocurrent_A(lux)
        v_out = i_photo * r_f
        if i_photo >= 1e-6:
            i_str = f"{i_photo*1e6:.2f} uA"
        else:
            i_str = f"{i_photo*1e9:.1f} nA"
        print(f"    {ev100:>3}  {lux:>10.0f}  {i_str:>14}  {v_out*1000:>8.1f} mV")

    print()
    print(f"    Transimpedance gain (R_f): {r_f/1e6:.2f} MOhm")
    print(f"    Photocurrent range:        "
          f"{i_min*1e9:.1f} nA  (EV {ev_min})  to  "
          f"{i_max*1e6:.2f} uA  (EV {ev_max})")
    print(f"    Output voltage range:      "
          f"{i_min*r_f*1000:.1f} mV  to  {i_max*r_f*1000:.0f} mV")

    # ADC resolution check
    v_lsb = ADC_VREF / ADC_COUNTS
    counts_min = i_min * r_f / v_lsb
    counts_max = i_max * r_f / v_lsb
    print(f"    ADC counts at EV {ev_min}:       "
          f"{counts_min:.0f}  ({counts_min/ADC_COUNTS*100:.1f}% of range)")
    print(f"    ADC counts at EV {ev_max}:      "
          f"{counts_max:.0f}  ({counts_max/ADC_COUNTS*100:.1f}% of range)")

    # Minimum resolvable EV step
    # 1 EV = 2x light = 2x photocurrent.  At low end, how many counts per EV?
    counts_per_ev_at_min = counts_min  # next EV up would be 2x = 2*counts_min
    print(f"    Counts per EV step at EV {ev_min}:  ~{counts_per_ev_at_min:.0f}")

    if counts_min < 10:
        print()
        print(f"    *** WARNING: Only {counts_min:.0f} ADC counts at EV {ev_min}.")
        print(f"        Consider a logarithmic TIA or auto-ranging gain for")
        print(f"        better low-light resolution. ***")

    print()


def main():
    print_shutter_speeds()
    print_ev_table()
    print_metering_circuit()
    sep = "=" * 72
    print(sep)


if __name__ == "__main__":
    main()
