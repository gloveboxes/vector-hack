import asyncio
import json
import asyncpg

user = "postgres"
password = "M1cr0s0ft"
host = "homehub"
port = 5434
database = "vector-hack"


async def load():
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

    master = json.load(open("master_enriched.json"))

    for r in master:
        insert_query = 'INSERT INTO public."video_gpt" (embedding, speaker, title, videoId, description, start, seconds, text, summary) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)'
        embedding = json.dumps(r["ada_v2"])
        speaker = r["speaker"]
        title = r["title"]
        videoId = r["videoId"]
        description = r["description"]
        start = r["start"]
        seconds = r["seconds"]
        text = r["text"]
        summary = r["summary"]

        await connection.execute(
            insert_query,
            embedding,
            speaker,
            title,
            videoId,
            description,
            start,
            seconds,
            text,
            summary,
        )


asyncio.run(load())
