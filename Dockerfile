FROM python:3.11-slim

WORKDIR /app

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy application file
COPY app.py .

# Install dependencies using uv
RUN uv pip install --system mistralai gradio python-dotenv

# Expose Gradio's default port
EXPOSE 7860

# Configure Gradio to accept external connections in Docker
ENV GRADIO_SERVER_NAME=0.0.0.0
ENV GRADIO_SERVER_PORT=7860

# Environment variable for Mistral API key (must be provided at runtime)
# Use: docker run -e MISTRAL_API_KEY=your_key_here ...
# Or: docker run --env-file .env ...

# Run the application
CMD ["python", "app.py"]
