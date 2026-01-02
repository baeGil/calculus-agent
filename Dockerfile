FROM python:3.11-slim

WORKDIR /app

# Install Node.js for frontend build
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy Python dependencies
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen || uv sync

# Copy frontend and build
COPY frontend/ ./frontend/
WORKDIR /app/frontend
RUN npm ci && npm run build

# Copy backend
WORKDIR /app
COPY backend/ ./backend/

# Create data directory for SQLite and set permissions
RUN mkdir -p /data && chmod 777 /data

# Set environment variables
ENV DATABASE_URL=sqlite+aiosqlite:///data/algebra_chat.db
ENV PYTHONPATH=/app

# Expose port
EXPOSE 7860

# Run the application
CMD ["uv", "run", "uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "7860"]
