# AI Service Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv for fast dependency management
RUN pip install uv

# Copy all files needed for build
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install dependencies (not editable mode for production)
RUN uv pip install --system .

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Run the service
CMD ["python", "-m", "src.main"]
