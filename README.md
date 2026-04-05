🚀 RAG Assistant — Production-Ready AI Document Query System

An end-to-end Retrieval-Augmented Generation (RAG) system that enables users to upload documents and query them using AI with real-time streaming responses.

🔗 Live Demo: https://rag-assistant-ruddy.vercel.app
⚡ Backend API: https://rag-assistant-ecwy.onrender.com

⸻

🧠 Overview

RAG Assistant is a full-stack AI system that:
	•	📄 Accepts PDF uploads
	•	⚙️ Processes documents asynchronously
	•	🧠 Generates embeddings and stores them in FAISS
	•	🔍 Retrieves relevant context using vector search
	•	🤖 Generates answers using LLM (Groq / Local models)
	•	⚡ Streams responses in real-time

⸻

🏗️ Architecture

PDF Upload → Chunking → Embeddings → FAISS → Query → Retrieval → LLM → Streaming Response → UI

⸻

⚙️ Tech Stack

Frontend: Next.js, TypeScript, Tailwind CSS
Backend: FastAPI, Async APIs, SQLite (Postgres-ready)
AI/ML: FAISS, Sentence Transformers, Groq
Deployment: Render (Backend), Vercel (Frontend)

⸻

✨ Features
	•	PDF upload and processing
	•	Real-time streaming responses
	•	Semantic search with FAISS
	•	Multi-document querying
	•	JWT authentication
	•	Document status tracking
	•	Sub-second query latency

⸻

📸 Demo Flow
	1.	User logs in
	2.	Uploads PDF
	3.	System processes document
	4.	User asks question
	5.	AI returns contextual answer

⸻

📂 Project Structure

rag-assistant/
├── app/ (FastAPI backend)
├── frontend/ (Next.js frontend)
├── services/ (RAG logic)
├── core/ (config)
└── data/ (uploads + FAISS)

⸻

🚀 Local Setup

Backend setup:
Create virtual env → install requirements → run FastAPI

Frontend setup:
Go to frontend folder → install dependencies → run dev server

⸻

🔐 Environment Variables

Backend:
SECRET_KEY, DATABASE_URL, ALLOWED_ORIGINS

Frontend:
NEXT_PUBLIC_API_URL

⸻

📡 API

POST /api/v1/query/stream → returns streaming tokens + sources

⸻

⚡ Performance
	•	~700ms response latency
	•	Efficient FAISS retrieval
	•	Lightweight embeddings
	•	Streaming UX

⸻

🎯 Future Improvements
	•	Chat memory
	•	Multi-format docs
	•	UI improvements
	•	Hybrid search

⸻

🙌 Author

Shashank Gupta

Built to demonstrate production-ready AI systems and RAG architecture

⸻

⭐ Support

If you like this project, give it a ⭐

⸻