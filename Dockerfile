FROM python:3.12-slim

WORKDIR /app

# Install OS-level dependencies for PostgreSQL client and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency definition and install system-wide
COPY pyproject.toml .
RUN uv pip install --system -r pyproject.toml

# Copy application source code
COPY . .

EXPOSE 8000

# Run FastAPI app with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
