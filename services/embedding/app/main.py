from fastapi import FastAPI
from pydantic import BaseModel, Field
from app.embedder import get_embedder, DIM

app = FastAPI(title="Trawl Embedding Service")
_embedder = get_embedder()


class EmbedRequest(BaseModel):
    texts: list[str] = Field(min_length=1)


class EmbedResponse(BaseModel):
    vectors: list[list[float]]
    dim: int


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/embed", response_model=EmbedResponse)
def embed(req: EmbedRequest) -> EmbedResponse:
    return EmbedResponse(vectors=_embedder.embed(req.texts), dim=DIM)
