#!/usr/bin/env python3
"""transport_sim.py — Super 8 Film Transport Mechanism Simulation

Simulates one (or more) complete revolutions of the main shaft,
modelling the four phases of the claw/shutter mechanism:

  Phase 1 (  0° – 180°):  Shutter OPEN, claw retracted, film stationary.
  Phase 2 (180° – 230°):  Shutter CLOSED, claw engages perforation.
  Phase 3 (230° – 330°):  Claw pulls film down 4.234 mm (pulldown stroke).
  Phase 4 (330° – 360°):  Claw retracts, film settles into registration.

Generates a matplotlib animation with three panels:
  Top-left:   Side view of film strip + claw + shutter blade
  Top-right:  Close-up of claw engagement with perforation
  Bottom:     Timing diagram (shutter, claw engage, film position vs angle)

Runs at both 18 fps and 24 fps.  Saves as .mp4 or shows interactively.

Usage:
    python transport_sim.py                # show animation at 18fps
    python transport_sim.py --fps 24       # show at 24fps
    python transport_sim.py --save         # export to .mp4 files
"""

import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")  # headless rendering for export
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.animation import FuncAnimation

# =========================================================================
# Mechanism parameters (mm and degrees)
# =========================================================================

FRAME_PITCH      = 4.234     # mm — distance between Super 8 frames
FRAME_WIDTH      = 5.79      # mm — gate aperture width
FRAME_HEIGHT     = 4.01      # mm — gate aperture height
PERF_WIDTH       = 0.91      # mm — perforation width
PERF_HEIGHT      = 1.14      # mm — perforation height
PERF_OFFSET_X    = 3.5       # mm — perf center from film left edge
FILM_WIDTH       = 8.0       # mm — Super 8 film strip width

# Phase boundaries (degrees of main shaft rotation)
PHASE1_END       = 180.0     # shutter open ends
PHASE2_END       = 230.0     # claw engagement ends
PHASE3_END       = 330.0     # pulldown stroke ends
PHASE4_END       = 360.0     # claw retraction ends

# Claw geometry
CLAW_WIDTH       = 0.6       # mm
CLAW_LENGTH      = 2.0       # mm
CLAW_TIP_LEN     = 1.0       # mm — portion that enters perforation
CLAW_RETRACT_X   = 2.5       # mm — distance claw retracts from film

# Number of visible frames on the film strip
VISIBLE_FRAMES   = 7

# Animation
ANIM_STEPS_PER_REV = 120     # frames of animation per shaft revolution
NUM_REVOLUTIONS    = 3        # number of shaft revolutions to animate


# =========================================================================
# Mechanism state calculator
# =========================================================================

def mechanism_state(angle_deg):
    """Return mechanism state for a given shaft angle (0-360).

    Returns dict:
        shutter_open:  bool
        claw_engaged:  bool
        claw_x_offset: float (mm, 0 = fully engaged, CLAW_RETRACT_X = retracted)
        film_dy:       float (mm, cumulative pulldown within this revolution)
    """
    angle = angle_deg % 360.0

    if angle < PHASE1_END:
        # Phase 1: shutter open, claw retracted
        return {
            "shutter_open": True,
            "claw_engaged": False,
            "claw_x_offset": CLAW_RETRACT_X,
            "film_dy": 0.0,
            "phase": 1,
        }

    elif angle < PHASE2_END:
        # Phase 2: shutter closed, claw engaging
        t = (angle - PHASE1_END) / (PHASE2_END - PHASE1_END)
        # Smooth engagement (ease-in)
        t_smooth = t * t  # quadratic ease-in
        return {
            "shutter_open": False,
            "claw_engaged": t > 0.7,  # snaps in at ~70% of phase
            "claw_x_offset": CLAW_RETRACT_X * (1.0 - t_smooth),
            "film_dy": 0.0,
            "phase": 2,
        }

    elif angle < PHASE3_END:
        # Phase 3: claw pulls film down
        t = (angle - PHASE2_END) / (PHASE3_END - PHASE2_END)
        # Sinusoidal pulldown profile (smooth start and stop)
        dy = FRAME_PITCH * 0.5 * (1.0 - np.cos(np.pi * t))
        return {
            "shutter_open": False,
            "claw_engaged": True,
            "claw_x_offset": 0.0,
            "film_dy": dy,
            "phase": 3,
        }

    else:
        # Phase 4: claw retracts, film settles
        t = (angle - PHASE3_END) / (PHASE4_END - PHASE3_END)
        t_smooth = t * t
        return {
            "shutter_open": False,
            "claw_engaged": False,
            "claw_x_offset": CLAW_RETRACT_X * t_smooth,
            "film_dy": FRAME_PITCH,  # film has moved a full frame
            "phase": 4,
        }


# =========================================================================
# Drawing helpers
# =========================================================================

def draw_film_strip(ax, y_offset, highlight_frame=None):
    """Draw a vertical film strip with perforations."""
    # Film base
    film_left = -FILM_WIDTH / 2
    film_top = y_offset + VISIBLE_FRAMES * FRAME_PITCH / 2
    film_bottom = y_offset - VISIBLE_FRAMES * FRAME_PITCH / 2
    film_height = film_top - film_bottom

    ax.add_patch(patches.Rectangle(
        (film_left, film_bottom), FILM_WIDTH, film_height,
        facecolor="#8B7355", edgecolor="#5C4033", linewidth=1.2, zorder=1))

    # Frame areas and perforations
    for i in range(VISIBLE_FRAMES):
        fy = y_offset + (i - VISIBLE_FRAMES // 2) * FRAME_PITCH
        # Frame area (exposed region)
        color = "#FFD700" if (highlight_frame is not None and i == highlight_frame) else "#A0522D"
        ax.add_patch(patches.Rectangle(
            (-FRAME_WIDTH / 2, fy - FRAME_HEIGHT / 2), FRAME_WIDTH, FRAME_HEIGHT,
            facecolor=color, edgecolor="#5C4033", linewidth=0.5, zorder=2))

        # Perforation (on the left side of film)
        perf_x = film_left + PERF_OFFSET_X - PERF_WIDTH / 2
        ax.add_patch(patches.Rectangle(
            (perf_x, fy - PERF_HEIGHT / 2), PERF_WIDTH, PERF_HEIGHT,
            facecolor="white", edgecolor="#5C4033", linewidth=0.5, zorder=2))

    return film_left


def draw_claw(ax, x_pos, y_pos, engaged):
    """Draw the claw mechanism."""
    color = "#CC0000" if engaged else "#888888"
    # Arm
    ax.add_patch(patches.Rectangle(
        (x_pos, y_pos - CLAW_WIDTH / 2), CLAW_LENGTH, CLAW_WIDTH,
        facecolor=color, edgecolor="black", linewidth=1, zorder=5))
    # Tip (the part entering the perforation)
    tip_x = x_pos + CLAW_LENGTH
    ax.add_patch(patches.FancyBboxPatch(
        (tip_x, y_pos - CLAW_WIDTH / 2), CLAW_TIP_LEN, CLAW_WIDTH,
        boxstyle="round,pad=0.1",
        facecolor=color, edgecolor="black", linewidth=1, zorder=5))


def draw_shutter(ax, is_open, gate_center_y):
    """Draw shutter state indicator."""
    if is_open:
        # Open: just the gate outline
        ax.add_patch(patches.Rectangle(
            (-FRAME_WIDTH / 2 - 0.3, gate_center_y - FRAME_HEIGHT / 2 - 0.3),
            FRAME_WIDTH + 0.6, FRAME_HEIGHT + 0.6,
            facecolor="none", edgecolor="#00AA00", linewidth=2, linestyle="--", zorder=6))
    else:
        # Closed: dark overlay on aperture
        ax.add_patch(patches.Rectangle(
            (-FRAME_WIDTH / 2, gate_center_y - FRAME_HEIGHT / 2),
            FRAME_WIDTH, FRAME_HEIGHT,
            facecolor="#333333", edgecolor="black", linewidth=1.5, alpha=0.85, zorder=6))


def draw_gate(ax, gate_y):
    """Draw the film gate (fixed aperture frame)."""
    # Gate plate (two horizontal bars above and below the aperture)
    gate_w = FILM_WIDTH + 4
    bar_h = 1.5
    # Top bar
    ax.add_patch(patches.Rectangle(
        (-gate_w / 2, gate_y + FRAME_HEIGHT / 2),
        gate_w, bar_h,
        facecolor="#444444", edgecolor="black", linewidth=1, zorder=4))
    # Bottom bar
    ax.add_patch(patches.Rectangle(
        (-gate_w / 2, gate_y - FRAME_HEIGHT / 2 - bar_h),
        gate_w, bar_h,
        facecolor="#444444", edgecolor="black", linewidth=1, zorder=4))


# =========================================================================
# Animation
# =========================================================================

def create_animation(target_fps, save=False):
    """Build and run/save the transport mechanism animation."""

    total_frames = ANIM_STEPS_PER_REV * NUM_REVOLUTIONS
    angles = np.linspace(0, 360 * NUM_REVOLUTIONS, total_frames, endpoint=False)

    # Precompute all states
    states = [mechanism_state(a) for a in angles]

    # Cumulative film position (each revolution adds FRAME_PITCH)
    film_positions = []
    completed_revs = 0
    for i, a in enumerate(angles):
        rev = int(a / 360)
        if rev > completed_revs:
            completed_revs = rev
        base_offset = rev * FRAME_PITCH
        film_positions.append(base_offset + states[i]["film_dy"])

    # ---- Figure layout ----
    fig = plt.figure(figsize=(14, 9))
    fig.patch.set_facecolor("#1a1a2e")

    # Side view (film + claw + shutter)
    ax_side = fig.add_axes([0.05, 0.35, 0.40, 0.60])
    # Claw close-up
    ax_claw = fig.add_axes([0.50, 0.35, 0.45, 0.60])
    # Timing diagram
    ax_timing = fig.add_axes([0.08, 0.06, 0.85, 0.25])

    title = fig.suptitle(
        "Super 8 Film Transport — {} fps".format(target_fps),
        fontsize=16, color="white", fontweight="bold")

    # ---- Timing diagram (static background) ----
    timing_angles = np.linspace(0, 360, 1000)
    shutter_signal = [1.0 if mechanism_state(a)["shutter_open"] else 0.0 for a in timing_angles]
    claw_signal = [1.0 if mechanism_state(a)["claw_engaged"] else 0.0 for a in timing_angles]
    film_signal = [mechanism_state(a)["film_dy"] / FRAME_PITCH for a in timing_angles]

    ax_timing.set_facecolor("#0f0f23")
    ax_timing.fill_between(timing_angles, 2.4, [2.4 + 0.5 * s for s in shutter_signal],
                           color="#00CC00", alpha=0.6, label="Shutter open")
    ax_timing.fill_between(timing_angles, 1.2, [1.2 + 0.5 * c for c in claw_signal],
                           color="#CC0000", alpha=0.6, label="Claw engaged")
    ax_timing.plot(timing_angles, film_signal, color="#4488FF", linewidth=2, label="Film position")

    ax_timing.set_xlim(0, 360)
    ax_timing.set_ylim(-0.2, 3.2)
    ax_timing.set_xlabel("Shaft angle (degrees)", color="white")
    ax_timing.set_yticks([0.5, 1.45, 2.65])
    ax_timing.set_yticklabels(["Film pos", "Claw", "Shutter"], color="white", fontsize=9)
    ax_timing.tick_params(colors="white")
    for spine in ax_timing.spines.values():
        spine.set_color("#444444")

    # Phase boundary lines
    for boundary in [PHASE1_END, PHASE2_END, PHASE3_END]:
        ax_timing.axvline(boundary, color="#666666", linewidth=0.8, linestyle="--")

    # Phase labels
    phase_centers = [90, 205, 280, 345]
    phase_names = ["P1: Expose", "P2: Engage", "P3: Pulldown", "P4: Retract"]
    for pc, pn in zip(phase_centers, phase_names):
        ax_timing.text(pc, 3.05, pn, ha="center", fontsize=7, color="#AAAAAA")

    ax_timing.legend(loc="upper right", fontsize=8, facecolor="#1a1a2e",
                     edgecolor="#444444", labelcolor="white")

    # Timing marker line (animated)
    timing_marker, = ax_timing.plot([0, 0], [-0.2, 3.2], color="yellow",
                                     linewidth=1.5, linestyle="-", alpha=0.8)

    # ---- Animation function ----

    def animate(frame_idx):
        st = states[frame_idx]
        angle = angles[frame_idx] % 360
        film_y = film_positions[frame_idx]

        # ---- Side view ----
        ax_side.clear()
        ax_side.set_facecolor("#0f0f23")
        ax_side.set_xlim(-10, 10)
        ax_side.set_ylim(-15, 15)
        ax_side.set_aspect("equal")
        ax_side.set_title("Film Gate — Side View", color="white", fontsize=11)
        ax_side.tick_params(colors="white", labelsize=7)
        for spine in ax_side.spines.values():
            spine.set_color("#444444")

        # Film strip (moves down by film_y)
        draw_film_strip(ax_side, -film_y, highlight_frame=VISIBLE_FRAMES // 2)

        # Gate
        draw_gate(ax_side, 0)

        # Shutter
        draw_shutter(ax_side, st["shutter_open"], 0)

        # Claw
        claw_x = -FILM_WIDTH / 2 - CLAW_LENGTH - CLAW_TIP_LEN + st["claw_x_offset"]
        # Claw Y tracks the target perforation during pulldown
        claw_y = -film_y % FRAME_PITCH  # align with nearest perf
        # During phase 3, claw moves with the film
        if st["phase"] == 3:
            claw_y = -st["film_dy"]
        elif st["phase"] == 4:
            claw_y = -FRAME_PITCH

        draw_claw(ax_side, claw_x, claw_y, st["claw_engaged"])

        # Info text
        phase_text = "Phase {}: {}".format(
            st["phase"],
            {1: "EXPOSING", 2: "ENGAGING", 3: "PULLDOWN", 4: "RETRACT"}[st["phase"]])
        ax_side.text(-9, 13, "{:.0f}deg".format(angle),
                     color="yellow", fontsize=10, fontweight="bold")
        ax_side.text(-9, 11, phase_text,
                     color="white", fontsize=9)
        ax_side.text(-9, 9, "Frame #{}".format(int(angles[frame_idx] / 360) + 1),
                     color="#AAAAAA", fontsize=8)

        # ---- Claw close-up ----
        ax_claw.clear()
        ax_claw.set_facecolor("#0f0f23")
        ax_claw.set_xlim(-5, 5)
        ax_claw.set_ylim(-3, 3)
        ax_claw.set_aspect("equal")
        ax_claw.set_title("Claw Detail", color="white", fontsize=11)
        ax_claw.tick_params(colors="white", labelsize=7)
        for spine in ax_claw.spines.values():
            spine.set_color("#444444")

        # Zoomed perforation
        perf_color = "#FFCCCC" if st["claw_engaged"] else "white"
        ax_claw.add_patch(patches.Rectangle(
            (-PERF_WIDTH / 2, -PERF_HEIGHT / 2), PERF_WIDTH, PERF_HEIGHT,
            facecolor=perf_color, edgecolor="#5C4033", linewidth=2, zorder=2))

        # Film edge around perforation
        ax_claw.add_patch(patches.Rectangle(
            (-2.5, -2.5), 5, 5,
            facecolor="#8B7355", edgecolor="#5C4033", linewidth=1, zorder=1))
        ax_claw.add_patch(patches.Rectangle(
            (-PERF_WIDTH / 2, -PERF_HEIGHT / 2), PERF_WIDTH, PERF_HEIGHT,
            facecolor=perf_color, edgecolor="#5C4033", linewidth=2, zorder=2))

        # Claw tip entering from left
        tip_x = -2.5 - CLAW_TIP_LEN + (2.5 + CLAW_TIP_LEN) * (1 - st["claw_x_offset"] / CLAW_RETRACT_X)
        claw_color = "#CC0000" if st["claw_engaged"] else "#888888"
        ax_claw.add_patch(patches.FancyBboxPatch(
            (tip_x - CLAW_TIP_LEN, -CLAW_WIDTH * 1.5 / 2), CLAW_TIP_LEN * 2, CLAW_WIDTH * 1.5,
            boxstyle="round,pad=0.1",
            facecolor=claw_color, edgecolor="black", linewidth=1.5, zorder=5))

        # Status indicators
        shutter_color = "#00FF00" if st["shutter_open"] else "#FF4444"
        shutter_text = "SHUTTER: OPEN" if st["shutter_open"] else "SHUTTER: CLOSED"
        ax_claw.text(-4.5, 2.5, shutter_text, fontsize=10, fontweight="bold",
                     color=shutter_color)

        engage_text = "CLAW: ENGAGED" if st["claw_engaged"] else "CLAW: RETRACTED"
        engage_color = "#FF6666" if st["claw_engaged"] else "#888888"
        ax_claw.text(-4.5, -2.5, engage_text, fontsize=10, fontweight="bold",
                     color=engage_color)

        # Film displacement
        ax_claw.text(1.5, -2.5, "dy={:.2f}mm".format(st["film_dy"]),
                     fontsize=9, color="#4488FF")

        # ---- Timing marker ----
        timing_marker.set_xdata([angle, angle])

        return []

    # ---- Build animation ----
    # Real-time interval: at target_fps, one revolution takes 1/fps seconds,
    # spread over ANIM_STEPS_PER_REV animation frames.
    interval_ms = (1000.0 / target_fps) / ANIM_STEPS_PER_REV * 10  # 10× slow-mo

    anim = FuncAnimation(fig, animate, frames=total_frames,
                         interval=interval_ms, blit=False, repeat=True)

    return fig, anim


def main():
    parser = argparse.ArgumentParser(description="Super 8 Transport Mechanism Simulation")
    parser.add_argument("--fps", type=int, choices=[18, 24], default=18,
                        help="Motor speed in frames per second")
    parser.add_argument("--save", action="store_true",
                        help="Save animation as .mp4 (requires ffmpeg)")
    parser.add_argument("--save-gif", action="store_true",
                        help="Save animation as .gif (requires Pillow)")
    args = parser.parse_args()

    if args.save or args.save_gif:
        fps_values = [18, 24]
    else:
        fps_values = [args.fps]

    for fps in fps_values:
        print("Generating {} fps animation...".format(fps))
        fig, anim = create_animation(fps)

        if args.save:
            outfile = "transport_{}fps.mp4".format(fps)
            anim.save(outfile, writer="ffmpeg", fps=30, dpi=120,
                      savefig_kwargs={"facecolor": fig.get_facecolor()})
            print("  Saved: {}".format(outfile))
            plt.close(fig)
        elif args.save_gif:
            outfile = "transport_{}fps.gif".format(fps)
            anim.save(outfile, writer="pillow", fps=20, dpi=100,
                      savefig_kwargs={"facecolor": fig.get_facecolor()})
            print("  Saved: {}".format(outfile))
            plt.close(fig)
        else:
            # Static frame export for headless environments
            outfile = "transport_{}fps_preview.png".format(fps)
            # Render frame at each phase midpoint
            fig2, axes = plt.subplots(2, 2, figsize=(16, 10))
            fig2.patch.set_facecolor("#1a1a2e")
            fig2.suptitle("Super 8 Film Transport — {} fps — Phase Overview".format(fps),
                          fontsize=14, color="white", fontweight="bold")

            phase_angles = [90, 205, 280, 345]
            phase_labels = [
                "Phase 1 (0-180deg): Shutter OPEN, film exposed",
                "Phase 2 (180-230deg): Claw engaging perforation",
                "Phase 3 (230-330deg): Pulldown stroke (4.234mm)",
                "Phase 4 (330-360deg): Claw retract, film settles",
            ]

            for idx, (angle, label) in enumerate(zip(phase_angles, phase_labels)):
                ax = axes[idx // 2][idx % 2]
                ax.set_facecolor("#0f0f23")
                ax.set_xlim(-10, 10)
                ax.set_ylim(-12, 12)
                ax.set_aspect("equal")
                ax.set_title(label, color="white", fontsize=9)
                ax.tick_params(colors="white", labelsize=6)
                for spine in ax.spines.values():
                    spine.set_color("#444444")

                st = mechanism_state(angle)

                draw_film_strip(ax, -st["film_dy"], highlight_frame=VISIBLE_FRAMES // 2)
                draw_gate(ax, 0)
                draw_shutter(ax, st["shutter_open"], 0)

                claw_x = -FILM_WIDTH / 2 - CLAW_LENGTH - CLAW_TIP_LEN + st["claw_x_offset"]
                claw_y = -st["film_dy"] if st["phase"] == 3 else 0
                draw_claw(ax, claw_x, claw_y, st["claw_engaged"])

            fig2.tight_layout(rect=[0, 0, 1, 0.95])
            fig2.savefig(outfile, dpi=150, facecolor=fig2.get_facecolor())
            print("  Saved preview: {}".format(outfile))
            plt.close(fig)
            plt.close(fig2)

    print("\nDone.")


if __name__ == "__main__":
    main()
