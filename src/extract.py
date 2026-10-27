import re
from collections import Counter

import fitz  # PyMuPDF


def norm(text):
    return re.sub(r"\d+", "#", text)


def page_rows(page, y_tol=0.6):
    """Reading-order text, with same-baseline pieces joined into 'a | b | c' rows."""
    lines = {}
    for x0, y0, x1, y1, word, block, line, _ in page.get_text("words"):
        d = lines.setdefault((block, line), {"x0": x0, "y0": y0, "x1": x1, "y1": y1, "words": []})
        d["x0"], d["y0"] = min(d["x0"], x0), min(d["y0"], y0)
        d["x1"], d["y1"] = max(d["x1"], x1), max(d["y1"], y1)
        d["words"].append(word)

    rows, prev = [], None
    for d in lines.values():
        text = " ".join(d["words"])
        if prev:
            h = d["y1"] - d["y0"]
            same_row = abs((d["y0"] + d["y1"]) / 2 - (prev["y0"] + prev["y1"]) / 2) < y_tol * h
            if same_row and d["x0"] >= prev["x1"] - 1:
                prev["text"] += " | " + text
                prev["x1"] = d["x1"]
                continue
        prev = {"text": text, "x0": d["x0"], "y0": d["y0"], "y1": d["y1"], "x1": d["x1"]}
        rows.append(prev)
    return rows


def in_margin(row, page, margin=0.10):
    w, h = page.rect.width, page.rect.height
    return (row["y0"] < margin * h or row["y1"] > (1 - margin) * h
            or row["x1"] < 0.08 * w or row["x0"] > 0.92 * w)


def find_boilerplate(doc, min_share=0.4):
    """Margin lines that repeat on >= 40% of pages (headers, footers, sidebars)."""
    counts = Counter()
    for page in doc:
        counts.update({norm(r["text"]) for r in page_rows(page) if in_margin(r, page)})
    return {k for k, c in counts.items() if c >= min_share * len(doc)}


def extract_page(doc, page_no, boilerplate):
    """page_no is the 1-based PDF index, the same one used in #page=N links."""
    page = doc[page_no - 1]
    rows = [r for r in page_rows(page)
            if not (in_margin(r, page) and norm(r["text"]) in boilerplate)]
    text = "\n".join(r["text"] for r in rows)
    return {"page": page_no, "text": text, "empty": len(text.strip()) < 50}