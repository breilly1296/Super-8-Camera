"""Generate engineering drawings with GD&T callouts for all machined parts."""

from super8cam.specs.master_specs import (
    FILM, CAMERA, TOL, FASTENERS, FASTENER_USAGE, MATERIALS, MATERIAL_USAGE,
)


def generate_gate_drawing():
    """Generate film gate drawing specification."""
    return {
        "part": "Film Gate",
        "material": MATERIALS[MATERIAL_USAGE["film_gate"]].designation,
        "dims": {
            "plate_w": (CAMERA.gate_plate_w, TOL.cnc_general),
            "plate_h": (CAMERA.gate_plate_h, TOL.cnc_general),
            "plate_thick": (CAMERA.gate_plate_thick, TOL.cnc_fine),
            "aperture_w": (FILM.frame_w, TOL.gate_aperture),
            "aperture_h": (FILM.frame_h, TOL.gate_aperture),
            "channel_depth": (CAMERA.gate_channel_depth, TOL.gate_channel_depth),
            "channel_w": (CAMERA.gate_channel_w, TOL.cnc_general),
            "reg_pin_hole": (CAMERA.reg_pin_dia, 0.005),
            "reg_pin_pos": (FILM.reg_pin_below_frame_center, TOL.reg_pin_position),
        },
        "surface_finish_ra_um": TOL.gate_surface_ra,
        "fasteners": FASTENER_USAGE["film_gate_mount"],
    }


def generate_all():
    """Generate all drawing specs."""
    return {
        "film_gate": generate_gate_drawing(),
    }


if __name__ == "__main__":
    import json
    specs = generate_all()
    print(json.dumps(specs, indent=2, default=str))
