"""Generate production build checklist — wraps the root-level build_checklist.py."""

from super8cam.specs.master_specs import FILM, CAMERA, TOL, FASTENERS


def get_inspection_criteria():
    """Return inspection criteria derived from master specs."""
    return {
        "gate_aperture_w": f"{FILM.frame_w} +/- {TOL.gate_aperture} mm",
        "gate_aperture_h": f"{FILM.frame_h} +/- {TOL.gate_aperture} mm",
        "reg_pin_dia": (f"{CAMERA.reg_pin_dia} "
                        f"+{TOL.reg_pin_dia_plus}/-{TOL.reg_pin_dia_minus} mm"),
        "gate_channel_depth": f"{CAMERA.gate_channel_depth} +/- {TOL.gate_channel_depth} mm",
        "shutter_od": f"{CAMERA.shutter_od} +/- 0.1 mm",
        "shaft_dia": f"{CAMERA.shaft_dia} mm {TOL.bearing_shaft} fit",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(get_inspection_criteria(), indent=2))
