import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.generate import answer

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = Path(__file__).resolve().parent / "static"
PDF_DIR = Path(os.getenv("PDF_DIR", ROOT / "data" / "pdfs")).resolve()

app = FastAPI(title="Moroccan Financial Reports Assistant")

# PDFs stay local and are served by filename; no upload route.
if PDF_DIR.is_dir():
    app.mount("/pdfs", StaticFiles(directory=PDF_DIR), name="pdfs")


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


@app.post("/ask")
def ask(request: AskRequest):
    try:
        result = answer(request.question.strip())
        return {
            "answer": result["answer"],
            "sources": result["sources"],
            "model": result["model"],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to generate an answer") from exc


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(STATIC_DIR / "index.html")
