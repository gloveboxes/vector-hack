import os
from pathlib import Path
import asyncio
import json
import asyncpg

TRANSCRIPT_MASTER_FILE = "master_transcriptions.json"
POSTGRES_CONNECTION_STRING = os.getenv("POSTGRES_CONNECTION_STRING")


class LOAD_TRANSCRIPTS:
    def __init__(self: "LOAD_TRANSCRIPTS", folder: str) -> None:
        # Load environment variables for database connection
        self.connection = None
        self.folder = folder

    async def connect(self: "LOAD_TRANSCRIPTS") -> bool:
        """Establish a connection to the database."""
        try:
            self.connection = await asyncpg.connect(POSTGRES_CONNECTION_STRING)

            if self.connection is None or self.connection.is_closed():
                print("Connection failed")
                return False

            print("Connection successful")
            return True
        except Exception as e:
            print(f"An error occurred while connecting to the database: {e}")
            return False

    async def load_data(self: "LOAD_TRANSCRIPTS") -> None:
        """Load data from JSON file and insert it into the database."""
        if not await self.connect():
            return

        try:
            input_file = Path(self.folder) / "output" / TRANSCRIPT_MASTER_FILE
            with input_file.open("r", encoding="utf-8") as f:
                master = json.load(f)

            # SQL query for inserting data
            insert_query = """
                INSERT INTO public."video_embeddings" 
                (embedding, start, seconds, text, summary) 
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """

            insert_video_query = """
                INSERT INTO public."video_catalog" 
                (id, speaker, title, videoId, description) 
                VALUES ($1, $2, $3, $4, $5)
            """

            insert_combined_query = """
                WITH inserted_embedding AS (
                    INSERT INTO public."video_embeddings" 
                    (embedding, start, seconds, text, summary) 
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING id
                )
                INSERT INTO public."video_catalog" 
                (id, speaker, title, videoId, description) 
                VALUES (
                    (SELECT id FROM inserted_embedding), 
                    $6, $7, $8, $9
                )
            """

            # Insert data into the database
            for r in master:
                try:
                    vector_string = "[{}]".format(", ".join(map(str, r["ada_v2"])))
                    await self.connection.execute(
                        insert_combined_query,
                        vector_string,
                        r["start"],
                        r["seconds"],
                        r["text"],
                        r["summary"],
                        r["speaker"],
                        r["title"],
                        r["videoId"],
                        r["description"],
                    )
                    
                    # vector_string = "[{}]".format(", ".join(map(str, r["ada_v2"])))
                    # id = await self.connection.fetchval(
                    #     insert_query,
                    #     vector_string,
                    #     r["start"],
                    #     r["seconds"],
                    #     r["text"],
                    #     r["summary"],
                    # )
                    # print(f"Inserted data with ID: {id}")

                    # await self.connection.execute(
                    #     insert_video_query,
                    #     id,
                    #     r["speaker"],
                    #     r["title"],
                    #     r["videoId"],
                    #     r["description"],
                    # )

                except Exception:
                    print(f"An error occurred while inserting data: {r['summary']}")

        except Exception as e:
            print(f"An error occurred while loading data: {e}")

        finally:
            # Close the database connection
            if self.connection and not self.connection.is_closed():
                await self.connection.close()
                print("Database connection closed.")

    def start_load(self: "LOAD_TRANSCRIPTS") -> None:
        """Start the process of loading data."""
        asyncio.run(self.load_data())
