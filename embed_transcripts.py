import logging
import re
import os
import json
import threading
import queue
import time
import openai
import tiktoken
from rich.progress import Progress
from ollama import Client

OLLAMA_EMBEDDING_ENDPOINT = "http://jumbo:11434"
OLLAMA_EMBEDDING_MODEL="nomic-embed-text"
TRANSCRIPT_MASTER_FILE = "master_transcriptions.json"

class EMBEDDED_TRANSCRIPTS:
    def __init__(self, folder: str, verbose: bool = False):
        # self.API_KEY = os.environ["AZURE_OPENAI_API_KEY"]
        # self.RESOURCE_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
        self.PROCESSING_THREADS = 6
        self.OPENAI_REQUEST_TIMEOUT = 60
        
        openai.api_type = "azure"
        # openai.api_key = self.API_KEY
        # openai.api_base = self.RESOURCE_ENDPOINT
        openai.api_version = "2023-05-15"

        self.logger = self.setup_logger(verbose)
        self.TRANSCRIPT_FOLDER = folder
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        self.total_segments = 0
        self.current_segment = 0
        self.output_segments = []
        self.remote_host = OLLAMA_EMBEDDING_ENDPOINT
        self.model = OLLAMA_EMBEDDING_MODEL

        self.segments = self.load_segments()
        self.custom_client = Client(host=self.remote_host, timeout=10)

    def setup_logger(self, verbose: bool):
        """Set up the logger with the desired verbosity level."""
        logging.basicConfig(level=logging.WARNING)
        logger = logging.getLogger(__name__)
        if verbose:
            logger.setLevel(logging.DEBUG)
        return logger


    def load_segments(self):
        """Load segments from the JSON file."""
        input_file = os.path.join(self.TRANSCRIPT_FOLDER, "output", TRANSCRIPT_MASTER_FILE)
        with open(input_file, "r", encoding="utf-8") as f:
            segments = json.load(f)
        self.total_segments = len(segments)
        return segments
    
    def get_text_embedding(self, prompt: str) -> list:
        max_retry = 3

        for i in range(max_retry):
            try:
                embedding_result = self.custom_client.embeddings(model=self.model, prompt=prompt)
                return embedding_result["embedding"]
            except Exception as e:
                print(f"Error: {e}")
        return []


    def normalize_text(self, s: str, sep_token=" \n "):
        """Normalize text by removing extra spaces and newlines."""
        s = re.sub(r"\s+", " ", s).strip()
        s = re.sub(r". ,", "", s)
        s = s.replace("..", ".")
        s = s.replace(". .", ".")
        s = s.replace("\n", "")
        s = s.strip()
        return s

    def process_queue(self, progress, task):
        """Process the queue."""
        while not self.q.empty():
            segment = self.q.get()

            if "ada_v2" in segment:
                self.output_segments.append(segment.copy())
                continue

            self.logger.debug(segment["title"])
            text = segment["text"]

            if len(self.tokenizer.encode(text)) > 8191:
                continue

            text = self.normalize_text(text)
            segment["text"] = text

            embedding = self.get_text_embedding(text)
            if embedding is None:
                self.output_segments.append(segment.copy())
                continue

            segment["ada_v2"] = embedding.copy()

            self.output_segments.append(segment.copy())
            progress.update(task, advance=1)
            self.q.task_done()
            time.sleep(0.2)

    def convert_time_to_seconds(self, value: str):
        """Convert time '00:01:20' to seconds."""
        time_value = value.split(":")
        if len(time_value) == 3:
            h, m, s = time_value
            return int(h) * 3600 + int(m) * 60 + int(s)
        return 0

    def save_embeddings(self):
        """Save the embeddings to a JSON file."""
        output_file = os.path.join(self.TRANSCRIPT_FOLDER, "output", TRANSCRIPT_MASTER_FILE)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.output_segments, f)

    def process_segments(self):
        """Process segments to enrich embeddings."""
        self.logger.debug("Total segments to be processed: %s", len(self.segments))

        # Add segment list to a queue
        self.q = queue.Queue()
        for segment in self.segments:
            self.q.put(segment)

        with Progress() as progress:
            task1 = progress.add_task("[green]Enriching Embeddings...", total=self.total_segments)
            # Create multiple threads to process the queue
            threads = []
            for i in range(self.PROCESSING_THREADS):
                t = threading.Thread(target=self.process_queue, args=(progress, task1))
                t.start()
                threads.append(t)

            # Wait for all threads to finish
            for t in threads:
                t.join()

        # Sort the output segments by videoId and start
        self.output_segments.sort(key=lambda x: (x["videoId"], self.convert_time_to_seconds(x["start"])))
        self.logger.debug("Total segments processed: %s", len(self.output_segments))

        # Save the enriched embeddings
        self.save_embeddings()
