import os
import shutil
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import subprocess
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
import signal
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Load environment variables from .env file
load_dotenv()

# Get configurations from environment variables
API_KEY = os.getenv("OPENAI_API_KEY")
PROJECT_ROOT = Path(__file__).parent.parent  # Root of the project
INPUT_FOLDER = PROJECT_ROOT / os.getenv("INPUT_FOLDER", "input")
OUTPUT_FOLDER = PROJECT_ROOT / os.getenv("OUTPUT_FOLDER", "output")
TEMP_FOLDER = PROJECT_ROOT / os.getenv("TEMP_FOLDER", "temp")
VOICE_MODEL = os.getenv("VOICE_MODEL", "alloy")
TTS_MODEL = os.getenv("TEXT_TO_SPEECH_MODEL", "tts-1")
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))
MAX_CHUNK_SIZE = int(os.getenv("MAX_CHUNK_SIZE", "4096"))

# Ensure required directories exist
INPUT_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
TEMP_FOLDER.mkdir(parents=True, exist_ok=True)

# Initialize OpenAI client
if not API_KEY:
    raise ValueError("OPENAI_API_KEY not found in .env file")
client = OpenAI(api_key=API_KEY)

# Graceful shutdown handling
def handle_exit_signal(signum, frame):
    logging.info("Received termination signal. Cleaning up...")
    if TEMP_FOLDER.exists():
        shutil.rmtree(TEMP_FOLDER)
    exit(0)

signal.signal(signal.SIGINT, handle_exit_signal)
signal.signal(signal.SIGTERM, handle_exit_signal)

def split_text_into_chunks(text: str, max_length: int = MAX_CHUNK_SIZE) -> List[str]:
    """Split a large text into manageable chunks."""
    chunks = []
    while len(text) > max_length:
        split_index = text.rfind(" ", 0, max_length)  # Split at the nearest space
        if split_index == -1:  # If no space is found, force split
            split_index = max_length
        chunks.append(text[:split_index])
        text = text[split_index:].strip()
    if text:
        chunks.append(text)
    return chunks

def generate_audio_with_retries(chunk: str, chunk_index: int, file_stem: str, retries: int = 3) -> Path:
    """Generate audio for a text chunk with retries."""
    for attempt in range(retries):
        try:
            return generate_audio(chunk, chunk_index, file_stem)
        except Exception as e:
            if attempt < retries - 1:
                logging.warning(f"Retrying chunk {chunk_index + 1} due to error: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise

def generate_audio(chunk: str, chunk_index: int, file_stem: str) -> Path:
    """Generate audio for a text chunk and save to a temporary file."""
    try:
        temp_subdir = TEMP_FOLDER / file_stem
        temp_subdir.mkdir(parents=True, exist_ok=True)

        output_audio_path = temp_subdir / f"{file_stem}_part_{chunk_index + 1}.mp3"
        response = client.audio.speech.create(
            model=TTS_MODEL,
            voice=VOICE_MODEL,
            input=chunk,
        )

        with open(output_audio_path, "wb") as audio_file:
            for audio_chunk in response.iter_bytes():
                audio_file.write(audio_chunk)

        logging.info(f"Generated audio for chunk {chunk_index + 1}")
        return output_audio_path
    except Exception as e:
        logging.error(f"Error generating audio for chunk {chunk_index + 1}: {e}")
        raise

def combine_audio_files(audio_files: List[Path], final_output_path: Path):
    """Combine multiple audio files into one using ffmpeg."""
    concat_file = TEMP_FOLDER / "concat_list.txt"
    with concat_file.open("w") as f:
        for file in audio_files:
            f.write(f"file '{file.resolve()}'\n")

    try:
        subprocess.run(
            ["ffmpeg", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(final_output_path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        logging.info(f"Combined audio files into {final_output_path}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error combining audio files: {e}")
        raise
    finally:
        if concat_file.exists():
            concat_file.unlink()

def process_file(file: Path):
    """Process a single text file to generate a combined audio file."""
    try:
        logging.info(f"Processing file: {file.name}")

        with file.open("r", encoding="utf-8") as f:
            text_content = f.read()

        if not text_content.strip():
            logging.warning(f"File {file.name} is empty. Skipping...")
            return

        # Split text into chunks
        chunks = split_text_into_chunks(text_content)
        audio_files = []

        # Process chunks in parallel with retries
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(generate_audio_with_retries, chunk, i, file.stem): i
                for i, chunk in enumerate(chunks)
            }
            for future in as_completed(futures):
                audio_files.append(future.result())

        # Sort audio files to ensure correct order
        audio_files.sort(key=lambda x: int(x.stem.split('_part_')[-1]))

        # Create a subfolder for the output file
        file_output_folder = OUTPUT_FOLDER / file.stem
        file_output_folder.mkdir(parents=True, exist_ok=True)

        # Define final output path
        final_output_path = file_output_folder / f"{file.stem}.mp3"

        # Combine audio files into one
        combine_audio_files(audio_files, final_output_path)

        # Move processed file to the output folder with a .processed suffix
        processed_file_path = file_output_folder / f"{file.stem}.processed.txt"
        shutil.move(file, processed_file_path)

        logging.info(f"Finished processing file: {file.name} -> {final_output_path.name}")
    except Exception as e:
        logging.error(f"Error processing file {file.name}: {e}", exc_info=True)

def main():
    """Main function to process all files in the input folder."""
    try:
        logging.info("Starting processing...")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(process_file, file): file.name
                for file in INPUT_FOLDER.glob("*.txt")
            }
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logging.error(f"Error processing a file: {e}")
    finally:
        # Cleanup temporary directory
        if TEMP_FOLDER.exists():
            shutil.rmtree(TEMP_FOLDER)
        logging.info("Processing complete!")

if __name__ == "__main__":
    main()
