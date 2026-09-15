# RAG pipeline notes

Working notes for the current FastAPI + Postgres + Ollama stack. Not a product spec.

## What it does

Upload a PDF → parse text with pypdf → split into overlapping chunks → embed with `all-MiniLM-L6-v2` → store in Postgres (`documents` + `chunks` with `vector(384)`) → on `POST /query`, embed the question, retrieve the top 5 chunks with pgvector `<=>`, send them to local Ollama (`llama3.2`) with a “answer only from context” system prompt → return `{question, answer, sources}` with filename + page citations.

Auth: JWT on `/documents` and `/query`. Login is still a hardcoded test user.

```
POST /documents  →  pdf_parser → chunker → embedder → document_store
POST /query      →  embed question → pgvector top-5 → Ollama → citations
```

## Design choices

- **pgvector in Postgres, not a separate vector DB.** We already run Postgres for the app. One container, SQL joins to filenames, and `ON DELETE CASCADE` is enough at this scale. Pinecone/Qdrant would be extra infra for a student project.

- **Chunk size 500, overlap 50.** Small enough that MiniLM’s ~256-token window is comfortable; overlap so a sentence split across a boundary still shows up in two chunks. Tuned by looking at day-14 output, not a paper.

- **`all-MiniLM-L6-v2`.** Fast on CPU, 384-d, no API key. Good enough to prove retrieval. A stronger model (e.g. `bge-small` / OpenAI) is a later swap in `app/services/embedder.py`.

- **Raw SQL, no ORM.** Tables are two files of `CREATE TABLE`. psycopg2 + the pgvector Python adapter is fewer moving parts while the schema is still changing. SQLAlchemy can wait until users/jobs exist.

## Known limitations

- Upload is **synchronous**: the HTTP request waits for parse + embed + insert. Fine for one PDF; will block under real load (Celery later).
- **No OCR.** Scanned PDFs store a `documents` row and zero chunks.
- **No re-ranking.** Top-5 cosine distance is the whole retrieval stack.
- **One embedding model**, shared for index and query (required for cosine to mean anything).
- Duplicate uploads create **duplicate document rows** (same filename, new id). Citations can repeat the same page from two ids.
- `GET /documents` is still an **in-memory list** for this process; Postgres is the source of truth for RAG.
- LLM is **local llama3.2** via Ollama; if Ollama is down, query returns 503 after retrieval.
- No eval set, no chunk-quality metrics, no hybrid (keyword + vector) search.

## Next

1. **LangChain comparison** — rebuild the same retrieve-then-generate path with LC so we can see what the framework actually buys vs this hand-rolled loop.
2. **Agent / LangGraph phase** — tools beyond “search my PDFs” (the day-9/10 weather loop was the sketch), with graph state instead of a single `/query` call.
3. Infra follow-ups already noted in code: async ingest, real users in Postgres, maybe a job queue.
