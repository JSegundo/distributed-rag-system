# CLAUDE.md - AI Assistant Guide for Distributed RAG System

This file provides guidance for Claude Code and other AI assistants working with this codebase.

## Project Overview

This is a **distributed Retrieval-Augmented Generation (RAG) system** that allows users to upload PDF documents and chat with them using AI. The system uses a microservices architecture with three main services communicating via RabbitMQ and PostgreSQL with pgvector.

**Key Purpose**: Document-based AI chat - users upload PDFs, the system extracts and embeds text, then enables semantic search and LLM-powered Q&A.

## Quick Reference - Development Commands

### Full Stack Development (Docker)
```bash
npm run dev          # Start all services with hot reload
npm run build:dev    # Build development containers
npm run stop         # Stop all services
npm run logs         # View all service logs
```

### Local Development (Without Docker)
```bash
# Infrastructure only
docker-compose -f docker-compose.dev.yml up postgres rabbitmq pgadmin

# API Server (Terminal 1)
cd server && npm install && npm run dev

# Processing Service (Terminal 2)
cd processing-service
python -m venv venv && source venv/bin/activate
pip install -r requirements/base.txt -r requirements/heavy.txt
python src/main.py

# Client (Terminal 3)
cd client && npm install && npm run dev
```

### Testing & Linting
```bash
cd server && npm test      # Server tests (Jest)
cd client && npm run lint  # Client linting (ESLint)
```

### Database Operations
```bash
# Connect to database
docker exec -it pdf_chat_rag-postgres-1 psql -U postgres -d ragdb

# Common queries
SELECT COUNT(*) FROM documents;
SELECT COUNT(*) FROM chunks;
\dt  # List tables
\dx  # List extensions (should show pgvector)
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐
│   Client    │────▶│   Server    │────▶│ Processing Svc   │
│  Next.js    │     │  Express    │     │    FastAPI       │
│  Port 3500  │     │  Port 3000  │     │   Port 8000      │
└─────────────┘     └─────────────┘     └──────────────────┘
                           │                      │
                           ▼                      ▼
                    ┌─────────────┐     ┌──────────────────┐
                    │  RabbitMQ   │     │   PostgreSQL     │
                    │  Port 5672  │     │   + pgvector     │
                    └─────────────┘     │   Port 5438      │
                                        └──────────────────┘
```

### Service Responsibilities

| Service | Language | Port | Purpose |
|---------|----------|------|---------|
| Client | TypeScript/React | 3500 | PDF upload UI, chat interface |
| Server | TypeScript/Node | 3000 | API gateway, WebSocket, LLM orchestration |
| Processing | Python | 8000 | PDF extraction, chunking, embedding, search |

## Project Structure

```
distributed-rag-system/
├── client/                     # Next.js 15 frontend
│   └── src/app/
│       ├── components/         # React components (PDFDropzone, ProcessingStatus)
│       ├── utils/              # Utility functions
│       └── page.tsx            # Main page
├── server/                     # Express.js API server
│   └── src/
│       ├── api/
│       │   ├── controllers/    # Request handlers
│       │   └── routes/         # API endpoints (document, chat, notifications)
│       ├── services/
│       │   ├── chat/           # ChatManager - orchestrates RAG flow
│       │   ├── llm/            # LLMService - Anthropic/OpenAI abstraction
│       │   ├── queue/          # QueueService - RabbitMQ wrapper
│       │   └── websocket/      # WebSocket notifications
│       ├── middleware/         # Express middleware
│       ├── types/              # TypeScript interfaces
│       └── config/             # Configuration (ports, queue settings)
├── processing-service/         # Python FastAPI service
│   └── src/
│       ├── api/                # FastAPI endpoints
│       │   └── routes/         # search.py, health.py
│       ├── process_pipeline/   # Document processing
│       │   ├── processor.py    # Main orchestrator
│       │   ├── extract.py      # PDF extraction (Docling)
│       │   ├── chunk.py        # Text chunking
│       │   └── embed.py        # OpenAI embeddings
│       ├── rag/                # RAG components
│       │   └── search.py       # Vector similarity search
│       ├── storage/            # DatabaseManager (connection pooling)
│       └── notifier/           # WebSocket notification sender
├── docker-compose.dev.yml      # Development orchestration
├── init.sql                    # Database schema
└── package.json                # Root npm scripts
```

## Key Entry Points

| File | Purpose |
|------|---------|
| `server/src/index.ts` | Server entry point |
| `processing-service/src/main.py` | Processing service entry |
| `client/src/app/page.tsx` | Frontend main page |
| `server/src/services/chat/chatManager.ts` | Chat orchestration logic |
| `processing-service/src/process_pipeline/processor.py` | Document processing pipeline |

## Code Conventions

### TypeScript (Server & Client)

- **File naming**: camelCase for files (`chatManager.ts`), PascalCase for components
- **Classes**: PascalCase (`LLMService`, `ChatManager`, `QueueService`)
- **Functions/variables**: camelCase
- **Constants**: UPPER_SNAKE_CASE
- **Exports**: Named exports preferred, singleton pattern for services
- **Async**: Always use async/await over raw promises
- **Error handling**: Try-catch with proper logging, centralized error middleware

### Python (Processing Service)

- **Class-based**: Components are classes (`DocumentProcessor`, `TextExtractor`, etc.)
- **Type hints**: Use Dict, List, Optional from typing
- **Logging**: Python logging module with structured output
- **Singleton**: DatabaseManager uses singleton pattern for connection pooling
- **Error handling**: Try-catch with exception re-raising

### React/Next.js (Client)

- **Client components**: Use `'use client'` directive when needed
- **State**: React hooks (useState, useEffect) - no Redux/Zustand
- **Styling**: Tailwind CSS classes
- **File upload**: react-dropzone for drag-and-drop

## Database Schema

```sql
-- Documents metadata
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    filename TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Text chunks with vector embeddings (1536 dimensions = OpenAI standard)
CREATE TABLE chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    chunk_text TEXT,
    embedding vector(1536),
    page_numbers INTEGER[],
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- IVFFlat index for cosine similarity search
CREATE INDEX chunks_embedding_idx
ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

## Environment Variables

Required variables in `.env`:

```env
# API Keys (required)
OPENAI_API_KEY=sk-...           # For embeddings (text-embedding-3-large)
ANTHROPIC_API_KEY=sk-ant-...    # For chat (Claude)

# Database
DATABASE_URL=postgres://postgres:yourpassword@postgres:5432/ragdb
DB_HOST=postgres
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_NAME=ragdb

# Queue
RABBITMQ_URL=amqp://rabbitmq:5672
RABBITMQ_QUEUE_NAME=document_processing

# Services
PROCESSING_SERVICE_URL=http://localhost:8000
UPLOADS_DIR=/app/uploads
```

## Key Classes & Interfaces

### Server (TypeScript)

```typescript
// ChatManager - Orchestrates RAG flow
class ChatManager {
  handleMessage(request: ChatRequest): Promise<ChatResponse>
  getConversationHistory(conversationId: string): ChatMessage[]
}

// LLMService - Multi-provider abstraction
class LLMService {
  generateResponse(request: LLMRequest): Promise<LLMResponse>
  setProvider(provider: 'anthropic' | 'openai'): void
}

// QueueService - RabbitMQ wrapper
class QueueService {
  sendToQueue(data: any): Promise<boolean>
}
```

### Processing Service (Python)

```python
# DocumentProcessor - Main pipeline
class DocumentProcessor:
    def process_document(self, file_id: str, file_path: str, metadata: Dict = None) -> Dict

# VectorSearch - Similarity search
class VectorSearch:
    def search(self, query: str, document_id: int = None, top_k: int = 5) -> List[Dict]

# DatabaseManager - Connection pooling (singleton)
class DatabaseManager:
    @staticmethod
    def get_instance() -> 'DatabaseManager'
    def execute_query(self, query: str, params: tuple = None) -> Any
```

## Data Flows

### Document Upload & Processing
1. User uploads PDF via Client (POST /api/document/upload)
2. Server saves file, sends job to RabbitMQ queue
3. Processing Service consumes message
4. Docling extracts text from PDF
5. Text is chunked (max 8191 tokens for embedding model)
6. OpenAI generates 1536-dim embeddings
7. Chunks stored in PostgreSQL with pgvector
8. WebSocket notification sent to client

### Chat Query
1. User sends message (POST /api/chat/chat)
2. ChatManager embeds query via OpenAI
3. Vector similarity search in PostgreSQL
4. Top-k results + conversation history = context
5. LLM (Claude/OpenAI) generates response
6. Response returned to client

## Common Tasks

### Adding a New API Endpoint (Server)
1. Create route in `server/src/api/routes/`
2. Create controller in `server/src/api/controllers/`
3. Add types in `server/src/types/`
4. Register route in `server/src/index.ts`

### Adding a New Processing Pipeline Step
1. Create module in `processing-service/src/process_pipeline/`
2. Integrate in `processor.py`
3. Add any new dependencies to `requirements/base.txt`

### Modifying Database Schema
1. Update `init.sql`
2. Recreate database: `docker-compose down -v && docker-compose up`
3. Update relevant TypeScript/Python types

## Known Issues & Gotchas

### Memory
- Processing service can OOM with large PDFs (200+ pages)
- Docling downloads ~6.5GB of OCR models on first run
- Processing service limited to 7GB in docker-compose

### No Persistence
- Conversation history is in-memory only (lost on server restart)
- No Redis or persistent session store

### Security Gaps
- No authentication/authorization implemented
- No rate limiting on API endpoints
- CORS is permissive for development

### Testing
- Limited test coverage
- Processing service has no test framework configured
- Integration tests require manual setup

## Port Reference

| Service | Port | Protocol |
|---------|------|----------|
| Client | 3500 | HTTP |
| Server | 3000 | HTTP/WebSocket |
| Processing | 8000 | HTTP |
| PostgreSQL | 5438 | TCP |
| RabbitMQ | 5672 | AMQP |
| RabbitMQ UI | 15672 | HTTP |
| PgAdmin | 5050 | HTTP |

## Related Documentation

- `README.md` - Project overview and setup
- `agents.md` - Detailed AI assistant guide
- `recommendations.md` - Architecture analysis and improvements
- `setup.md` - Development setup notes
- `notes.md` - Developer notes and decisions
