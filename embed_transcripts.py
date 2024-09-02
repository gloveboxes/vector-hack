import os
import logging
from pathlib import Path
import re
import json
import tiktoken
from ollama import Client

OLLAMA_EMBEDDING_ENDPOINT = os.getenv("OLLAMA_EMBEDDING_ENDPOINT")
OLLAMA_EMBEDDING_MODEL = "nomic-embed-text"
TRANSCRIPT_MASTER_FILE = "master_transcriptions.json"


class EMBED_TRANSCRIPTS:
    def __init__(self: "EMBED_TRANSCRIPTS", folder: str, verbose: bool = False) -> None:

        self.PROCESSING_THREADS = 1
        self.OPENAI_REQUEST_TIMEOUT = 60

        self.logger = self.setup_logger(verbose)
        self.folder = folder
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        self.total_segments = 0
        self.current_segment = 0
        self.output_segments = []
        self.remote_host = OLLAMA_EMBEDDING_ENDPOINT
        self.model = OLLAMA_EMBEDDING_MODEL

        self.segments = self.load_segments()
        self.custom_client = Client(host=self.remote_host, timeout=10)

    def load_master(self: "EMBED_TRANSCRIPTS") -> list:
        """Load segments from the JSON file."""
        input_file = Path(self.folder) / "output" / TRANSCRIPT_MASTER_FILE
        with input_file.open("r", encoding="utf-8") as f:
            segments = json.load(f)
        self.total_segments = len(segments)
        return segments

    def setup_logger(self: "EMBED_TRANSCRIPTS", verbose: bool) -> logging.Logger:
        """Set up the logger with the desired verbosity level."""
        logging.basicConfig(level=logging.WARNING)
        logger = logging.getLogger(__name__)
        if verbose:
            logger.setLevel(logging.DEBUG)
        return logger

    def load_segments(self: "EMBED_TRANSCRIPTS") -> list:
        """Load segments from the JSON file."""
        input_file = Path(self.folder) / "output" / TRANSCRIPT_MASTER_FILE
        with input_file.open("r", encoding="utf-8") as f:
            segments = json.load(f)
        self.total_segments = len(segments)
        return segments

    def get_text_embedding(self: "EMBED_TRANSCRIPTS", prompt: str) -> list:
        max_retry = 3

        for i in range(max_retry):
            try:
                embedding_result = self.custom_client.embeddings(model=self.model, prompt=prompt)
                return embedding_result["embedding"]
            except Exception as e:
                print(f"Error: {e}")
        return []

    def normalize_text(self: "EMBED_TRANSCRIPTS", s: str, sep_token: str = " \n ") -> str:
        """Normalize text by removing extra spaces and newlines."""
        s = re.sub(r"\s+", " ", s).strip()
        s = re.sub(r". ,", "", s)
        s = s.replace("..", ".")
        s = s.replace(". .", ".")
        s = s.replace("\n", "")
        s = s.strip()
        return s

    def process_segment(self: "EMBED_TRANSCRIPTS", segment: dict) -> None:
        """Process the queue."""

        self.logger.debug(segment["title"])
        text = segment["text"]

        if len(self.tokenizer.encode(text)) > 8191:
            self.output_segments.append(segment.copy())
            return

        text = self.normalize_text(text)
        segment["text"] = text

        embedding = self.get_text_embedding(text)
        if embedding is None:
            self.output_segments.append(segment.copy())
            return

        segment["ada_v2"] = embedding.copy()
        self.output_segments.append(segment.copy())

    def convert_time_to_seconds(self: "EMBED_TRANSCRIPTS", value: str) -> int:
        """Convert time '00:01:20' to seconds."""
        time_value = value.split(":")
        if len(time_value) == 3:
            h, m, s = time_value
            return int(h) * 3600 + int(m) * 60 + int(s)
        return 0

    def save_embeddings(self: "EMBED_TRANSCRIPTS") -> None:
        """Save the embeddings to a JSON file."""
        output_file = Path(self.folder) / "output" / TRANSCRIPT_MASTER_FILE
        with Path(output_file).open("w", encoding="utf-8") as f:
            json.dump(self.output_segments, f)

    def process_segments(self: "EMBED_TRANSCRIPTS") -> None:
        """Process segments to enrich embeddings."""

        master_segments = self.load_master()

        self.logger.debug("Total segments to be processed: %s", len(master_segments))

        for count, segment in enumerate(master_segments, start=1):
            print(count)
            self.process_segment(segment)

        # Sort the output segments by videoId and start
        self.output_segments.sort(key=lambda x: (x["videoId"], self.convert_time_to_seconds(x["start"])))
        self.logger.debug("Total segments processed: %s", len(self.output_segments))

        self.save_embeddings()
