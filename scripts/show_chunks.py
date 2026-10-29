import json
import sys

f, page = sys.argv[1], int(sys.argv[2])
for line in open("data/chunks.jsonl", encoding="utf-8"):
    r = json.loads(line)
    if r["source_file"] == f and r["page"] == page:
        print(f"--- {r['id']} [{r['chunk_type']}] ---\n{r['text']}\n")