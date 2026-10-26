import sys
import time
from pathlib import Path

import fitz  # PyMuPDF
import pdfplumber

sys.stdout.reconfigure(encoding="utf-8")  # avoids Windows console encoding errors


def to_markdown(rows):
    rows = [[(c or "").replace("\n", " ").strip() for c in r] for r in rows if r]
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    lines = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * width]
    lines += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(lines)


def pymupdf_text(pdf, n):
    return fitz.open(pdf)[n - 1].get_text("text")


def pymupdf_tables(pdf, n):
    tabs = fitz.open(pdf)[n - 1].find_tables().tables
    return "\n\n".join(to_markdown(t.extract()) for t in tabs)


def plumber_tables(pdf, n, settings=None):
    with pdfplumber.open(pdf) as p:
        tabs = p.pages[n - 1].extract_tables(settings) if settings else p.pages[n - 1].extract_tables()
    return "\n\n".join(to_markdown(t) for t in tabs)


def scan(pdf, min_rows=5):
    """List pages that contain a table with at least min_rows rows."""
    for i, page in enumerate(fitz.open(pdf), start=1):
        try:
            big = [t for t in page.find_tables().tables if t.row_count >= min_rows and t.col_count >= 2]
        except Exception:
            continue
        if big:
            r = max(t.row_count for t in big)
            c = max(t.col_count for t in big)
            print(f"page {i}: {len(big)} table(s), largest {r} rows x {c} cols")


def compare(pdf, n):
    out = Path("docs/extraction_tests")
    out.mkdir(parents=True, exist_ok=True)
    stem = f"{Path(pdf).stem}_p{n}"
    methods = {
        "1_pymupdf_text": lambda: pymupdf_text(pdf, n),
        "2_pymupdf_tables": lambda: pymupdf_tables(pdf, n),
        "3_pdfplumber_lines": lambda: plumber_tables(pdf, n),
        "4_pdfplumber_text": lambda: plumber_tables(
            pdf, n, {"vertical_strategy": "text", "horizontal_strategy": "text"}
        ),
        "5_plumber_layout_text": lambda: plumber_layout_text(pdf, n),
        "6_cropped_text_tables": lambda: cropped_text_tables(pdf, n),
        "7_row_merged_text": lambda: row_merged_text(pdf, n),
    }
    for name, fn in methods.items():
        t0 = time.time()
        content = fn() or "(nothing extracted)"
        dt = time.time() - t0
        (out / f"{stem}__{name}.md").write_text(content, encoding="utf-8")
        print(f"\n===== {name}  ({dt:.2f}s) =====\n{content[:2500]}")

def plumber_layout_text(pdf, n):
    with pdfplumber.open(pdf) as p:
        return p.pages[n - 1].extract_text(layout=True)


def cropped_text_tables(pdf, n):
    bboxes = [t.bbox for t in fitz.open(pdf)[n - 1].find_tables().tables]
    out = []
    with pdfplumber.open(pdf) as p:
        page = p.pages[n - 1]
        for b in bboxes:
            region = page.crop(b, strict=False)
            rows = region.extract_table(
                {"vertical_strategy": "text", "horizontal_strategy": "text"}
            )
            out.append(to_markdown(rows) if rows else "")
    return "\n\n".join(out)

def row_merged_text(pdf, n, y_tol=0.6):
    """PyMuPDF reading order, with same-baseline pieces joined into one row."""
    page = fitz.open(pdf)[n - 1]
    lines = {}
    for x0, y0, x1, y1, word, block, line, _ in page.get_text("words"):
        d = lines.setdefault((block, line), {"x0": x0, "y0": y0, "x1": x1, "y1": y1, "words": []})
        d["x0"], d["y0"] = min(d["x0"], x0), min(d["y0"], y0)
        d["x1"], d["y1"] = max(d["x1"], x1), max(d["y1"], y1)
        d["words"].append(word)

    rows, prev = [], None
    for d in lines.values():
        text = " ".join(d["words"])
        if prev is not None:
            h = d["y1"] - d["y0"]
            same_row = abs((d["y0"] + d["y1"]) / 2 - (prev["y0"] + prev["y1"]) / 2) < y_tol * h
            to_right = d["x0"] >= prev["x1"] - 1
            if same_row and to_right:
                prev["text"] += " | " + text
                prev["x1"] = d["x1"]
                continue
        prev = {"text": text, "y0": d["y0"], "y1": d["y1"], "x1": d["x1"]}
        rows.append(prev)
    return "\n".join(r["text"] for r in rows)

if __name__ == "__main__":
    cmd, pdf = sys.argv[1], sys.argv[2]
    if cmd == "scan":
        scan(pdf)
    elif cmd == "compare":
        compare(pdf, int(sys.argv[3]))

