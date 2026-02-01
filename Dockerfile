FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml ./
COPY main.py ./

# Install dependencies
RUN uv pip install --system --no-cache \
    google-generativeai>=0.8.0 \
    python-dotenv>=1.0.0 \
    rich>=13.0.0 \
    prompt-toolkit>=3.0.0

CMD ["python", "main.py"]
