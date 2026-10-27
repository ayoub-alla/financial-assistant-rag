import math
import re

MAX_TEXT_CHARS = 1200
TEXT_OVERLAP_LINES = 2
TABLE_ROWS = 8
CAPTION_LINES = 2
HEADER_RE = re.compile(r"\b(19|20)\d{2}\b|\bNote\b|\bChange\b")


def _flags(lines):
    """True for table rows (contain ' | '), plus short wrapped labels sandwiched between rows."""
    n = len(lines)
    flags = []
    for i, line in enumerate(lines):
        t = " | " in line
        if not t and 0 < i < n - 1 and len(line) < 80 and " | " in lines[i - 1] and " | " in lines[i + 1]:
            t = True
        flags.append(t)
    return flags


def _runs(lines, flags):
    runs = []
    for line, t in zip(lines, flags):
        if runs and runs[-1][0] == t:
            runs[-1][1].append(line)
        else:
            runs.append([t, [line]])
    for r in runs:
        if r[0] and len(r[1]) < 2:  # a single piped line is not a table
            r[0] = False
    merged = []
    for r in runs:
        if merged and merged[-1][0] == r[0]:
            merged[-1][1].extend(r[1])
        else:
            merged.append(r)
    return merged


def _caption(prev_lines):
    """Short title lines just above a table (copied, not moved)."""
    cap = []
    for line in reversed(prev_lines[-CAPTION_LINES:]):
        if len(line) < 80 and not line.rstrip().endswith((".", ",", ";")):
            cap.insert(0, line)
        else:
            break
    return cap


def _table_chunks(caption, rows):
    header = rows[0] if HEADER_RE.search(rows[0]) else None
    body = rows[1:] if header else rows
    if not body:
        return []
    size = math.ceil(len(body) / math.ceil(len(body) / TABLE_ROWS))  # even split
    chunks = []
    for i in range(0, len(body), size):
        lines = caption + ([header] if header else []) + body[i:i + size]
        chunks.append("\n".join(lines))
    return chunks


def _text_chunks(lines):
    chunks, cur, size = [], [], 0
    for line in lines:
        if cur and size + len(line) > MAX_TEXT_CHARS:
            chunks.append("\n".join(cur))
            cur = cur[-TEXT_OVERLAP_LINES:]
            size = sum(len(x) + 1 for x in cur)
        cur.append(line)
        size += len(line) + 1
    if cur:
        chunks.append("\n".join(cur))
    return [c for c in chunks if len(c.strip()) >= 40]


def chunk_page(text):
    lines = [l for l in text.split("\n") if l.strip()]
    runs = _runs(lines, _flags(lines))
    out = []
    for i, (is_table, rows) in enumerate(runs):
        if is_table:
            cap = _caption(runs[i - 1][1]) if i and not runs[i - 1][0] else []
            out += [{"type": "table", "text": c} for c in _table_chunks(cap, rows)]
        else:
            out += [{"type": "text", "text": c} for c in _text_chunks(rows)]
    return out