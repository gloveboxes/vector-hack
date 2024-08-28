import asyncpg
import asyncio
from ollama import Client
import json

remote_host = "http://hub:11434"
user = "postgres"
password = "M1cr0s0ft"
host = "rpi58"
port = 5432
database = "vector-hack"


def get_vector_data(prompt: str):
    custom_client = Client(host=remote_host, timeout=10)
    embedding_result = custom_client.embeddings(model="nomic-embed-text", prompt=prompt)
    return embedding_result["embedding"]


async def connect_to_db():
    # Connect to the PostgreSQL database
    connection = await asyncpg.connect(
        user=user,
        password=password,
        host=host,
        port=port,
        database=database,
    )

    if connection is None or connection.is_closed():
        print("Connection failed")
        return

    print("Connection successful")

    while True:
        prompt = input("Enter a prompt: ")
        if prompt == "exit":
            break
        if prompt is None or prompt == "":
            continue

        vector = json.dumps(get_vector_data(prompt))

        select_query = 'SELECT * FROM public."video_gpt" ORDER BY embedding <-> $1 LIMIT 2'
        results = await connection.fetch(select_query, vector)

        for result in results:
            # https://youtu.be/_G-PDO7OERE?si=bbukKnSBAekuaYzB&t=1123
            title = result["title"]
            youtube_id = f'https://youtu.be/{result["videoid"]}&t={result["seconds"]}'
            print(title)
            print(youtube_id)

    await connection.close()


# summarize_text("hdghdghdg")


# Run the async function
asyncio.run(connect_to_db())
