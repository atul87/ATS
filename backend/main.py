import logging
import os
import hashlib
import re
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import (
    ALLOWED_ORIGINS,
    APP_DESCRIPTION,
    APP_TITLE,
    APP_VERSION,
    SPACY_MODEL_PRIMARY,
    SPACY_MODEL_SECONDARY,
    SENTENCE_TRANSFORMER_MODEL,
)
from backend.api.routes import router
import backend.core.config as core_config

logger = logging.getLogger("ats_resume_scorer")


def _truthy_env(name: str) -> bool:
    return os.getenv(name, "").lower() in {"1", "true", "yes", "on"}


class _FastDoc:
    ents = ()
    noun_chunks = ()


class _FastNLP:
    def __call__(self, text: str):
        return _FastDoc()


class _FastEmbedder:
    def encode(self, text: str, convert_to_tensor: bool = False):
        vector = [0.0] * 64
        for token in re.findall(r"[a-z0-9+#.]+", (text or "").lower()):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            vector[digest[0] % len(vector)] += 1.0

        if not any(vector):
            vector[0] = 1.0
        return vector


# Log startup environment validation. In production, fail fast on missing vars.
missing_env = core_config.check_required_env_vars()
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
if missing_env:
    if ENVIRONMENT == "production":
        logger.error(f"Startup missing environment variables (production): {missing_env}")
        raise RuntimeError(f"Missing required environment variables: {missing_env}")
    else:
        logger.warning(f"Startup missing environment variables: {missing_env}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    import time

    start_time = time.time()
    logger.info("Starting ATS Resume Analyzer API...")

    if _truthy_env("ATS_FAST_MODEL_MODE"):
        app.state.nlp = _FastNLP()
        app.state.embedder = _FastEmbedder()
        logger.info("ATS_FAST_MODEL_MODE enabled; using deterministic lightweight models.")
    else:
        logger.info(f"Loading spaCy NLP model: {SPACY_MODEL_PRIMARY}")
        import spacy

        spacy_start = time.time()
        try:
            app.state.nlp = spacy.load(SPACY_MODEL_PRIMARY)
            spacy_time = time.time() - spacy_start
            logger.info(
                f"Loaded {SPACY_MODEL_PRIMARY} in {spacy_time:.2f}s",
                extra={
                    "model_load": spacy_time,
                    "model_load_time": spacy_time,
                    "model_name": SPACY_MODEL_PRIMARY,
                },
            )
        except OSError:
            logger.warning(
                f"{SPACY_MODEL_PRIMARY} not found — falling back to {SPACY_MODEL_SECONDARY}"
            )
            app.state.nlp = spacy.load(SPACY_MODEL_SECONDARY)
            spacy_time = time.time() - spacy_start
            logger.info(
                f"Loaded {SPACY_MODEL_SECONDARY} (fallback) in {spacy_time:.2f}s",
                extra={
                    "model_load": spacy_time,
                    "model_load_time": spacy_time,
                    "model_name": SPACY_MODEL_SECONDARY,
                },
            )

        st_start = time.time()
        logger.info(f"Loading SentenceTransformer: {SENTENCE_TRANSFORMER_MODEL}")
        from sentence_transformers import SentenceTransformer

        app.state.embedder = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)
        st_time = time.time() - st_start
        logger.info(
            f"Loaded {SENTENCE_TRANSFORMER_MODEL} in {st_time:.2f}s",
            extra={
                "model_load": st_time,
                "model_load_time": st_time,
                "model_name": SENTENCE_TRANSFORMER_MODEL,
            },
        )

    total_time = time.time() - start_time
    logger.info(
        f"All models loaded. API is ready to serve requests in {total_time:.2f}s.",
        extra={"total_load_time": total_time},
    )

    try:
        yield
    finally:
        logger.info("shutting down the api!!")


app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root():
    return {
        "name": "ATS Resume Analyzer API",
        "version": "2.0.0",
        "endpoints": {
            "POST   /api/v1/analyze-resume": "Analyze a resume",
            "GET    /api/v1/history": "Get user history",
            "DELETE /api/v1/history/:id": "Delete a history entry",
            "GET    /api/v1/health": "Health check",
            "POST   /api/v1/generate-pdf": "Generate PDF report from data",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-restart on code changes (dev only)
    )
