import argparse
import json
import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from get_embedding_function import get_embedding_function

load_dotenv()

CHROMA_PATH = os.getenv("CHROMA_PATH", "chroma")
os.makedirs(CHROMA_PATH, exist_ok=True)

# Groq API Base URL
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "groq/compound-mini"

PROMPT_TEMPLATE = """
Answer the question based on the following context. If the context does not explicitly contain the answer but is related, you can use your general knowledge to construct a helpful response, but make sure to state what information comes from the context and what comes from general knowledge.

Context:
{context}

---

Question: {question}
"""

# ─── Module-level singletons (created once, reused every query) ───────────────
_embedding_function = None
_db = None
_models = {}


def _is_gemini(model_name: str) -> bool:
    """Return True if the model name should be routed to the Google Gemini API."""
    return "gemini" in model_name.lower()


def _is_chat_model(model_name: str) -> bool:
    """All active cloud models (Groq, Gemini) return ChatMessage with .content."""
    return True


def _get_db():
    """Return cached Chroma DB connection — only opens once per process."""
    global _db, _embedding_function
    if _db is None:
        _embedding_function = get_embedding_function()
        _db = Chroma(
            persist_directory=CHROMA_PATH,
            embedding_function=_embedding_function
        )
    return _db


def _get_model(model_name: str = DEFAULT_MODEL):
    """Return cached model instance by name.
    - Gemini models → Google Generative AI API
    - Other models  → Groq API (Ultra-fast cloud inference)
    """
    global _models
    if model_name not in _models:
        if _is_gemini(model_name):
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError(
                    "GEMINI_API_KEY is not set. Add it to your .env file: GEMINI_API_KEY=AIza..."
                )
            _models[model_name] = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=0.7,
                streaming=True,
            )
        else:
            # Route to Groq API
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError(
                    "GROQ_API_KEY is not set. Add it to your .env file: GROQ_API_KEY=gsk_..."
                )
            _models[model_name] = ChatOpenAI(
                model=model_name,
                api_key=api_key,
                base_url=GROQ_BASE_URL,
                temperature=0.3,
                streaming=True,
            )
    return _models[model_name]



def invalidate_db_cache():
    """Call this after adding new documents so the DB reloads fresh."""
    global _db
    if _db is not None:
        try:
            # Release the underlying Chroma client so Windows file locks are freed
            if hasattr(_db, '_client'):
                _db._client.clear_system_cache()
            del _db
        except Exception:
            pass
        import gc
        gc.collect()
    _db = None


# ──────────────────────────────────────────────────────────────────────────────

def warm_up():
    """Warm up cached DB and default model at server startup."""
    try:
        _get_db()
        _get_model(DEFAULT_MODEL)
    except Exception as e:
        print(f"Warm up notice: {e}")


def _build_prompt(query_text: str, k: int = 2):
    """Shared retrieval + prompt build used by all query functions."""
    db = _get_db()
    results = db.similarity_search_with_score(query_text, k=k)
    context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(context=context_text, question=query_text)
    return prompt, results


def _extract_text(content) -> str:
    """Extract clean string text from ChatMessage content (handles string, list of dicts, etc.)."""
    if not content:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if item.get("type") == "text" and "text" in item:
                    parts.append(item["text"])
                elif "text" in item:
                    parts.append(str(item["text"]))
            elif hasattr(item, "text"):
                parts.append(str(item.text))
        return "".join(parts)
    if hasattr(content, "text"):
        return str(content.text)
    return str(content)


def query_rag(query_text: str, model_name: str = DEFAULT_MODEL):
    """Simple query — returns plain text response."""
    prompt, results = _build_prompt(query_text)
    model = _get_model(model_name)
    response_text = _extract_text(model.invoke(prompt).content)
    sources = [doc.metadata.get("id", None) for doc, _score in results]
    print(f"Response: {response_text}\nSources: {sources}")
    return response_text


def query_rag_detailed(query_text: str, model_name: str = DEFAULT_MODEL):
    """Returns response + structured source metadata for the UI."""
    prompt, results = _build_prompt(query_text)
    model = _get_model(model_name)
    response_text = _extract_text(model.invoke(prompt).content)

    sources = [
        {
            "id": doc.metadata.get("id"),
            "content": doc.page_content,
            "score": float(_score)
        }
        for doc, _score in results
    ]

    return {
        "response": response_text,
        "sources": sources
    }


def query_rag_stream(query_text: str, model_name: str = DEFAULT_MODEL):
    """
    SSE generator — streams tokens then sends a final sources event.
    Compatible with EventSource on the frontend.
    Supports Groq and Gemini cloud models.
    """
    prompt, results = _build_prompt(query_text)
    model = _get_model(model_name)

    # Stream tokens
    for chunk in model.stream(prompt):
        token = _extract_text(chunk.content)
        if token:
            yield f"data: {json.dumps({'token': token})}\n\n"

    # Send sources after streaming completes
    sources = [
        {
            "id": doc.metadata.get("id"),
            "content": doc.page_content,
            "score": float(_score)
        }
        for doc, _score in results
    ]
    yield f"event: sources\ndata: {json.dumps({'sources': sources})}\n\n"
    yield "event: done\ndata: {}\n\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query_text", type=str, help="The query text.")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Model name (e.g. groq/compound-mini, llama-3.1-8b-instant, gemini-2.0-flash)")
    args = parser.parse_args()
    query_rag(args.query_text, args.model)



if __name__ == "__main__":
    main()
