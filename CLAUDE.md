# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A simple Gradio web application that allows users to upload PDF files, process them using Mistral's OCR API, and download the converted markdown files.

**Tech Stack:**
- Python 3.9+
- Gradio 4.0+ for the web interface
- Mistral AI SDK for OCR processing
- uv for package management
- Docker for containerization

## Environment Setup

This project uses `uv` for package management. All environment commands should use `uv --active`.

### Initial Setup

1. Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```

2. Add your Mistral API key to `.env`:
   ```
   MISTRAL_API_KEY=your_actual_api_key_here
   ```
   Get your API key from https://console.mistral.ai/

3. Install dependencies:
   ```bash
   uv pip install mistralai gradio python-dotenv
   ```

### Running the Application

**Development mode:**
```bash
uv run python app.py
```

The app will be available at http://localhost:7860

**Using Docker:**
```bash
# Build the image
docker build -t mistral-ocr-gradio .

# Run with .env file (recommended)
docker run -p 7860:7860 --env-file .env mistral-ocr-gradio

# Or pass API key directly
docker run -p 7860:7860 -e MISTRAL_API_KEY=your_key_here mistral-ocr-gradio
```

The app will be available at http://localhost:7860

## Project Structure

- `app.py` - Main Gradio application with OCR processing logic
- `pyproject.toml` - Project dependencies and metadata
- `Dockerfile` - Container configuration for deployment
- `.env.example` - Template for environment variables
- `.dockerignore` - Files to exclude from Docker builds

## Application Architecture

The app follows a simple workflow:

1. **File Upload**: User uploads a PDF via Gradio interface
2. **Mistral Upload**: PDF is uploaded to Mistral's file storage using `client.files.upload()`
3. **Get Signed URL**: Retrieve a signed URL for the uploaded file using `client.files.get_signed_url()`
4. **OCR Processing**: Call `client.ocr.process()` with the document URL
5. **Markdown Generation**: Combine all pages' markdown content with page markers
6. **Download**: Provide the complete markdown as a downloadable file

### Key Functions

- `upload_pdf_to_mistral(pdf_file)`: Handles uploading PDF to Mistral and returns signed URL
- `process_pdf_ocr(pdf_file, progress)`: Main processing function that orchestrates the entire OCR workflow

## Mistral OCR API Details

The application uses Mistral's OCR API which:
- Accepts PDF files and images
- Returns structured markdown content per page
- Supports the `mistral-ocr-latest` model
- Requires files to be uploaded to Mistral's file storage first

## Environment Variables

- `MISTRAL_API_KEY` (required): Your Mistral API key from https://console.mistral.ai/
- `GRADIO_SERVER_NAME` (optional): Server hostname, defaults to `localhost` for local dev, set to `0.0.0.0` in Docker
- `GRADIO_SERVER_PORT` (optional): Server port, defaults to `7860`

## Development Notes

- The app runs on port 7860 by default (Gradio's standard port)
- Server binding is configurable via environment variables for Docker compatibility
- Progress callbacks are implemented for better UX during processing
- Error handling includes user-friendly messages in the Gradio interface
- Temporary files are created for markdown downloads
