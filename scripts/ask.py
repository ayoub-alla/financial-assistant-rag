import argparse
import sys
import time

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")
from src.generate import answer

ap = argparse.ArgumentParser()
ap.add_argument("question", nargs="+")
ap.add_argument("--company")
ap.add_argument("--year", type=int)
a = ap.parse_args()

t0 = time.time()
r = answer(" ".join(a.question), company=a.company, year=a.year)
dt = time.time() - t0

print(r["answer"])
print("\nSources:")
for s in r["sources"]:
    print(f"- {s['company_name']} {s['year']} {s['doc_type']}, p.{s['page']} ({s['source_file']})")
print(f"\n[{dt:.1f}s, model: {r['model']}]")