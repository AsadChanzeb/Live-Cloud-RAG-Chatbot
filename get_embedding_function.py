import os
from dotenv import load_dotenv
from langchain_community.embeddings import JinaEmbeddings

load_dotenv()


def get_embedding_function():
    api_key = os.getenv("JINA_API_KEY")
    if not api_key:
        raise ValueError(
            "JINA_API_KEY is not set. Please add it to your .env file or environment variables."
        )
    embeddings = JinaEmbeddings(
        jina_api_key=api_key,
        model_name="jina-embeddings-v3",
    )
    return embeddings

