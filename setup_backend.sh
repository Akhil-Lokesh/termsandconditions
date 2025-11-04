#!/bin/bash

# T&C Analysis System - Backend Setup Script
# This script sets up the complete backend environment

set -e  # Exit on any error

echo "🚀 T&C Analysis System - Backend Setup"
echo "======================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR/backend"

cd "$BACKEND_DIR"

# Step 1: Check API Keys
echo "📋 Step 1: Checking API Keys..."
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ ERROR: .env file not found!${NC}"
    echo "Please run: cp .env.example .env"
    echo "Then add your API keys and run this script again."
    exit 1
fi

# Check if API keys are set
if grep -q "YOUR_OPENAI_API_KEY_HERE" .env; then
    echo -e "${RED}❌ ERROR: OpenAI API key not set!${NC}"
    echo "Please edit backend/.env and add your OpenAI API key (line 7)"
    echo "Location: $BACKEND_DIR/.env"
    exit 1
fi

if grep -q "YOUR_PINECONE_API_KEY_HERE" .env; then
    echo -e "${RED}❌ ERROR: Pinecone API key not set!${NC}"
    echo "Please edit backend/.env and add your Pinecone API key (line 16)"
    echo "Location: $BACKEND_DIR/.env"
    exit 1
fi

echo -e "${GREEN}✅ API keys configured${NC}"
echo ""

# Step 2: Check Python
echo "📋 Step 2: Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ ERROR: Python 3 not found!${NC}"
    echo "Please install Python 3.9 or later"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✅ Python $PYTHON_VERSION found${NC}"
echo ""

# Step 3: Create Virtual Environment
echo "📋 Step 3: Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
else
    echo -e "${YELLOW}⚠️  Virtual environment already exists${NC}"
fi
echo ""

# Step 4: Activate and Install Dependencies
echo "📋 Step 4: Installing Python dependencies..."
source venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip --quiet

echo "Installing requirements..."
pip install -r requirements.txt --quiet

echo -e "${GREEN}✅ Dependencies installed${NC}"
echo ""

# Step 5: Check Docker
echo "📋 Step 5: Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ ERROR: Docker not found!${NC}"
    echo "Please install Docker Desktop from https://www.docker.com/products/docker-desktop"
    exit 1
fi

if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ ERROR: Docker daemon not running!${NC}"
    echo "Please start Docker Desktop application"
    exit 1
fi

echo -e "${GREEN}✅ Docker is running${NC}"
echo ""

# Step 6: Start Database Services
echo "📋 Step 6: Starting database services..."
echo "Starting PostgreSQL and Redis..."
docker-compose up -d

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
sleep 5

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo -e "${GREEN}✅ Database services started${NC}"
else
    echo -e "${RED}❌ ERROR: Failed to start database services${NC}"
    docker-compose logs
    exit 1
fi
echo ""

# Step 7: Run Database Migrations
echo "📋 Step 7: Setting up database..."

# Check if alembic is installed
if ! command -v alembic &> /dev/null; then
    echo "Installing alembic..."
    pip install alembic --quiet
fi

# Check if migrations directory exists
if [ ! -d "alembic/versions" ] || [ -z "$(ls -A alembic/versions)" ]; then
    echo "Creating initial migration..."
    alembic revision --autogenerate -m "Initial migration"
fi

echo "Running migrations..."
alembic upgrade head

echo -e "${GREEN}✅ Database migrations complete${NC}"
echo ""

# Step 8: Test Backend
echo "📋 Step 8: Testing backend imports..."
python -c "from app.main import app; print('✅ Backend imports successful')" || {
    echo -e "${RED}❌ ERROR: Backend import failed${NC}"
    exit 1
}
echo ""

# Summary
echo "======================================="
echo -e "${GREEN}✅ BACKEND SETUP COMPLETE!${NC}"
echo "======================================="
echo ""
echo "🎉 Your backend is ready to start!"
echo ""
echo "To start the backend server:"
echo "  cd $BACKEND_DIR"
echo "  source venv/bin/activate"
echo "  uvicorn app.main:app --reload"
echo ""
echo "Backend will run on: http://localhost:8000"
echo "API docs will be at: http://localhost:8000/api/v1/docs"
echo ""
echo "Frontend is already running on: http://localhost:5173"
echo ""
