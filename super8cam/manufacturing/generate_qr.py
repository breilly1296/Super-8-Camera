"""generate_qr.py — QR code generation for every part in the catalog.

Generates:
  1. Individual QR code PNGs (10mm or 6mm at 300 DPI) for laser engraving
  2. A QR code sheet PDF (A4) with all parts in a grid, labeled
  3. A master QR code for the camera repair guide
  4. Compatibility labels (40mm x 15mm PNG) for shipping

Usage:
    conda run -n super8 python -m super8cam.manufacturing.generate_qr
    conda run -n super8 python -m super8cam.manufacturing.generate_qr --output export/qr
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

try:
    import qrcode
    from qrcode.image.pil import PilImage
except ImportError:
    print("ERROR: qrcode[pil] not installed. Run: pip install qrcode[pil]")
    sys.exit(1)

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install Pillow")
    sys.exit(1)

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
except ImportError:
    print("ERROR: reportlab not installed. Run: pip install reportlab")
    sys.exit(1)

from super8cam.specs.modularity import PART_CATALOG
from super8cam.specs.interface_standard import INTERFACE_VERSION


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://super8camera.com/parts"
REPAIR_GUIDE_URL = "https://super8camera.com/repair-guide"
DPI = 300

# Parts too small for their own QR code — QR goes on the parent module
SKIP_QR_PARTS = {"S8C-106"}  # Registration pin (<10mm)

# Size thresholds: parts with any dimension > 20mm get 10mm QR, else 6mm
LARGE_QR_MM = 10.0
SMALL_QR_MM = 6.0

# Known part dimensions (largest dimension in mm) for size selection
# Derived from CadQuery bounding boxes
PART_MAX_DIM = {
    "S8C-101": 24.0,    # Film Gate
    "S8C-102": 30.0,    # Pressure Plate
    "S8C-103": 16.5,    # Claw Mechanism
    "S8C-104": 16.0,    # Cam Follower
    "S8C-105": 30.0,    # Film Channel
    "S8C-106": 3.5,     # Registration Pin — SKIP
    "S8C-201": 28.0,    # Shutter Disc
    "S8C-202": 38.0,    # Main Shaft
    "S8C-301": 28.4,    # Motor Mount
    "S8C-302": 62.2,    # Gearbox Housing
    "S8C-303": 22.4,    # Gear Set
    "S8C-401": 72.0,    # Cartridge Receiver
    "S8C-402": 59.0,    # Cartridge Door
    "S8C-501": 58.0,    # PCB Bracket
    "S8C-601": 66.0,    # Battery Door
    "S8C-602": 133.0,   # Bottom Plate
    "S8C-701": 30.0,    # Lens Mount
    "S8C-702": 40.0,    # Viewfinder
    "S8C-801": 128.5,   # Body Left Half
    "S8C-802": 67.0,    # Body Right Half
    "S8C-803": 133.0,   # Top Plate
    "S8C-804": 28.0,    # Trigger Assembly
}


def _qr_size_mm(part_number: str) -> Optional[float]:
    """Return QR code size in mm for a part, or None to skip."""
    if part_number in SKIP_QR_PARTS:
        return None
    max_dim = PART_MAX_DIM.get(part_number, 25.0)  # default: assume large
    return LARGE_QR_MM if max_dim > 20.0 else SMALL_QR_MM


def _mm_to_px(mm_val: float) -> int:
    """Convert mm to pixels at 300 DPI."""
    return int(mm_val / 25.4 * DPI)


# ---------------------------------------------------------------------------
# QR code generation
# ---------------------------------------------------------------------------

def generate_qr_image(url: str, size_mm: float) -> Image.Image:
    """Generate a QR code image at the specified physical size."""
    size_px = _mm_to_px(size_mm)

    qr = qrcode.QRCode(
        version=None,  # auto-size
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=1,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img = img.get_image()
    img = img.resize((size_px, size_px), Image.NEAREST)
    return img


def generate_part_qr_codes(output_dir: str) -> list:
    """Generate individual QR code PNGs for each part in the catalog.

    Returns list of (part_number, filename, size_mm) for parts that got QR codes.
    """
    os.makedirs(output_dir, exist_ok=True)
    results = []

    for part_number, entry in PART_CATALOG.items():
        size = _qr_size_mm(part_number)
        if size is None:
            print(f"    SKIP {part_number} ({entry.name}) — too small, QR on parent module")
            continue

        url = f"{BASE_URL}/{part_number}"
        img = generate_qr_image(url, size)
        filename = f"qr_{part_number}.png"
        filepath = os.path.join(output_dir, filename)
        img.save(filepath, dpi=(DPI, DPI))
        results.append((part_number, filename, size))
        print(f"    {part_number} → {filename} ({size}mm × {size}mm)")

    # Master camera QR
    master_img = generate_qr_image(REPAIR_GUIDE_URL, LARGE_QR_MM)
    master_path = os.path.join(output_dir, "qr_master_repair_guide.png")
    master_img.save(master_path, dpi=(DPI, DPI))
    print(f"    MASTER → qr_master_repair_guide.png (repair guide)")

    return results


# ---------------------------------------------------------------------------
# QR code sheet PDF (A4)
# ---------------------------------------------------------------------------

def generate_qr_sheet_pdf(output_dir: str) -> str:
    """Generate an A4 PDF with all part QR codes in a labeled grid."""
    os.makedirs(output_dir, exist_ok=True)
    pdf_path = os.path.join(output_dir, "qr_code_sheet.pdf")

    page_w, page_h = A4  # 210mm x 297mm in points
    margin = 15 * mm
    cell_w = 40 * mm
    cell_h = 35 * mm
    qr_display = 20 * mm  # QR display size on the sheet

    cols = int((page_w - 2 * margin) / cell_w)
    rows = int((page_h - 2 * margin) / cell_h)

    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.setTitle("Super 8 Camera — Part QR Codes")

    parts = [(pn, entry) for pn, entry in PART_CATALOG.items()
             if pn not in SKIP_QR_PARTS]

    idx = 0
    while idx < len(parts):
        # Page header
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, page_h - 10 * mm,
                     f"Super 8 Camera — Part QR Codes (v{INTERFACE_VERSION})")
        c.setFont("Helvetica", 7)
        c.drawString(margin, page_h - 14 * mm,
                     "Cut along grid lines. Attach QR to corresponding part.")

        for row in range(rows):
            for col in range(cols):
                if idx >= len(parts):
                    break

                part_number, entry = parts[idx]
                url = f"{BASE_URL}/{part_number}"

                x = margin + col * cell_w
                y = page_h - 20 * mm - (row + 1) * cell_h

                # Generate QR as temp image
                qr_img = generate_qr_image(url, 15.0)
                tmp_path = os.path.join(output_dir, f"_tmp_{part_number}.png")
                qr_img.save(tmp_path, dpi=(DPI, DPI))

                # Draw QR
                c.drawImage(tmp_path, x + 2 * mm, y + 8 * mm,
                            width=qr_display, height=qr_display)
                os.remove(tmp_path)

                # Labels
                c.setFont("Helvetica-Bold", 7)
                c.drawString(x + qr_display + 4 * mm, y + 22 * mm, part_number)
                c.setFont("Helvetica", 6)
                # Truncate long names
                name = entry.name[:18]
                c.drawString(x + qr_display + 4 * mm, y + 18 * mm, name)
                c.drawString(x + qr_display + 4 * mm, y + 14 * mm,
                             f"v{INTERFACE_VERSION}")

                # Cell border (dashed cut line)
                c.setDash(2, 2)
                c.setStrokeColorRGB(0.7, 0.7, 0.7)
                c.rect(x, y + 4 * mm, cell_w - 2 * mm, cell_h - 2 * mm)
                c.setDash()

                idx += 1

        c.showPage()

    # Add master repair guide QR on last page
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, page_h - 20 * mm, "Master Repair Guide QR")
    c.setFont("Helvetica", 10)
    c.drawString(margin, page_h - 28 * mm,
                 "Scan for the complete online repair guide:")
    c.drawString(margin, page_h - 34 * mm, REPAIR_GUIDE_URL)

    master_img = generate_qr_image(REPAIR_GUIDE_URL, 30.0)
    master_tmp = os.path.join(output_dir, "_tmp_master.png")
    master_img.save(master_tmp, dpi=(DPI, DPI))
    c.drawImage(master_tmp, margin, page_h - 80 * mm,
                width=40 * mm, height=40 * mm)
    os.remove(master_tmp)

    c.showPage()
    c.save()
    print(f"    PDF → {pdf_path}")
    return pdf_path


# ---------------------------------------------------------------------------
# Compatibility label (40mm x 15mm PNG)
# ---------------------------------------------------------------------------

def generate_compatibility_label(part_number: str,
                                  output_dir: str = "export/qr") -> str:
    """Generate a compatibility label PNG (40mm x 15mm) for shipping.

    Shows:
      - Part number
      - Interface spec version ("v1.0 Compatible")
      - Checkmark icon indicating verified fit
    """
    os.makedirs(output_dir, exist_ok=True)

    width_px = _mm_to_px(40.0)   # ~472 px
    height_px = _mm_to_px(15.0)  # ~177 px

    img = Image.new("RGB", (width_px, height_px), "white")
    draw = ImageDraw.Draw(img)

    # Border
    draw.rectangle([0, 0, width_px - 1, height_px - 1],
                   outline="black", width=2)

    # Try to use a decent font, fall back to default
    font_large = None
    font_small = None
    try:
        font_large = ImageFont.truetype("arial.ttf", 28)
        font_small = ImageFont.truetype("arial.ttf", 18)
    except (OSError, IOError):
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        except (OSError, IOError):
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()

    # Checkmark circle (left side)
    cx, cy = 30, height_px // 2
    r = 22
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#2ECC40", outline="#1a8a2e", width=2)
    # Checkmark (simple lines)
    draw.line([(cx - 10, cy), (cx - 3, cy + 10), (cx + 12, cy - 10)],
              fill="white", width=4)

    # Part number
    text_x = 60
    draw.text((text_x, 12), part_number, fill="black", font=font_large)

    # Version compatibility
    draw.text((text_x, 55), f"v{INTERFACE_VERSION} Compatible",
              fill="#555555", font=font_small)

    # Small QR in the right corner
    url = f"{BASE_URL}/{part_number}"
    qr_img = generate_qr_image(url, 12.0)
    qr_size = _mm_to_px(12.0)
    qr_img = qr_img.resize((min(qr_size, height_px - 10),
                              min(qr_size, height_px - 10)), Image.NEAREST)
    qr_x = width_px - qr_img.width - 8
    qr_y = (height_px - qr_img.height) // 2
    img.paste(qr_img, (qr_x, qr_y))

    filename = f"label_{part_number}.png"
    filepath = os.path.join(output_dir, filename)
    img.save(filepath, dpi=(DPI, DPI))
    return filepath


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate QR codes for Super 8 Camera parts")
    parser.add_argument("--output", "-o", default="export/qr",
                        help="Output directory (default: export/qr)")
    args = parser.parse_args()

    sep = "=" * 65
    print(f"\n{sep}")
    print("  QR CODE GENERATION")
    print(sep)

    # 1. Individual part QR codes
    print(f"\n  Individual part QR codes:")
    results = generate_part_qr_codes(args.output)
    print(f"\n  Generated {len(results)} QR codes")

    # 2. QR code sheet PDF
    print(f"\n  QR code sheet PDF:")
    generate_qr_sheet_pdf(args.output)

    # 3. Compatibility labels
    print(f"\n  Compatibility labels:")
    label_count = 0
    for part_number in PART_CATALOG:
        if part_number not in SKIP_QR_PARTS:
            path = generate_compatibility_label(part_number, args.output)
            print(f"    {part_number} → {os.path.basename(path)}")
            label_count += 1
    print(f"\n  Generated {label_count} compatibility labels")

    print(f"\n  All outputs in: {args.output}/")
    print(sep)


if __name__ == "__main__":
    main()
