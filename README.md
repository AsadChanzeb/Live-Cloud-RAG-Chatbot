# ⚡ Live Cloud RAG Chatbot

[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-FF6F00?style=for-the-badge)](https://www.trychroma.com/)
[![Jina AI](https://img.shields.io/badge/Jina_AI-Embeddings_v3-009688?style=for-the-badge)](https://jina.ai/)
[![Groq](https://img.shields.io/badge/Groq-Llama_3.3_70B-F55036?style=for-the-badge)](https://groq.com/)
[![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Render](https://img.shields.io/badge/Render-Cloud_Ready-46E3B7?style=for-the-badge&logo=render&logoColor=black)](https://render.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg?style=for-the-badge)](https://github.com/AsadChanzeb/Live-Cloud-RAG-Chatbot)

A modern, high-performance **Retrieval-Augmented Generation (RAG)** web application and conversational assistant. Powered by **Jina AI Embeddings v3**, **ChromaDB vector database**, and **Groq Cloud LLMs (Llama 3.3 70B)** with real-time Server-Sent Events (SSE) streaming and a glassmorphism web interface.

---

## 📑 Table of Contents

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [Key Features](#-key-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Quickstart Guide](#-quickstart-guide)
  - [1. Prerequisites](#1-prerequisites)
  - [2. Clone & Setup Virtual Environment](#2-clone--setup-virtual-environment)
  - [3. Configure Environment Variables](#3-configure-environment-variables)
  - [4. Index Knowledge Base](#4-index-knowledge-base)
  - [5. Run the Application](#5-run-the-application)
- [CLI Usage](#-cli-usage)
- [API Reference](#-api-reference)
- [Docker Deployment](#-docker-deployment)
- [Deploy to Render Cloud](#-deploy-to-render-cloud)
- [License](#-license)

---

## 🌟 Overview

This project provides an end-to-end RAG workflow optimized for speed, low resource consumption, and seamless cloud deployment:
1. **Document Ingestion**: Extracts text from PDF documents using `PyPDFDirectoryLoader`, splits text into context-aware chunks with deterministic chunk IDs.
2. **Vector Embeddings**: Generates dense semantic embeddings using **Jina Embeddings v3** via cloud API (no heavy local transformer models required in memory).
3. **Similarity Search**: Queries **ChromaDB** using Cosine similarity with relevance score filtering.
4. **LLM Generation**: Streams context-grounded answers through ultra-low latency **Groq API** (Llama 3.3 70B / Compound Mini) or **Google Gemini**.
5. **Modern Interface**: A sleek, responsive, glassmorphic UI featuring live SSE streaming, Markdown rendering, copy actions, and document management.

---

## 🏗 System Architecture

```
                                  ┌───────────────────────────────┐
                                  │      Client Web Browser       │
                                  │   (Glassmorphic UI / SSE)     │
                                  └──────────────┬────────────────┘
                                                 │
                             HTTP / JSON & SSE   │  POST /api/upload (PDFs)
                                                 ▼
                             ┌───────────────────────────────────────┐
                             │       Flask Web Server (app.py)       │
                             └───────────┬───────────────┬───────────┘
                                         │               │
                     Vector Similarity   │               │ Document Chunking
                           Query         │               │ & Indexing
                                         ▼               ▼
                 ┌────────────────────────────────────────────────────────┐
                 │                   ChromaDB Vector Store                │
                 │                    (Local / Persistent)                │
                 └───────────────────────────────┬────────────────────────┘
                                                 │
                                                 │ Dense Vector Generation
                                                 ▼
                               ┌───────────────────────────────────┐
                               │       Jina AI Embeddings v3       │
                               │        (Cloud API Service)        │
                               └───────────────────────────────────┘
                                                 │
                                                 ▼ Retrieved Context + Prompt
                               ┌───────────────────────────────────┐
                               │           Groq Cloud LLM          │
                               │  (Llama-3.3-70b / Compound-Mini)  │
                               │      (Optional: Gemini 1.5)       │
                               └─────────────────┬─────────────────┘
                                                 │
                                                 ▼ Real-time Stream
                                  ┌───────────────────────────────┐
                                  │   SSE Tokens back to Client   │
                                  └───────────────────────────────┘
```

---

## ✨ Key Features

- **⚡ Blazing Fast Streaming Responses**: Real-time token streaming using Server-Sent Events (`/api/query/stream`).
- **🧠 Cloud Embeddings via Jina AI**: Eliminates heavy local PyTorch dependencies; lightweight footprint for fast cloud booting.
- **🚀 High-Speed LLM Inference via Groq**: Integrated with Groq's LPU inference engine for rapid responses.
- **📄 Dynamic Document Management**:
  - Drag-and-drop PDF upload directly in UI (`/api/upload`).
  - Single-file incremental indexing without re-processing previous documents.
  - Reset & clear database functionality.
- **🎯 Deterministic Chunk Deduplication**: Unique chunk IDs (`source:page:chunk_index`) prevent duplicate vector storage when re-indexing.
- **💻 CLI & Web Interfaces**: Full support for both terminal-based interactive queries and browser GUI.
- **🐳 Production Ready**: Complete Dockerfile, `.dockerignore`, `render.yaml` blueprint, and Gunicorn WSGI configuration.

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | [Flask](https://flask.palletsprojects.com/) (Python 3.11) + Gunicorn |
| **LLM Orchestration** | [LangChain](https://www.langchain.com/) (`langchain-core`, `langchain-community`, `langchain-chroma`) |
| **LLM Provider** | [Groq Cloud](https://groq.com/) (`llama-3.3-70b-versatile`, `groq/compound-mini`) & [Google Gemini](https://aistudio.google.com/) |
| **Embeddings** | [Jina AI](https://jina.ai/) (`jina-embeddings-v3`) |
| **Vector Database** | [ChromaDB](https://www.trychroma.com/) |
| **Document Processing**| [PyPDF](https://pypdf.readthedocs.io/) & LangChain Text Splitters |
| **Frontend UI** | HTML5, Vanilla CSS (Glassmorphism), JavaScript (EventSource SSE) |
| **Deployment** | Docker & Render Web Service |

---

## 📁 Project Structure

```bash
Live-Cloud-RAG-Chatbot/
├── app.py                     # Flask application entry point & API endpoints
├── query_data.py              # RAG query pipeline, ChromaDB retrieval & Groq LLM streaming
├── populate_database.py       # PDF loader, text splitter, and ChromaDB vector indexing
├── get_embedding_function.py  # Jina AI embedding function initialization
├── index.html                 # Modern glassmorphism single-page UI
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Multi-stage production container configuration
├── render.yaml                # Render Infrastructure-as-Code blueprint
├── .env.example               # Environment variable template
├── .gitignore                 # Git ignore rules for virtual environments, secrets & databases
├── data/                      # PDF knowledge base source files
│   ├── constitution.pdf
│   └── data.pdf
└── chroma/                    # ChromaDB vector store (generated on indexing)
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites

- **Python 3.11+** installed
- **Jina AI API Key**: Get a free API key at [jina.ai/embeddings](https://jina.ai/embeddings)
- **Groq Cloud API Key**: Get a free API key at [console.groq.com](https://console.groq.com/keys)
- *(Optional)* **Google Gemini API Key**: [aistudio.google.com](https://aistudio.google.com)

### 2. Clone & Setup Virtual Environment

```bash
# Clone the repository
git clone https://github.com/AsadChanzeb/Live-Cloud-RAG-Chatbot.git
cd Live-Cloud-RAG-Chatbot

# Create and activate a virtual environment
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
```

### 3. Configure Environment Variables

Create a `.env` file in the root directory:

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```env
# Required API Keys
JINA_API_KEY=jina_xxxxxxxxxxxxxxxxxxxxxxxx
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx

# Optional Fallback Key
GEMINI_API_KEY=your_gemini_api_key_here

# Storage Paths
CHROMA_PATH=chroma
DATA_FOLDER=data

# Port
PORT=8000
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

### 4. Index Knowledge Base

Place your `.pdf` documents into the `data/` directory and run:

```bash
python populate_database.py
```

To clear and rebuild the database from scratch:

```bash
python populate_database.py --reset
```

### 5. Run the Application

Start the web server locally:

```bash
python app.py
```

Open your browser and navigate to:
```
http://localhost:8000
```

---

## 💻 CLI Usage

You can query the RAG system directly from your command line:

```bash
# Run a one-off query
python query_data.py --query "What are the main rights outlined in the constitution?"

# Specify a custom model
python query_data.py --query "Summarize the document" --model "llama-3.3-70b-versatile"
```

---

## 🔌 API Reference

### `GET /`
Serves the single-page web user interface.

### `POST /api/query`
Standard JSON query endpoint.
- **Request Body**:
  ```json
  {
    "query": "What is the primary topic of the document?",
    "model": "groq/compound-mini"
  }
  ```
- **Response**:
  ```json
  {
    "response": "The document outlines...",
    "sources": ["data/constitution.pdf:2:0"]
  }
  ```

### `GET /api/query/stream`
Server-Sent Events (SSE) streaming endpoint.
- **Query Parameters**: `query=<text>&model=<model_name>`
- **Stream Events**:
  - `data: {"chunk": "Hello"}`
  - `data: {"chunk": " world!"}`
  - `event: done`, `data: {"sources": [...]}`

### `POST /api/upload`
Uploads and indexes a new PDF document.
- **Form Data**: `file` (multipart/form-data, `.pdf` only, max 50MB)
- **Response**: `{"success": true, "message": "Uploaded and indexed 'report.pdf' (12 chunks)."}`

### `GET /api/documents`
Lists all active indexed PDF files in the knowledge base.

### `POST /api/reset`
Clears ChromaDB vectors and removes uploaded PDF files.

---

## 🐳 Docker Deployment

Build and run the container locally:

```bash
# Build the Docker image
docker build -t rag-chatbot:latest .

# Run container with environment variables
docker run -d -p 8000:8000 \
  -e JINA_API_KEY="your_jina_key" \
  -e GROQ_API_KEY="your_groq_key" \
  --name rag-live rag-chatbot:latest
```

Access the service at `http://localhost:8000`.

---

## ☁️ Deploy to Render Cloud

### Option 1: Render Blueprint (Recommended)
1. Fork or push this repository to your GitHub account.
2. Log into [Render Dashboard](https://dashboard.render.com/).
3. Click **New +** → **Blueprint**.
4. Connect this repository; Render will read [`render.yaml`](file:///d:/Rag%20Live/render.yaml).
5. Set your `JINA_API_KEY` and `GROQ_API_KEY` in the environment variables prompt.
6. Click **Apply** to deploy!

### Option 2: Docker Web Service on Render
1. Create a new **Web Service** on Render.
2. Connect your repository and select **Docker** environment.
3. Add `JINA_API_KEY` and `GROQ_API_KEY` under **Environment Variables**.
4. Deploy!

For in-depth deployment steps and troubleshooting, see [RENDER_DEPLOYMENT_GUIDE.md](file:///d:/Rag%20Live/RENDER_DEPLOYMENT_GUIDE.md).

---

## 📄 License

This project is licensed under the MIT License. Feel free to use, modify, and distribute for personal and commercial projects.
