"""Decimal-safe quote calculation and dependency-free PDF output."""
from __future__ import annotations

import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

TWOPLACES = Decimal("0.01")

def money(value) -> Decimal:
    if value is None or value == "": return Decimal("0.00")
    text=str(value).strip().replace(" ", "").replace("\u00a0", "")
    if "," in text and "." in text: text=text.replace(".", "").replace(",", ".")
    elif "," in text: text=text.replace(",", ".")
    return Decimal(text or "0").quantize(TWOPLACES, rounding=ROUND_HALF_UP)

def format_number(value, decimals=2) -> str:
    number=money(value); text=f"{number:,.{decimals}f}".replace(",","X").replace(".",",").replace("X"," ")
    return text.rstrip("0").rstrip(",") if decimals else text.split(",")[0]

def format_sek(value) -> str:
    return f"{format_number(value)} kr"

def calculate_quote(*, base_price=0, participants=0, price_per_participant=0, travel_km=0,
                    km_rate=0, overnight=0, per_diem=0, venue=0, catering=0,
                    other=0, vat_rate=25, include=None, manual_total=None):
    values = {"base_price": base_price, "participants": participants, "price_per_participant": price_per_participant,
              "travel_km": travel_km, "km_rate": km_rate, "overnight": overnight, "per_diem": per_diem,
              "venue": venue, "catering": catering, "other": other}
    values = {key: money(val) for key, val in values.items()}
    items = {
        "base_price": values["base_price"],
        "participant_cost": values["participants"] * values["price_per_participant"],
        "travel_cost": values["travel_km"] * values["km_rate"],
        "overnight": values["overnight"], "per_diem": values["per_diem"],
        "venue": values["venue"], "catering": values["catering"], "other": values["other"],
    }
    enabled = set(items) if include is None else {"base_price", "participant_cost", *set(include)}
    selected = {key: amount for key, amount in items.items() if key in enabled}
    internal_total = sum(selected.values(), Decimal("0.00")).quantize(TWOPLACES)
    ex_vat = money(manual_total) if manual_total not in (None, "") else internal_total
    vat = (ex_vat * money(vat_rate) / Decimal("100")).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    return {"currency": "SEK", "participants": int(values["participants"]), "vat_rate": str(money(vat_rate)),
            "items": {key: str(value) for key, value in selected.items()}, "internal_total": str(internal_total),
            "manual_total": str(money(manual_total)) if manual_total not in (None, "") else "",
            "total_price_ex_vat": str(ex_vat), "vat_amount": str(vat), "total_price_inc_vat": str(ex_vat + vat)}

def render_quote_template(template: str, values: dict) -> str:
    return re.sub(r"{{\s*([A-Za-z0-9_]+)\s*}}", lambda match: str(values.get(match.group(1), "")), template)

def _pdf_escape(text: str) -> str:
    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

def generate_pdf(path: str | Path, *, title: str, lines: list[str]) -> Path:
    """Write a small, valid one-page PDF without requiring a third-party package."""
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    content = ["BT", "/F1 11 Tf", "50 790 Td", "14 TL"]
    for line in [title, ""] + lines:
        chunks = [line[i:i + 90] for i in range(0, max(1, len(line)), 90)] or [""]
        for chunk in chunks:
            content.append(f"({_pdf_escape(chunk)}) Tj T*")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1", "replace")
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>", b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>", b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"]
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"); offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(output)); output.extend(f"{index} 0 obj\n".encode()); output.extend(obj); output.extend(b"\nendobj\n")
    xref = len(output); output.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode()); output.extend("".join(f"{offset:010d} 00000 n \n" for offset in offsets[1:]).encode()); output.extend(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()); path.write_bytes(output); return path
