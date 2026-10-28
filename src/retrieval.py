import os
from functools import lru_cache

from dotenv import load_dotenv
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer

load_dotenv()
INDEX = os.getenv("MONGODB_VECTOR_INDEX", "chunks_vector_index")
TOP_K = int(os.getenv("TOP_K", 6))


@lru_cache(maxsize=1)
def _model():
    m = SentenceTransformer(os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3"))
    m.max_seq_length = 1024
    return m


@lru_cache(maxsize=1)
def _coll():
    client = MongoClient(os.environ["MONGODB_URI"])
    return client[os.getenv("MONGODB_DB", "financial_reports")][os.getenv("MONGODB_COLLECTION", "chunks")]


def _cond(field, value):
    if isinstance(value, (list, tuple)):
        return {field: {"$in": list(value)}}
    return {field: {"$eq": value}}


def retrieve(question, k=TOP_K, company=None, year=None, doc_type=None):
    """Top-k chunks by vector similarity. company/year/doc_type accept a value or a list."""
    conds = [_cond(f, v) for f, v in (("company", company), ("year", year), ("doc_type", doc_type)) if v]
    vec = _model().encode([question], normalize_embeddings=True)[0].tolist()

    stage = {"index": INDEX, "path": "embedding", "queryVector": vec,
             "numCandidates": max(100, k * 20), "limit": k}
    if conds:
        stage["filter"] = conds[0] if len(conds) == 1 else {"$and": conds}

    pipeline = [
        {"$vectorSearch": stage},
        {"$addFields": {"score": {"$meta": "vectorSearchScore"}}},
        {"$project": {"embedding": 0}},
    ]
    return list(_coll().aggregate(pipeline))