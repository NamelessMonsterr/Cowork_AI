# Production Dockerfile for Flash Assistant

FROM python:3.11-slim-windowsservercore

# Set working directory
WORKDIR /app

# Install system dependencies
RUN pip install --upgrade pip

# Copy requirements
COPY requirements.lock ./
COPY requirements.txt ./

# Install Python dependencies from lock file
RUN pip install --no-cache-dir -r requirements.lock

# Copy application code
COPY assistant/ ./assistant/
COPY ui/ ./ui/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV ENV=production

# Expose port
EXPOSE 8765

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8765/health')"

# CRITICAL SECURITY FIX: Create non-privileged user
# Windows containers: use ContainerAdministrator -> ContainerUser pattern
RUN net user appuser /add && \
    icacls C:\\app /grant appuser:F /T

USER appuser

# Run application (single worker for session consistency)
CMD ["python", "-m", "uvicorn", "assistant.main:app", "--host", "0.0.0.0", "--port", "8765", "--workers", "1"]
