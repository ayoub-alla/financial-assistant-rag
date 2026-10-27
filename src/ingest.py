import json
import re
import sys
from collections import Counter
from pathlib import Path

import fitz

sys.path.insert(0, ".")
from src.chunking import chunk_page
from src.extract import extract_page, find_boilerplate

PDF_DIR = Path("data/pdfs")
OUT = Path("data/chunks.jsonl")
PATTERN = re.compile(r"^([a-z]+)_(\d{4})_([a-z]+)$")
NAMES = {"attijariwafa": "Attijariwafa Bank", "iam": "Maroc Telecom", "marsa": "Marsa Maroc"}


def main():
    lengths = []
    with OUT.open("w", encoding="utf-8") as f:
        for pdf in sorted(PDF_DIR.glob("*.pdf")):
            m = PATTERN.match(pdf.stem)
            if not m:
                print(f"SKIP {pdf.name} (name does not match company_year_doctype)")
                continue
            company, year, doc_type = m.group(1), int(m.group(2)), m.group(3)

            doc = fitz.open(pdf)
            boilerplate = find_boilerplate(doc)
            kinds, empty = Counter(), []
            for p in range(1, len(doc) + 1):
                page = extract_page(doc, p, boilerplate)
                if page["empty"]:
                    empty.append(p)
                    continue
                for k, ch in enumerate(chunk_page(page["text"])):
                    rec = {
                        "id": f"{pdf.stem}_p{p}_c{k}",
                        "text": ch["text"],
                        "chunk_type": ch["type"],
                        "company": company,
                        "company_name": NAMES.get(company, company),
                        "year": year,
                        "doc_type": doc_type,
                        "period": f"FY{year}",
                        "page": p,
                        "source_file": pdf.name,
                    }
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    kinds[ch["type"]] += 1
                    lengths.append(len(ch["text"]))
            print(f"{pdf.name}: {len(doc)} pages, {sum(kinds.values())} chunks "
                  f"({kinds['table']} table, {kinds['text']} text), {len(empty)} empty pages {empty[:8]}")

    print(f"\nTotal {len(lengths)} chunks, avg {sum(lengths) // max(1, len(lengths))} chars, max {max(lengths, default=0)}")
    print(f"Written to {OUT}")


if __name__ == "__main__":
    main()