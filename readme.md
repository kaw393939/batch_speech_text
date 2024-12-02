# Text-to-Speech Batch Processor

This Python project uses the OpenAI API to convert text files into high-quality speech audio files. It supports batch processing of multiple text files, chunking for large files, and parallel processing for optimal performance. 

The tool is built with reliability and scalability in mind, making it suitable for personal and professional use.

## Features

- Converts text files into MP3 audio files using OpenAI's text-to-speech API.
- Handles large text files by splitting them into manageable chunks.
- Supports parallel processing for efficient batch conversion.
- Automatically moves processed files to the output folder with a `.processed` suffix.
- Includes retry logic for handling transient API failures.
- Graceful shutdown on termination signals with proper cleanup.
- Customizable via a `.env` configuration file.

## Requirements

- Python 3.10+
- [Poetry](https://python-poetry.org/) for dependency management
- An OpenAI API key

## Installation

1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd <your-repo-name>
   ```

2. Install dependencies with Poetry:
   ```bash
   poetry install
   ```

3. Create a `.env` file in the project root and configure the following variables:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   INPUT_FOLDER=./input
   OUTPUT_FOLDER=./output
   VOICE_MODEL=alloy
   TEXT_TO_SPEECH_MODEL=tts-1
   MAX_WORKERS=4
   DEBUG=false
   MAX_CHUNK_SIZE=4096
   ```

4. Ensure `ffmpeg` is installed on your system:
   - On Ubuntu:
     ```bash
     sudo apt install ffmpeg
     ```
   - On macOS (via Homebrew):
     ```bash
     brew install ffmpeg
     ```

## Usage

1. Place text files (`.txt`) into the input folder specified in your `.env` file (`./input` by default).

2. Run the script:
   ```bash
   poetry run python app.py
   ```

3. Converted MP3 files will appear in the output folder (`./output` by default).

4. Processed text files will be renamed with a `.processed` suffix and moved to the output folder.

## Configuration

The `.env` file allows customization of the following settings:

- **OPENAI_API_KEY**: Your OpenAI API key (required).
- **INPUT_FOLDER**: Path to the folder containing input text files.
- **OUTPUT_FOLDER**: Path to the folder where output audio files will be saved.
- **VOICE_MODEL**: The voice model to use for text-to-speech (e.g., `alloy`).
- **TEXT_TO_SPEECH_MODEL**: The text-to-speech model (e.g., `tts-1`).
- **MAX_WORKERS**: Number of threads for parallel processing.
- **DEBUG**: Set to `true` for debug-level logging.
- **MAX_CHUNK_SIZE**: Maximum size (in characters) for each text chunk.

## License

This project is licensed under the [MIT License](LICENSE).

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any feature requests or bug fixes.

## Acknowledgments

- [OpenAI](https://openai.com) for the Text-to-Speech API.
- [Python Poetry](https://python-poetry.org/) for dependency management.
- [FFmpeg](https://ffmpeg.org/) for audio processing.