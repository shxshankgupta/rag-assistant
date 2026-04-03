🚀 RAG Assistant (Local LLM + Production-Ready RAG System)

An end-to-end Retrieval-Augmented Generation (RAG) system built with FastAPI.
Upload PDFs → auto-chunk & embed → query with streaming AI answers using local LLM (Ollama) or optional cloud providers.

⸻

🧠 Overview

RAG Assistant is a full-stack AI system that:
	•	📄 Accepts PDF uploads
	•	⚙️ Processes documents asynchronously (Celery + Redis)
	•	🧠 Generates embeddings and stores them in FAISS
	•	🔍 Retrieves relevant context using vector search
	•	🤖 Generates answers using:
	•	Local LLM (Ollama – Qwen2.5) ✅ (default)
	•	OpenAI (optional)

Designed to demonstrate real-world AI architecture + scalable backend design.

⸻

🏗️ Architecture

Upload PDF → Celery Processing → Chunking → Embeddings → FAISS Store
→ User Query → Vector Search → Context Retrieval → LLM (Ollama/OpenAI)
→ Streaming Response → UI


⸻

⚙️ Tech Stack

🖥️ Frontend
	•	Next.js (App Router)
	•	TypeScript
	•	Tailwind CSS

🔧 Backend
	•	FastAPI
	•	Celery (Background Tasks)
	•	Redis (Queue + Caching)
	•	SQLite / PostgreSQL

🧠 AI / ML
	•	FAISS (Vector Store)
	•	Ollama (Local LLM)
	•	Qwen2.5 (3B / 7B)
	•	OpenAI (optional fallback)

⸻

✨ Features
	•	📄 Upload PDF documents
	•	⚡ Async document processing (Celery)
	•	🧠 Semantic search with FAISS
	•	🤖 Local LLM (no API cost)
	•	🔄 Streaming responses (SSE)
	•	🔐 JWT Authentication
	•	📊 Document processing status tracking
	•	🔍 Multi-document querying

⸻

📂 Project Structure

rag-assistant/
├── app/                # FastAPI backend
├── frontend/           # Next.js frontend
├── workers/            # Celery workers
├── core/               # Config & settings
├── services/           # RAG pipeline logic
└── vector_store/       # FAISS integration


⸻

🚀 Getting Started (Local Setup)

1️⃣ Clone the repo

git clone <your-repo>
cd rag-assistant


⸻

2️⃣ Backend setup

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt


⸻

3️⃣ Start services

Start Redis

redis-server

Start Celery worker

celery -A app.workers.celery_app:celery_app worker --loglevel=info --pool=solo

Start FastAPI

uvicorn app.main:app --reload


⸻

🤖 Local LLM Setup (Ollama)

Install Ollama

https://ollama.com

Start Ollama

ollama serve
ollama pull qwen2.5:3b

Environment config

OLLAMA_MODEL=qwen2.5:3b

👉 Now all queries will run fully locally (no API cost)

⸻

🌐 Frontend Setup

cd frontend
npm install
npm run dev

Open:
👉 http://localhost:3000

⸻

🔐 Environment Variables

Backend (.env)

SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///./rag.db
REDIS_URL=redis://localhost:6379/0

# Local LLM
OLLAMA_MODEL=qwen2.5:3b

# Optional (only if using OpenAI)
OPENAI_API_KEY=

Frontend (.env.local)

NEXT_PUBLIC_API_URL=http://127.0.0.1:8000


⸻

🧪 Usage
	1.	Open http://localhost:3000
	2.	Register / Login
	3.	Upload a PDF
	4.	Wait for processing
	5.	Ask questions
	6.	Get AI-generated answers 🎯

⸻

📡 API Highlights

Streaming Query (SSE)

POST /api/v1/query/stream

Events:

data: {"type": "sources", ...}
data: {"type": "token", "content": "..."}
data: {"type": "done"}
data: [DONE]


⸻

⚠️ Notes
	•	First query may be slow (model warmup)
	•	Works best with 8GB+ RAM
	•	Local inference avoids API cost
	•	Can be switched to OpenAI easily

⸻

🚀 Deployment

Frontend
	•	Deploy on Vercel

Backend

Requires:
	•	Redis
	•	Celery worker
	•	Ollama (or OpenAI)

⸻

🎯 Future Improvements
	•	Cloud LLM integration (Groq / OpenRouter)
	•	Chat memory support
	•	Multi-file formats (DOCX, TXT)
	•	Better UI/UX
	•	Performance optimizations

⸻

🙌 Author

Shashank

Built as a full-stack AI system to demonstrate RAG architecture, async processing, and local LLM integration.

⸻

⭐ Support

If you like this project, give it a ⭐ on GitHub!
:::

⸻

