import json
import os

from dotenv import load_dotenv
import asyncpg
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ollama import Client

# Load environment variables from .env file
load_dotenv()


app = FastAPI()

remote_host = os.getenv("REMOTE_HOST")
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
host = os.getenv("DB_HOST")
port = int(os.getenv("DB_PORT"))
database = os.getenv("DB_NAME")


class PromptRequest(BaseModel):
    prompt: str


def get_vector_data(prompt: str) -> list:
    custom_client = Client(host=remote_host, timeout=10)
    embedding_result = custom_client.embeddings(model="nomic-embed-text", prompt=prompt)
    return embedding_result["embedding"]


async def connect_to_db() -> asyncpg.Connection:
    return await asyncpg.connect(
        user=user,
        password=password,
        host=host,
        port=port,
        database=database,
    )


@app.post("/get-videos/")
async def get_videos(request: PromptRequest) -> list:
    prompt = request.prompt
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    connection = await connect_to_db()
    if connection is None or connection.is_closed():
        raise HTTPException(status_code=500, detail="Connection to database failed")

    try:
        query_vector = json.dumps(get_vector_data(prompt))

        select_query = 'SELECT * FROM public."video_gpt" ORDER BY embedding <-> $1 LIMIT 2'
        results = await connection.fetch(select_query, query_vector)

        response = []
        for result in results:
            title = result["title"]
            youtube_link = f'https://youtu.be/{result["videoid"]}&t={result["seconds"]}'
            response.append({"title": title, "youtube_link": youtube_link, "summary": result["summary"]})

        return response
    finally:
        await connection.close()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
