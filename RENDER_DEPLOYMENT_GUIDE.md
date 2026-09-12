# Render Deployment Guide: Cloud RAG Chatbot

This guide provides step-by-step instructions to deploy your RAG Chatbot with **Jina Embeddings**, **Groq Cloud LLM**, and **ChromaDB** to [Render](https://render.com).

---

## Prerequisites
- A **GitHub** account with your repository pushed.
- A free **Render** account at [render.com](https://render.com).
- Your API keys (already in your `.env`):
  - `JINA_API_KEY`
  - `GROQ_API_KEY`
  - `GEMINI_API_KEY`

---

## Step 1: Commit and Push Changes to GitHub

In your project terminal, run the following commands to commit the new Render configuration files:

```bash
git add .
git commit -m "Configure Jina + Groq RAG for Render deployment"
git push origin main
```

---

## Step 2: Create Web Service on Render

1. Log into your **[Render Dashboard](https://dashboard.render.com/)**.
2. Click the **"New +"** button in the top navigation and select **"Web Service"**.
3. Choose **"Build and deploy from a Git repository"** and click **Next**.
4. Select or search for your repository (`Local-RAG-LLM-Chatbot-...`) and click **Connect**.

---

## Step 3: Configure the Web Service Settings

Fill in the settings form:

| Field | Value | Notes |
| :--- | :--- | :--- |
| **Name** | `rag-chatbot` | (or any name you prefer) |
| **Region** | Closest to you (e.g., *Frankfurt*, *Oregon*, *Ohio*, *Singapore*) | Lower latency |
| **Branch** | `main` | (or your active branch) |
| **Root Directory** | *(Leave blank)* | Uses root of repository |
| **Runtime** | **Docker** *(Recommended)* OR **Python 3** | Docker is recommended for consistent C++ and SQLite libraries |

### If Choosing Docker (Recommended):
- **Dockerfile Path**: `./Dockerfile` (detected automatically)
- **Docker Context**: `.` (detected automatically)

### If Choosing Python 3 (Native):
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn --workers 1 --threads 8 --timeout 120 --bind 0.0.0.0:$PORT app:app`

---

## Step 4: Add Environment Variables

Scroll down to the **"Environment Variables"** section and click **"Add Environment Variable"** for each of the following:

| Key | Value | Description |
| :--- | :--- | :--- |
| `JINA_API_KEY` | `jina_e0e8...` | Your Jina AI API Key |
| `GROQ_API_KEY` | `gsk_Ih5U...` | Your Groq Cloud API Key |
| `GEMINI_API_KEY` | `AQ.Ab8R...` | Your Google AI API Key |
| `CHROMA_PATH` | `chroma` | ChromaDB vector store directory |
| `DATA_FOLDER` | `data` | Document storage folder |
| `PYTHON_VERSION` | `3.11.9` | *(Only required if using native Python runtime)* |

> [!TIP]
> Do NOT set `PORT` manually. Render sets this variable automatically (usually `10000`) and the application dynamically binds to it.

---

## Step 5: Choose Plan & Deploy

1. Under **Instance Type**, select **Free** ($0/month).
2. Click **"Deploy Web Service"** at the bottom of the page.

---

## Step 6: Monitor Build & Deployment Logs

Render will stream the deployment logs in real-time:
1. Docker image will build and install all dependencies.
2. Gunicorn will boot with 1 worker and 8 threads.
3. The server will run `init_app()`, which automatically indexes the seed PDFs (`data/constitution.pdf` and `data/data.pdf`) into ChromaDB using Jina v3 embeddings.
4. Render will report: `Your service is live 🎉`.
5. Click the URL at the top left of the service dashboard (e.g., `https://rag-chatbot-xxxx.onrender.com`).

---

## Free Tier Spin-Down Note
- Render's **Free Tier** spins down web services after 15 minutes of inactivity.
- On the first request after spinning down, it will take ~30–50 seconds to wake up ("cold start").
- Thanks to the startup auto-indexing routine in `app.py`, even if the container restarts, the seed documents in `data/` will automatically be ready to query immediately upon wakeup.
- To keep uploaded documents permanently across container rebuilds, you can optionally attach a **Persistent Disk** on Render (available on the Starter plan: $7/mo + $1/mo disk).
