#!/bin/bash
# Apply Alembic migrations to database
# Run this after Docker Compose is started

set -e

echo "=================================="
echo "Applying Database Migrations"
echo "=================================="
echo ""

# Check if backend container is running
if ! docker compose ps backend | grep -q "Up"; then
    echo "❌ Error: Backend container is not running"
    echo "Please start services first: docker compose up -d"
    exit 1
fi

echo "✓ Backend container is running"
echo ""

# Apply migrations
echo "Running: alembic upgrade head"
echo "----------------------------------"
docker compose exec backend alembic upgrade head

echo ""
echo "✅ Migrations applied successfully!"
echo ""

# Show current migration status
echo "Current migration status:"
echo "----------------------------------"
docker compose exec backend alembic current

echo ""
echo "To view migration history:"
echo "  docker compose exec backend alembic history"
echo ""
echo "To create a new migration:"
echo "  docker compose exec backend alembic revision --autogenerate -m 'Description'"
