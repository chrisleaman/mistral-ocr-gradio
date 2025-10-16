# Mistral OCR Gradio App

A simple web application that converts PDF files to Markdown using Mistral's OCR API.

## Features

- Upload PDF files through an intuitive web interface
- Convert PDF content to Markdown format using Mistral's OCR
- Download the converted Markdown file
- Real-time progress tracking during processing
- Docker support for easy deployment

## Prerequisites

- Python 3.9 or higher
- A Mistral API key (get one from [https://console.mistral.ai/](https://console.mistral.ai/))
- [uv](https://github.com/astral-sh/uv) package manager

## Quick Start

1. Clone this repository

2. Create a `.env` file with your Mistral API key:
   ```bash
   cp .env.example .env
   # Edit .env and add your MISTRAL_API_KEY
   ```

3. Install dependencies:
   ```bash
   uv pip install mistralai gradio python-dotenv
   ```

4. Run the application:
   ```bash
   uv run python app.py
   ```

5. Open your browser and go to `http://localhost:7860`

## Docker Usage

Build and run using Docker:

```bash
# Build the image
docker build -t mistral-ocr-gradio .

# Run with .env file (recommended)
docker run -p 7860:7860 --env-file .env mistral-ocr-gradio

# Or pass API key directly as environment variable
docker run -p 7860:7860 -e MISTRAL_API_KEY=your_key_here mistral-ocr-gradio
```

The app will be available at http://localhost:7860

## How It Works

1. Upload a PDF file using the web interface
2. The app uploads the PDF to Mistral's file storage
3. Mistral's OCR API processes the PDF and extracts text
4. The extracted text is formatted as Markdown
5. Download the resulting Markdown file

## Project Structure

```
.
├── app.py              # Main Gradio application
├── pyproject.toml      # Project dependencies
├── Dockerfile          # Docker configuration
├── .env.example        # Environment variables template
├── CLAUDE.md           # Documentation for Claude Code
└── README.md           # This file
```

## License

MIT
