from fastapi import FastAPI
from pydantic import BaseModel, Field

from .answer import answer
from .db import connect
from .schemas import Answer

app = FastAPI(title="OWASP Cheat Sheet Assistant")


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ask")
def ask(req: AskRequest) -> Answer:
    with connect() as conn:
        return answer(req.question, conn=conn)
