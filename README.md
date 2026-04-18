# CIBIL-RegBot

CIBIL-RegBot is a knowledge-graph enhanced regulatory compliance RAG system for RBI credit information reporting workflows. It combines clause-level ingestion, hybrid retrieval, hierarchy-based conflict resolution, citation-backed answer generation, and a reviewable audit trail.

## Stack

- Backend: FastAPI, SQLAlchemy, pgvector-ready storage, Redis caching, NetworkX knowledge graph
- Frontend: React 18, Vite, TypeScript, Zustand, React Query
- Retrieval: vector + BM25 hybrid search with RRF fusion and reranking
- Governance: hierarchy-aware conflict resolution, groundedness checks, full request audit logging

## Quick start

1. Copy `backend/.env.example` to `backend/.env` and fill in keys.
2. Make sure PostgreSQL and Redis are running locally or point `POSTGRES_URL` and `REDIS_URL` in `backend/.env` to your services.
3. Initialize the database with `python backend/scripts/init_db.py`.
4. Seed sample data with `python backend/scripts/seed_data.py`.
5. Run the backend with `uvicorn app.main:app --reload --port 8000` from `backend`.
6. Run the frontend with `npm install` and `npm run dev` from `frontend`.

## Core behavior

- Hierarchy is immutable: `RBI_MASTER > CICRA > RBI_CIRCULAR > SOP`
- Dispute timeline is fixed at `21 + 9 = 30` calendar days
- Consumer compensation is `Rs.100/day`
- Regulator penalty is `Rs.5,000/day`
- Answers must cite evidence or refuse with insufficient evidence

## Project map

- Backend app entry: `backend/app/main.py`
- RAG orchestrator: `backend/app/rag/pipeline.py`
- Ingestion orchestration: `backend/app/services/ingestion_service.py`
- Frontend query page: `frontend/src/pages/QueryPage.tsx`

# RAG-BOT
