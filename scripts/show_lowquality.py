import json
import random
from collections import Counter

rows = [json.loads(l) for l in open("data/chunks.jsonl", encoding="utf-8")]
bad = [r for r in rows if r["low_quality"]]
print(Counter(r["company"] for r in bad))

random.seed(1)
for r in random.sample(bad, 10):
    print(f"\n--- {r['id']} [{r['chunk_type']}] ---\n{r['text'][:400]}")