# AI Knowledge Agent Platform

FastAPI backend for an AI RAG + agent system.

> Work-in-progress student project — skeleton only, no AI logic yet.

## Run locally

1. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy environment variables:

   ```bash
   cp .env.example .env
   ```

4. Start Postgres and Redis:

   ```bash
   docker compose up -d
   ```

5. Run the API server:

   ```bash
   uvicorn app.main:app --reload
   ```

The health check is available at `GET http://127.0.0.1:8000/health`.
