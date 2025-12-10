FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements-backend.txt .
RUN pip install --no-cache-dir -r requirements-backend.txt

# Copy backend code
COPY backend/ /app/backend/
COPY model/ /app/model/
COPY alembic/ /app/alembic/
COPY alembic.ini /app/

# Create uploads directory
RUN mkdir -p /app/backend/uploads

# Expose port
EXPOSE 8000

# Run migrations and start server
CMD alembic upgrade head && uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
