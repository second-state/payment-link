FROM python:3.13-slim

WORKDIR /app

# Install git (required for fetching git dependencies)
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy project files
COPY pyproject.toml uv.lock* ./

# Install dependencies
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY main.py config.py database.py ./
COPY static/ ./static/

# Expose port
EXPOSE 8000

# Run the application (--no-sync to use pre-installed dependencies)
CMD ["uv", "run", "--no-sync", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
