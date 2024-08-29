import os
from pathlib import Path
from dotenv import load_dotenv

from download_transcripts import DOWNLOAD_TRANSCRIPT
from bucket_transcripts import BUCKET_TRANSCRIPTS
from embed_transcripts import EMBEDDED_TRANSCRIPTS
from summarize_transcripts import SUMMARIZE_TRANSCRIPTS
from load_transcripts import LOAD_TRANSCRIPTS

# Load environment variables from .env file
load_dotenv()

TRANSCRIPT_FOLDER = os.environ["TRANSCRIPT_FOLDER"]


# does the transcript folder exist?
if not Path(TRANSCRIPT_FOLDER).exists():
    Path(TRANSCRIPT_FOLDER).mkdir()

dl = DOWNLOAD_TRANSCRIPT(TRANSCRIPT_FOLDER)
dl.start_download()

bt = BUCKET_TRANSCRIPTS(TRANSCRIPT_FOLDER, 3)
bt.process_transcripts()

embedded_transcripts = EMBEDDED_TRANSCRIPTS(folder=TRANSCRIPT_FOLDER, verbose=False)
embedded_transcripts.process_segments()

summarize_transcripts = SUMMARIZE_TRANSCRIPTS(folder=TRANSCRIPT_FOLDER)
summarize_transcripts.summarize_text()

loader = LOAD_TRANSCRIPTS(folder=TRANSCRIPT_FOLDER)
loader.start_load()
