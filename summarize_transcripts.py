import os
from pathlib import Path
from ollama import Client
import json
from time import sleep

summary_endpoint = os.environ.get("SUMMARY_ENDPOINT")
model = "phi3.5"
TRANSCRIPT_MASTER_FILE = "master_transcriptions.json"

SYSTEM_MESSAGE = (
    "You're an AI Assistant for video transcripts. "
    "Write a 60 word technical summary. Avoid starting sentences with 'This video'. "
    "Just give the summary in plain text, no additional information"
)


class SUMMARIZE_TRANSCRIPTS:
    def __init__(self: "SUMMARIZE_TRANSCRIPTS", folder: str, timeout: int = 60) -> None:
        self.folder = folder
        self.model = model
        self.timeout = timeout
        self.master_segments = []
        self.total_segments = 0
        self.custom_client = Client(host=summary_endpoint, timeout=self.timeout)

    def load_master(self: "SUMMARIZE_TRANSCRIPTS") -> list:
        """Load segments from the JSON file."""
        input_file = Path(self.folder) / "output" / TRANSCRIPT_MASTER_FILE
        with input_file.open("r", encoding="utf-8") as f:
            segments = json.load(f)
        self.total_segments = len(segments)
        return segments

    def save_master(self: "SUMMARIZE_TRANSCRIPTS") -> None:
        """Save the embeddings to a JSON file."""
        output_file = Path(self.folder) / "output" / TRANSCRIPT_MASTER_FILE
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(self.master_segments, f)

    def get_summary(self: "SUMMARIZE_TRANSCRIPTS", text: str) -> str:
        max_retry = 3

        for attempt in range(max_retry):
            try:
                ollama_response = self.custom_client.chat(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_MESSAGE},
                        {"role": "user", "content": text},
                    ],
                )
                return ollama_response["message"]["content"].strip()
            except Exception as error:
                print(f"Attempt {attempt + 1} failed with error: {error}")
                sleep(4)
        else:
            print("All retry attempts failed.")
            return ""

    def summarize_text(self: "SUMMARIZE_TRANSCRIPTS") -> None:
        count = 0
        self.master_segments = self.load_master()

        for count, r in enumerate(self.master_segments, start=1):
            print(count)

            r["summary"] = self.get_summary(r["text"])

        self.save_master()
