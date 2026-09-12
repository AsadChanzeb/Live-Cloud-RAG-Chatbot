# Transition Plan: Local RAG to Live Public Deployment (Jina + Groq + ChromaDB)

This document outlines the audit findings of the existing codebase, required API credentials and their free-tier limits, and the step-by-step implementation plan to transition the chatbot from local Ollama to cloud-hosted APIs (Jina Embeddings + Groq LLM) with persistent vector storage ready for cloud deployment.

---

## 1. Codebase Audit: Ollama & ChromaDB References

### Places Where Ollama Is Called
1. **[get_embedding_function.py](file:///d:/Rag%20Live/get_embedding_function.py#L1-L8)**:
   - Line 1: `from langchain_ollama import OllamaEmbeddings`
   - Lines 5–7: `embeddings = OllamaEmbeddings(model="nomic-embed-text")` — local Ollama embedding function.
2. **[query_data.py](file:///d:/Rag%20Live/query_data.py#L7-L109)**:
   - Line 7: `from langchain_ollama import OllamaLLM`
   - Lines 96–109: Fallbacks in `_get_model()` instantiate `OllamaLLM(model="mistral")` and `OllamaLLM(model="llama3.2:3b")`.
   - Lines 63, 135, 174, 187, 211: Default model argument set to `"llama3.2:3b"`.
3. **[app.py](file:///d:/Rag%20Live/app.py#L41-L55)**:
   - Line 41: `model_name = data.get('model', 'mistral').strip()`
   - Line 55: `model_name = request.args.get('model', 'mistral').strip()`
4. **[index.html](file:///d:/Rag%20Live/index.html#L886-L890)**:
   - Lines 886–889: `<optgroup label="🖥️ Local (Ollama)">` with options for `mistral` and `llama3.2:3b`.
5. **[requirements.txt](file:///d:/Rag%20Live/requirements.txt#L8)**:
   - Line 8: `langchain-ollama`

### Places Where ChromaDB Is Initialized / Queried
1. **[populate_database.py](file:///d:/Rag%20Live/populate_database.py#L8-L110)**:
   - Line 8: `from langchain_chroma import Chroma`
   - Line 10: `CHROMA_PATH = "chroma"` (hardcoded local path)
   - Lines 55–58: `Chroma(persist_directory=CHROMA_PATH, embedding_function=get_embedding_function())`
   - Line 62: `db.get(include=[])`
   - Line 70: `db.add_documents(new_chunks, ids=[...])`
   - Line 109–110: `shutil.rmtree(CHROMA_PATH)` in `clear_database()`
2. **[query_data.py](file:///d:/Rag%20Live/query_data.py#L5-L120)**:
   - Line 5: `from langchain_chroma import Chroma`
   - Line 15: `CHROMA_PATH = "chroma"` (hardcoded local path)
   - Lines 56–59: `Chroma(persist_directory=CHROMA_PATH, embedding_function=_embedding_function)`
   - Line 120: `_db._client.clear_system_cache()`
   - Line 143: `db.similarity_search_with_score(query_text, k=k)`
3. **[app.py](file:///d:/Rag%20Live/app.py#L8-L130)**:
   - Calls `add_single_file_to_chroma()`, `clear_database()`, and `invalidate_db_cache()`
   - Uses local `DATA_FOLDER = 'data'` for uploaded PDF documents.

---

## 2. Required Credentials, Signups & Free-Tier Limits

Before making live changes or deploying, you will need to obtain the following credentials:

| Service | Credential Name | Where to Sign Up & Get Key | Free-Tier Quota & Limits |
| :--- | :--- | :--- | :--- |
| **Jina AI** | `JINA_API_KEY` | [jina.ai/embeddings](https://jina.ai/embeddings) → Log in / Sign up → "API Keys" → Generate Key | **1,000,000 Free Tokens** upon signup. No credit card required. Free tier rate limit: up to 500 RPM. |
| **Groq Cloud** | `GROQ_API_KEY` | [console.groq.com/keys](https://console.groq.com/keys) → Log in / Sign up → "Create API Key" | **100% Free Developer Tier**. For `llama-3.1-8b-instant`: **30 Requests/min**, **14,400 Requests/day**, **6,000 Tokens/min**. |
| **Google AI Studio** *(Optional / Backup)* | `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com/app/apikey) → "Create API Key" | **Free Tier**: 15 RPM, 1,500 RPD for Gemini 2.0 Flash. (Already present in your `.env`). |
| **Render** or **Railway** | Account Signup | [render.com](https://render.com) or [railway.com](https://railway.com) | **Render**: Free tier Web Service (spins down after 15 min idle; persistent disks require paid Starter $7/mo + $1/mo disk).<br>**Railway**: $5 one-time free credit, supports Persistent Volumes directly attached to folders without tier gating. |

> [!IMPORTANT]
> **Vector Dimension Mismatch Notice**:
> Ollama's `nomic-embed-text` creates 768-dimensional vectors, whereas Jina's `jina-embeddings-v3` creates 1024-dimensional vectors. When we switch to Jina, any existing ChromaDB index created locally with Ollama will fail with a dimension mismatch if queried directly. The database will need to be cleared and re-indexed using Jina.

---

## 3. Proposed Changes

### Configuration & Dependencies
#### [MODIFY] [requirements.txt](file:///d:/Rag%20Live/requirements.txt)
- Add `langchain-groq` (official Groq LangChain integration) and `gunicorn` (production WSGI server for Flask).
- Ensure `langchain-community`, `langchain-chroma`, and `python-dotenv` are kept.
- Keep `langchain-ollama` optional or remove it from mandatory production installs.

#### [NEW] [.env.example](file:///d:/Rag%20Live/.env.example)
- Provide a clean template with all configuration keys:
  ```bash
  JINA_API_KEY=your_jina_api_key_here
  GROQ_API_KEY=your_groq_api_key_here
  GEMINI_API_KEY=your_gemini_api_key_here
  CHROMA_PATH=chroma
  DATA_FOLDER=data
  PORT=8000
  ```

---

### Embeddings Layer
#### [MODIFY] [get_embedding_function.py](file:///d:/Rag%20Live/get_embedding_function.py)
- Replace `OllamaEmbeddings` with `JinaEmbeddings(model_name="jina-embeddings-v3", jina_api_key=...)`.
- Pull `JINA_API_KEY` from `os.getenv("JINA_API_KEY")` with friendly validation error if missing.

---

### Inference & RAG Query Layer
#### [MODIFY] [query_data.py](file:///d:/Rag%20Live/query_data.py)
- Make `CHROMA_PATH` configurable via `os.getenv("CHROMA_PATH", "chroma")`.
- Integrate `ChatGroq` using `GROQ_API_KEY` and set `llama-3.1-8b-instant` as the default model.
- Keep existing prompt template, retrieval logic (`k=2`), score normalization, and SSE streaming untouched.
- Support both Groq and Gemini models seamlessly.

---

### Database Population Layer
#### [MODIFY] [populate_database.py](file:///d:/Rag%20Live/populate_database.py)
- Read `CHROMA_PATH` from `os.getenv("CHROMA_PATH", "chroma")`.
- Read `DATA_PATH` from `os.getenv("DATA_FOLDER", "data")`.
- Automatically create directories if they do not exist.

---

### Application & API Layer
#### [MODIFY] [app.py](file:///d:/Rag%20Live/app.py)
- Update default model to `llama-3.1-8b-instant`.
- Read `DATA_FOLDER` from `os.getenv("DATA_FOLDER", "data")`.
- Support cloud port binding `os.getenv("PORT", 8000)`.

---

### Frontend UI
#### [MODIFY] [index.html](file:///d:/Rag%20Live/index.html)
- Update the `<select id="modelSelector">` to showcase **Groq (Ultra-Fast Cloud)** with options:
  - `llama-3.1-8b-instant` (Default, Blazing Fast)
  - `llama-3.3-70b-versatile` (Smart & Accurate)
- Keep Gemini group as secondary option.
- Remove obsolete local Ollama options that won't function on public cloud hosts.

---

## 4. Verification Plan

### Local Verification (Automated & Manual)
1. **Syntax & Import Check**: Verify all modified scripts compile without error.
2. **Embedding Verification**: Verify `get_embedding_function()` successfully creates a `JinaEmbeddings` instance with `model_name="jina-embeddings-v3"`.
3. **Groq Model Verification**: Run a test query with `ChatGroq` or query pipeline to ensure token streaming and completion function properly.
4. **ChromaDB Path Configuration**: Test running `populate_database.py` and `query_data.py` with custom `CHROMA_PATH` environment variable.
5. **Web Server Verification**: Run Flask app and verify `/api/documents`, `/api/query/stream`, and static file serving.

---

## 5. Next Step & Confirmation

Per requirement #8: **We will not deploy or push anything without confirming each required key with you first.**

Please review the required credentials above. Do you have your **Jina API key** and **Groq API key** ready, and which deployment platform (**Render** or **Railway**) do you prefer for the step-by-step deployment guide?
