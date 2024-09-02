import os
from typing import Any, AsyncGenerator, List

from dotenv import load_dotenv
import asyncpg
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager

from ollama import Client

# Load environment variables from .env file
load_dotenv()


OLLAMA_EMBEDDING_ENDPOINT = os.getenv("OLLAMA_EMBEDDING_ENDPOINT")
POSTGRES_CONNECTION_STRING = os.getenv("POSTGRES_CONNECTION_STRING")
EMBEDDING_MODEL = "nomic-embed-text"


class PromptRequest(BaseModel):
    prompt: str


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[Any, Any]:
    app.state.db_connection = await asyncpg.connect(POSTGRES_CONNECTION_STRING)
    try:
        yield
    finally:
        await app.state.db_connection.close()


app = FastAPI(lifespan=lifespan)


def get_vector_data(prompt: str) -> List[float]:
    custom_client = Client(host=OLLAMA_EMBEDDING_ENDPOINT, timeout=10)
    embedding_result = custom_client.embeddings(model=EMBEDDING_MODEL, prompt=prompt)
    return embedding_result["embedding"]


async def connect_to_db() -> asyncpg.Connection:
    return await asyncpg.connect(POSTGRES_CONNECTION_STRING)


@app.post("/get-videos/")
async def get_videos(request: PromptRequest) -> list:
    if not request.prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    connection = app.state.db_connection
    if connection is None or connection.is_closed():
        raise HTTPException(status_code=500, detail="Connection to database failed")

    try:
        vector = get_vector_data(request.prompt)
        vector_string = f"[{', '.join(map(str, vector))}]"

        select_query = """
        SELECT *, embedding <-> $1::vector AS distance 
        FROM public.video_gpt 
        ORDER BY distance 
        LIMIT 3
        """

        results = await connection.fetch(select_query, vector_string)

        return [
            {
                "title": result["title"],
                "distance": result["distance"],
                "youtube_link": f'https://youtu.be/{result["videoid"]}&t={result["seconds"]}',
                "text": result["text"]
            }
            for result in results
        ]
    
    except Exception as e:
        print(f"An error occurred while fetching data: {e}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
