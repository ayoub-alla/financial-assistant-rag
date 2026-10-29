import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer

load_dotenv()
CHUNKS = Path("data/chunks.jsonl")
SLICE = 256


def main():
    rows = [json.loads(l) for l in CHUNKS.open(encoding="utf-8")]
    rows = [r for r in rows if not r["low_quality"]]

    coll = MongoClient(os.environ["MONGODB_URI"])[os.getenv("MONGODB_DB", "financial_reports")][
        os.getenv("MONGODB_COLLECTION", "chunks")
    ]
    if "--reset" in sys.argv:
        coll.delete_many({})
    done = set(coll.distinct("_id"))
    rows = [r for r in rows if r["id"] not in done]
    print(f"{len(rows)} chunks to embed ({len(done)} already in the database)")
    if not rows:
        return

    model = SentenceTransformer(os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3"))
    model.max_seq_length = 1024

    for i in range(0, len(rows), SLICE):
        part = rows[i:i + SLICE]
        texts = [f"[{r['company_name']} {r['year']} p.{r['page']}]\n{r['text']}" for r in part]
        vecs = model.encode(texts, batch_size=32, normalize_embeddings=True)
        for r, v in zip(part, vecs):
            r["_id"] = r.pop("id")
            r["embedding"] = v.tolist()
        coll.insert_many(part)
        print(f"inserted {i + len(part)}/{len(rows)}")


if __name__ == "__main__":
    main()