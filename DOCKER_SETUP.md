# Docker Setup Guide

## Quick Start

Start all services (PostgreSQL, Redis, Backend):

```bash
cd "/Users/akhil/Desktop/Project T&C"
docker-compose up -d
```

Check service status:

```bash
docker-compose ps
```

View logs:

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f postgres
docker-compose logs -f redis
```

Stop all services:

```bash
docker-compose down
```

Stop and remove volumes (⚠️ deletes database data):

```bash
docker-compose down -v
```

---

## Service Configuration

### Backend Service

- **Container**: `tc-analysis-backend`
- **Port**: `8000` (http://localhost:8000)
- **API Docs**: http://localhost:8000/api/v1/docs
- **Health Check**: http://localhost:8000/health
- **Hot Reload**: Enabled via volume mounting

### PostgreSQL Database

- **Container**: `tc-analysis-postgres`
- **Port**: `5432`
- **Database**: `tcanalysis`
- **User**: `tcuser`
- **Password**: `tcpassword`
- **Health Check**: Automatic with `pg_isready`

### Redis Cache

- **Container**: `tc-analysis-redis`
- **Port**: `6379`
- **Persistence**: Enabled (AOF)
- **Health Check**: Automatic with `redis-cli ping`

---

## Environment Configuration

### Running in Docker

The `docker-compose.yml` overrides the database and Redis URLs to use Docker service names:

- `DATABASE_URL=postgresql://tcuser:tcpassword@postgres:5432/tcanalysis`
- `REDIS_URL=redis://redis:6379/0`

**Note**: The `backend/.env` file has both local and Docker configurations commented. When running in Docker, the environment variables from `docker-compose.yml` take precedence.

### Running Locally (Outside Docker)

If you want to run the backend locally but use Docker for PostgreSQL and Redis:

1. Start only the database services:
   ```bash
   docker-compose up -d postgres redis
   ```

2. Make sure `backend/.env` has local URLs:
   ```env
   DATABASE_URL=postgresql://tcuser:tcpassword@localhost:5432/tcanalysis
   REDIS_URL=redis://localhost:6379/0
   ```

3. Run the backend locally:
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

---

## Database Management

### Initialize Database

Run migrations inside the backend container:

```bash
docker-compose exec backend python scripts/init_database.py
```

Or manually with Alembic:

```bash
docker-compose exec backend python -m alembic upgrade head
```

### Check Migration Status

```bash
docker-compose exec backend python -m alembic current
```

### Reset Database (⚠️ Destructive)

```bash
docker-compose exec backend python scripts/init_database.py --reset
```

### Access PostgreSQL Shell

```bash
docker-compose exec postgres psql -U tcuser -d tcanalysis
```

Useful commands:
- `\dt` - List tables
- `\d table_name` - Describe table schema
- `SELECT COUNT(*) FROM documents;` - Count documents
- `\q` - Quit

### Access Redis CLI

```bash
docker-compose exec redis redis-cli
```

Useful commands:
- `KEYS *` - List all keys
- `GET key_name` - Get value
- `FLUSHALL` - Clear all data (⚠️ destructive)
- `exit` - Quit

---

## Troubleshooting

### Backend Can't Connect to Database

**Symptoms**: `connection refused` errors in backend logs

**Solutions**:

1. Check if postgres is healthy:
   ```bash
   docker-compose ps postgres
   ```

2. Check postgres logs:
   ```bash
   docker-compose logs postgres
   ```

3. Verify network:
   ```bash
   docker network inspect project-tc_tc-network
   ```

4. Restart services:
   ```bash
   docker-compose restart postgres backend
   ```

### Database Migration Errors

**Symptoms**: Backend fails to start due to missing tables

**Solution**: Run migrations manually:

```bash
docker-compose exec backend python -m alembic upgrade head
```

### Port Already in Use

**Symptoms**: `bind: address already in use`

**Solution**:

1. Find what's using the port:
   ```bash
   lsof -i :8000  # or :5432 or :6379
   ```

2. Stop the conflicting service or change port in `docker-compose.yml`

### Backend Container Keeps Restarting

**Symptoms**: Backend container status shows "Restarting"

**Solutions**:

1. Check backend logs:
   ```bash
   docker-compose logs backend
   ```

2. Common issues:
   - Missing API keys in `.env`
   - Database not ready (should auto-fix with health checks)
   - Python dependency errors

3. Rebuild the image:
   ```bash
   docker-compose build backend
   docker-compose up -d backend
   ```

### Slow Build Times

**Solution**: The Docker image is being rebuilt from scratch.

- Use BuildKit for faster builds:
  ```bash
  DOCKER_BUILDKIT=1 docker-compose build
  ```

- Check `.dockerignore` includes `__pycache__`, `venv/`, etc.

---

## Development Workflow

### Making Code Changes

1. Edit code in `backend/` directory
2. Changes are automatically synced to container (volume mount)
3. Backend auto-reloads (uvicorn `--reload` flag)
4. View logs: `docker-compose logs -f backend`

### Installing New Dependencies

1. Add to `backend/requirements.txt`
2. Rebuild backend image:
   ```bash
   docker-compose build backend
   docker-compose up -d backend
   ```

### Running Tests in Container

```bash
docker-compose exec backend pytest
```

### Running Scripts in Container

```bash
# Example: Index baseline corpus
docker-compose exec backend python scripts/index_baseline_corpus.py
```

---

## Production Considerations

⚠️ **Do NOT use this Docker setup in production as-is!**

For production deployment:

1. **Remove `--reload` flag** from uvicorn command
2. **Use production WSGI server** (gunicorn)
3. **Use managed database** (AWS RDS, Azure Database, etc.)
4. **Use managed Redis** (AWS ElastiCache, Redis Cloud, etc.)
5. **Add SSL/TLS** certificates
6. **Use secrets management** (AWS Secrets Manager, Vault, etc.)
7. **Add monitoring** (Prometheus, Grafana, etc.)
8. **Add logging** (ELK stack, CloudWatch, etc.)
9. **Use multi-stage builds** for smaller images
10. **Run as non-root user** in container

See `docs/DEPLOYMENT.md` for production deployment guide.

---

## Useful Commands Reference

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart a service
docker-compose restart backend

# Rebuild a service
docker-compose build backend

# View logs (follow)
docker-compose logs -f backend

# Execute command in container
docker-compose exec backend python --version

# List running containers
docker-compose ps

# Remove all containers and volumes
docker-compose down -v

# Check resource usage
docker stats
```

---

## Network Architecture

```
┌─────────────────────────────────────────────┐
│           Docker Network: tc-network        │
│                                             │
│  ┌──────────────┐  ┌──────────────┐       │
│  │  PostgreSQL  │  │    Redis     │       │
│  │   :5432      │  │    :6379     │       │
│  └──────┬───────┘  └──────┬───────┘       │
│         │                  │                │
│         └──────┬───────────┘                │
│                │                            │
│         ┌──────▼───────┐                    │
│         │   Backend    │                    │
│         │   :8000      │                    │
│         └──────┬───────┘                    │
└────────────────┼──────────────────────────┘
                 │
                 │ (host port mapping)
                 │
         ┌───────▼────────┐
         │  localhost:8000 │
         │  (your browser) │
         └─────────────────┘
```

All services communicate via the `tc-network` Docker bridge network using service names as hostnames.
