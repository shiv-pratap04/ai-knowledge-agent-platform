# RAG Pipeline

The application has one RAG endpoint: `POST /query`. It uses LangChain for document loading, splitting, embeddings, retrieval, prompting, and generation.

## Ingestion

```text
POST /documents
    -> LangChain PyPDFLoader
    -> RecursiveCharacterTextSplitter
    -> HuggingFaceEmbeddings (all-MiniLM-L6-v2, 384 dimensions)
    -> PostgreSQL documents/chunks tables with pgvector embeddings
```

Uploads are processed synchronously. Empty or image-only PDFs are stored without chunks and reported to the caller. PostgreSQL remains the source of truth for indexed documents.

## Query

```text
POST /query
    -> LangChain HuggingFaceEmbeddings
    -> PgChunksRetriever
    -> pgvector cosine retrieval
    -> LangChain ChatPromptTemplate
    -> ChatOllama (llama3.2)
    -> answer with page-cited sources
```

`PgChunksRetriever` is a LangChain `BaseRetriever` over the existing `chunks` table. The database schema remains the application-owned `documents` and `chunks` schema with `vector(384)` embeddings.

## Agent

```text
POST /agent
    -> LangGraph ReAct agent
    -> LangChain search_knowledge_base tool
    -> PgChunksRetriever
    -> ChatOllama (llama3.2)
```

LangGraph owns the agent state and tool loop. There is no manual prompt-parsing or hand-written function-calling loop in the application.

## Configuration

- Embedding model: `all-MiniLM-L6-v2`
- Embedding dimension: `384`
- Vector distance: pgvector cosine distance (`<=>`)
- Chat model: local Ollama `llama3.2`
- Authentication: JWT on `/documents`, `/query`, and `/agent`
