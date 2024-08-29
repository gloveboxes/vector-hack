from datetime import datetime, timedelta
import glob
import os
import json
import tiktoken
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VttSegment:
    def __init__(self, segment: dict[str, str | float]) -> None:
        self.text = segment.get("text")
        self.start = segment.get("start")
        self.duration = segment.get("duration")


class BUCKET_TRANSCRIPTS:
    SEGMENT_LENGTH_MINUTES = 5
    PERCENTAGE_OVERLAP = 0.05
    MAX_TOKENS = 2048

    def __init__(self, folder=None, minutes=5, verbose=False):
        self.segments = []
        self.total_files = 0
        self.transcript_folder = folder or "transcripts"
        self.segment_length_minutes = minutes or self.SEGMENT_LENGTH_MINUTES
        self.verbose = verbose
        self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")

        if self.verbose:
            logger.setLevel(logging.DEBUG)

        if not self.transcript_folder:
            logger.error("Transcript folder not provided")
            exit(1)

    def gen_metadata_master(self, metadata):
        """Generate the metadata master csv file"""
        text = metadata["title"] + " " + metadata["description"]
        metadata["start"] = "00:00:00"

        text = text.strip()

        if text == "" or text is None:
            metadata["text"] = "No description available."
        else:
            text = text.replace("\n", "")
            metadata["text"] = text.strip()

    def clean_text(self, text):
        """Clean the text"""
        text = text.replace("\n", " ")  # remove new lines
        text = text.replace("&#39;", "'")
        text = text.replace(">>", "")  # remove '>>'
        text = text.replace("  ", " ")  # remove double spaces
        text = text.replace("[inaudible]", "")  # [inaudible]
        return text

    def append_text_to_previous_segment(self, text):
        """Append PERCENTAGE_OVERLAP text to the previous segment to smooth context transition"""
        if len(self.segments) > 0:
            words = text.split(" ")
            word_count = len(words)
            if word_count > 0:
                append_text = " ".join(words[0 : int(word_count * self.PERCENTAGE_OVERLAP)])
                self.segments[-1]["text"] += append_text

    def add_new_segment(self, metadata, text, segment_begin_seconds):
        """Add a new segment to the segments list"""
        delta = timedelta(seconds=segment_begin_seconds)
        begin_time = datetime.min + delta
        metadata["start"] = begin_time.strftime("%H:%M:%S")
        metadata["seconds"] = segment_begin_seconds

        metadata["text"] = text
        self.segments.append(metadata.copy())

    def parse_json_vtt_transcript(self, vtt, metadata):
        """Parse the JSON VTT file and return the transcript"""
        text = ""
        current_seconds = None
        seg_begin_seconds = None
        seg_finish_seconds = None
        current_token_length = 0
        first_segment = True

        # Add speaker name, title, and description to the transcript
        for key in ["speaker", "title", "description"]:
            if key in metadata and metadata[key] != "":
                metadata[key] = self.clean_text(metadata.get(key))
                text += f"{metadata.get(key)}. "

        current_token_length = len(self.tokenizer.encode(text))

        # Open the VTT file
        with open(vtt, "r", encoding="utf-8") as json_file:
            json_vtt = json.load(json_file)

            for segment in json_vtt:
                seg = VttSegment(segment)
                current_seconds = int(seg.start)
                current_text = seg.text

                if seg_begin_seconds is None:
                    seg_begin_seconds = current_seconds
                    seg_finish_seconds = seg_begin_seconds + self.segment_length_minutes * 60

                total_tokens = len(self.tokenizer.encode(current_text)) + current_token_length

                if current_seconds < seg_finish_seconds and total_tokens < self.MAX_TOKENS:
                    text += current_text + " "
                    current_token_length = total_tokens
                else:
                    if not first_segment:
                        self.append_text_to_previous_segment(text)
                    first_segment = False
                    self.add_new_segment(metadata, text, seg_begin_seconds)

                    text = current_text + " "
                    seg_begin_seconds = None
                    seg_finish_seconds = None
                    current_token_length = len(self.tokenizer.encode(text))

            if seg_begin_seconds and text != "":
                previous_segment_tokens = len(self.tokenizer.encode(self.segments[-1]["text"]))
                current_segment_tokens = len(self.tokenizer.encode(text))

                if previous_segment_tokens + current_segment_tokens < self.MAX_TOKENS:
                    self.segments[-1]["text"] += text
                else:
                    if not first_segment:
                        self.append_text_to_previous_segment(text)
                    first_segment = False
                    self.add_new_segment(metadata, text, seg_begin_seconds)

    def get_transcript(self, metadata):
        """Get the transcript from the .vtt file"""
        vtt = os.path.join(self.transcript_folder, metadata["videoId"] + ".json.vtt")

        if not os.path.exists(vtt):
            logger.info("vtt file does not exist: %s", vtt)
            return
        logger.debug("Processing file: %s", vtt)
        self.total_files += 1

        self.parse_json_vtt_transcript(vtt, metadata)

    def save_segments(self):
        """Save segments to a JSON file"""
        output_file = os.path.join(self.transcript_folder, "output", "master_transcriptions.json")
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.segments, f, ensure_ascii=False, indent=4)

    def process_transcripts(self):
        """Process all transcripts in the transcript folder"""
        logger.info("Transcription folder: %s", self.transcript_folder)
        logger.info("Segment length %d minutes", self.segment_length_minutes)

        folder = os.path.join(self.transcript_folder, "*.json")

        for file in glob.glob(folder):
            meta = json.load(open(file, encoding="utf-8"))
            self.get_transcript(meta)

        logger.info("Total files: %s", self.total_files)
        logger.info("Total segments: %s", len(self.segments))

        self.save_segments()
