import sys

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")
from src.retrieval import retrieve

TESTS = [
    ("What were Maroc Telecom's total assets in 2025?", dict(company="iam", year=2025), "75,811"),
    ("What was Wafasalaf's net income in 2024?", dict(company="attijariwafa", year=2024), "353 million"),
    ("How much solid bulk traffic did Marsa Maroc handle in 2024?", dict(company="marsa", year=2024), "18.8 million tons"),
    ("Quels sont les principaux risques de Maroc Telecom ?", {}, None),
    ("Who won the 2022 football World Cup?", {}, None),
]

for q, flt, expect in TESTS:
    hits = retrieve(q, k=10, **flt)
    print(f"\n==== {q}  {flt}")
    if expect:
        ranks = [i for i, h in enumerate(hits, 1) if expect in h["text"]]
        print(f"   expected '{expect}': " + (f"FOUND at ranks {ranks}" if ranks else "MISSING from top 10"))
    for i, h in enumerate(hits[:6], start=1):
        body = h["text"].replace("\n", " / ")[:160]
        print(f"{i}. {h['score']:.3f} {h['_id']} [{h['chunk_type']}] {body}")