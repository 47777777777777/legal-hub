FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=7860

# Install system dependencies if needed (curl, ca-certificates)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy all repository files
COPY . /app

# Ensure data and static directories exist
RUN mkdir -p /app/data /app/static

# Build initial corpus if needed and ensure permissions
RUN python scripts/build_comprehensive_corpus.py || true

# Hugging Face Spaces uses non-root user (user 1000)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose default Hugging Face Spaces port
EXPOSE 7860

# Run sync on startup (if DB empty) then start server
CMD ["python", "backend/app.py"]

