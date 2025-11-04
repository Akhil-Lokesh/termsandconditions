# AI-Powered Terms & Conditions Analysis System

An intelligent RAG (Retrieval-Augmented Generation) system that analyzes Terms & Conditions documents, answers questions in plain language, and automatically detects risky or unusual clauses.

## 🎯 Project Overview

This system performs three core functions:

1. **Document Analysis**: Extracts and understands the legal structure of T&C documents
2. **Intelligent Q&A**: Answers user questions about T&C clauses in plain language with citations
3. **Anomaly Detection**: Automatically identifies risky, unusual, or concerning clauses by comparing to a baseline corpus of 100+ standard T&Cs

**Key Differentiator**: Unlike generic document Q&A systems, this actively analyzes Terms & Conditions to detect risky clauses, compare to industry standards, and flag consumer protection concerns.

## 🚀 Features

- **Smart Document Processing**: Extracts legal structure (sections, clauses) with metadata
- **Legal-Aware Chunking**: Preserves clause integrity for accurate retrieval
- **Semantic Search**: Vector similarity search for relevant clauses
- **Plain Language Answers**: GPT-4 powered explanations with section citations
- **Anomaly Detection**: Identifies unusual or risky clauses (prevalence <30%)
- **Risk Scoring**: Overall risk assessment (1-10 scale)
- **Comparison Tool**: Side-by-side comparison of multiple T&Cs
- **Missing Clause Detection**: Flags absence of standard consumer protections

## 🛠️ Tech Stack

### Backend
- **API Framework**: FastAPI (Python 3.10+)
- **LLM**: OpenAI GPT-4 (analysis), GPT-3.5-turbo (development)
- **Embeddings**: OpenAI text-embedding-3-small
- **Vector DB**: Pinecone
- **Database**: PostgreSQL
- **Cache**: Redis
- **PDF Processing**: PyPDF2, pdfplumber

### Frontend
- **Framework**: React + TypeScript
- **UI**: Tailwind CSS + shadcn/ui
- **State Management**: React Query
- **Build Tool**: Vite
- **Deployment**: Netlify

### Infrastructure
- **Backend Deployment**: Railway/Render
- **Frontend Deployment**: Netlify
- **Containerization**: Docker + Docker Compose
- **CI/CD**: GitHub Actions

## 📁 Project Structure

```
Project T&C/
├── backend/              # FastAPI backend application
│   ├── app/
│   │   ├── api/         # API endpoints
│   │   ├── core/        # Core business logic
│   │   ├── models/      # Database models
│   │   ├── schemas/     # Pydantic schemas
│   │   ├── services/    # External services (OpenAI, Pinecone)
│   │   ├── prompts/     # LLM prompts
│   │   └── utils/       # Utility functions
│   ├── tests/           # Backend tests
│   └── alembic/         # Database migrations
│
├── frontend/            # React frontend application
│   └── src/
│       ├── components/  # React components
│       ├── pages/       # Page components
│       ├── hooks/       # Custom React hooks
│       ├── services/    # API services
│       └── types/       # TypeScript types
│
├── scripts/             # Utility scripts
│   ├── build_baseline_corpus.py
│   └── setup_dev_environment.sh
│
├── data/                # Data directory
│   ├── baseline_corpus/ # 100+ standard T&Cs
│   └── test_samples/    # Test T&C documents
│
└── docs/                # Documentation
    ├── ARCHITECTURE.md  # System architecture
    ├── API.md          # API documentation
    ├── DEPLOYMENT.md   # Deployment guide
    └── DEVELOPMENT.md  # Development setup
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Docker & Docker Compose
- OpenAI API key
- Pinecone API key

### Development Setup

See [DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed setup instructions.

Quick start:

```bash
# Clone repository
git clone <your-repo-url>
cd "Project T&C"

# Set up backend
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys

# Set up frontend
cd ../frontend
npm install
cp .env.example .env
# Edit .env with backend API URL

# Start services
docker-compose up -d

# Run backend
cd backend
uvicorn app.main:app --reload

# Run frontend (in new terminal)
cd frontend
npm run dev
```

Visit http://localhost:5173 to see the application.

## 📊 Development Timeline

- **Phase 1 (Weeks 1-3)**: Foundation & Basic RAG
- **Phase 2 (Weeks 4-5)**: T&C Specialization & Metadata
- **Phase 3 (Weeks 6-7)**: Anomaly Detection System
- **Phase 4 (Weeks 8-10)**: Frontend & Deployment

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed timeline and deliverables.

## 📚 Documentation

- [Architecture Overview](docs/ARCHITECTURE.md) - System design and components
- [API Documentation](docs/API.md) - API endpoints and usage
- [Development Guide](docs/DEVELOPMENT.md) - Setup and development workflow
- [Deployment Guide](docs/DEPLOYMENT.md) - Production deployment instructions

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test

# Coverage report
pytest --cov=app --cov-report=html
```

## 📝 License

MIT License - See [LICENSE](LICENSE) file for details.

## 🤝 Contributing

This is a portfolio project. Contributions, issues, and feature requests are welcome!

## 📧 Contact

Your Name - your.email@example.com

Project Link: [https://github.com/yourusername/tc-analysis-system](https://github.com/yourusername/tc-analysis-system)
