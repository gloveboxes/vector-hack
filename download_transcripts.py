""" This script downloads the transcripts for all the videos in a YouTube playlist. """

import os
from pathlib import Path
import json
import logging
import time
import threading
import queue
import googleapiclient.discovery
import googleapiclient.errors
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import WebVTTFormatter
from concurrent.futures import ThreadPoolExecutor, as_completed


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GOOGLE_DEVELOPER_API_KEY = os.environ["GOOGLE_DEVELOPER_API_KEY"]
YOUTUBE_PLAYLIST_ID = os.environ["YOUTUBE_PLAYLIST_ID"]

# Initialize the Google developer API client
GOOGLE_API_SERVICE_NAME = "youtube"
GOOGLE_API_VERSION = "v3"

MAX_RESULTS = 50
PROCESSING_THREADS = 40

formatter = WebVTTFormatter()
q = queue.Queue()


class Counter:
    """thread safe counter"""

    def __init__(self):
        """initialize the counter"""
        self.value = 0
        self.lock = threading.Lock()

    def increment(self):
        """increment the counter"""
        with self.lock:
            self.value += 1


class DOWNLOAD_TRANSCRIPT:

    def __init__(self, transcript_folder: str) -> None:
        self.count = Counter()
        self.transcript_folder = transcript_folder

    def gen_metadata(self, playlist_item: dict) -> None:
        """Generate metadata for a video"""

        video_id = playlist_item["snippet"]["resourceId"]["videoId"]

        filename = Path(self.transcript_folder) / (video_id + ".json")

        metadata = {}
        metadata["speaker"] = ""
        metadata["title"] = playlist_item["snippet"]["title"]
        metadata["videoId"] = playlist_item["snippet"]["resourceId"]["videoId"]
        metadata["description"] = playlist_item["snippet"]["description"]

        # save the metadata as a .json file
        with filename.open("w", encoding="utf-8") as file:
            json.dump(metadata, file)

    def get_transcript(self, playlist_item: dict, counter_id: int) -> bool:
        """Get the transcript for a video"""

        video_id = playlist_item["snippet"]["resourceId"]["videoId"]
        filename = Path(self.transcript_folder) / (video_id + ".json.vtt")

        # if video transcript already exists, skip it
        if Path(filename).exists():
            logger.debug("Skipping video %d, %s", counter_id, video_id)
            return False

        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            # remove \n from the text
            for item in transcript:
                item["text"] = item["text"].replace("\n", " ")

            logger.debug("Transcription download completed: %d, %s", counter_id, video_id)
            # save the transcript as a .vtt file
            with open(filename, "w", encoding="utf-8") as file:
                json.dump(transcript, file, indent=4, ensure_ascii=False)
                # file.write(transcript)

        except Exception as exception:
            logger.debug(exception)
            logger.debug("Transcription not found for video: %s", video_id)
            return False

        return True

    def process_queue(self) -> None:
        """process the queue"""
        while not q.empty():
            video = q.get()

            self.count.increment()

            if self.get_transcript(video, self.count.value):
                self.gen_metadata(video)
            q.task_done()

    def start_download(self) -> None:
        """Start the download process."""
        logger.debug("Transcription folder: %s", self.transcript_folder)

        youtube = googleapiclient.discovery.build(
            GOOGLE_API_SERVICE_NAME, GOOGLE_API_VERSION, developerKey=GOOGLE_DEVELOPER_API_KEY
        )

        # Create a request object with the playlist ID and the max results
        request = youtube.playlistItems().list(part="snippet", playlistId=YOUTUBE_PLAYLIST_ID, maxResults=MAX_RESULTS)

        # Loop through the pages of results until there is no next page token
        while request:
            try:
                response = request.execute()

                # Batch process the items in the response
                items = response.get("items", [])
                for item in items:
                    q.put(item)

                logger.info("Total transcriptions to be downloaded so far: %s", q.qsize())

                # Get the next page token from the response and create a new request object
                next_page_token = response.get("nextPageToken")
                if next_page_token:
                    request = youtube.playlistItems().list(
                        part="snippet",
                        playlistId=YOUTUBE_PLAYLIST_ID,
                        maxResults=MAX_RESULTS,
                        pageToken=next_page_token,
                    )
                else:
                    request = None

            except googleapiclient.errors.HttpError as e:
                logger.error("An HTTP error occurred: %s", e)
                break

        start_time = time.time()

        logger.info("Downloading transcriptions")

        # Using ThreadPoolExecutor to manage threads
        with ThreadPoolExecutor(max_workers=PROCESSING_THREADS) as executor:
            futures = [executor.submit(self.process_queue) for _ in range(PROCESSING_THREADS)]
            for future in as_completed(futures):
                try:
                    future.result()  # To catch any exceptions that occurred during processing
                except Exception as e:
                    logger.error("An error occurred during processing: %s", e)

        finish_time = time.time()
        logger.debug("Total time taken: %.2f seconds", finish_time - start_time)
