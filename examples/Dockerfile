# Example Dockerfile for MCP server using mcp-mapped-resource-lib
#
# This Dockerfile demonstrates how to build a Docker image for an MCP server
# that uses the MCP Mapped Resource Library for blob storage.

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for python-magic (MIME type detection)
RUN apt-get update && apt-get install -y \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy library source (or install from PyPI)
COPY . /app/

# Install the library and dependencies
RUN pip install --no-cache-dir -e .

# Install FastMCP for the example server
RUN pip install --no-cache-dir fastmcp>=2.0.0

# Create blob storage directory
RUN mkdir -p /mnt/blob-storage && chmod 755 /mnt/blob-storage

# Set environment variables
ENV BLOB_STORAGE_ROOT=/mnt/blob-storage \
    BLOB_MAX_SIZE_MB=100 \
    BLOB_DEFAULT_TTL_HOURS=24 \
    PYTHONUNBUFFERED=1

# Expose port for MCP server
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the example server
CMD ["python", "examples/fastmcp_example.py"]

# Alternative: Production-ready Dockerfile
# FROM python:3.11-slim AS builder
#
# WORKDIR /app
# COPY . .
# RUN pip install --no-cache-dir build && python -m build
#
# FROM python:3.11-slim
#
# RUN apt-get update && apt-get install -y libmagic1 && rm -rf /var/lib/apt/lists/*
#
# COPY --from=builder /app/dist/*.whl /tmp/
# RUN pip install --no-cache-dir /tmp/*.whl fastmcp>=2.0.0 && rm /tmp/*.whl
#
# RUN mkdir -p /mnt/blob-storage && chmod 755 /mnt/blob-storage
#
# ENV BLOB_STORAGE_ROOT=/mnt/blob-storage
# EXPOSE 8000
#
# CMD ["python", "-m", "your_mcp_server"]
