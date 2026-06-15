# ARHA Quick Setup & Testing Guide

## Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 13+
- Docker (optional, for containerized PostgreSQL)

## Backend Setup

### 1. Create Virtual Environment
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Setup Environment
```bash
# Copy example to .env
cp .env.example .env

# Edit .env with your values
# MINIMUM REQUIRED for testing:
ARHA_ENV=development
SECRET_KEY=your-32-character-secret-key-here-12345
ARHA_PASSPHRASE=your-16-character-passphrase-123
DATABASE_URL=postgresql://user:password@localhost:5432/arha_dev
OPENAI_API_KEY=sk-your-key  # Can be dummy for local testing
```

### 4. Setup Database
```bash
# Using Docker (easiest):
docker run -d \
  --name arha-postgres \
  -e POSTGRES_USER=arha_user \
  -e POSTGRES_PASSWORD=arha_pass \
  -e POSTGRES_DB=arha_dev \
  -p 5432:5432 \
  postgres:15-alpine

# Then update .env:
# DATABASE_URL=postgresql://arha_user:arha_pass@localhost:5432/arha_dev
```

### 5. Start Backend
```bash
# Verify compilation first
python -m py_compile app/*.py
python -c "import app.main; print('✓ Backend compiles successfully')"

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 6. Test Backend Health
```bash
# In another terminal:
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","environment":"development","version":"2.0.0"}
```

---

## Frontend Setup

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Verify Build
```bash
npm run build

# Should complete without errors
# Output: dist/ folder created with optimized build
```

### 3. Run Development Server
```bash
npm run dev

# Expected output:
#   VITE v... ready in XXX ms
#   ➜  Local:   http://localhost:5173/
```

### 4. Verify Frontend
Open http://localhost:5173 in your browser
- You should see the ARHA interface
- Buttons should be interactive (showing "coming soon" alerts)

---

## Validation Tests

### Backend Validation
```bash
# Test 1: Import all modules
python -c "from app import main, models, skills, scoring; print('✓ All imports work')"

# Test 2: Check database connection
python -c "
import asyncio
from app.database import database_is_healthy
print('Testing DB...')
print('✓ Database healthy' if asyncio.run(database_is_healthy()) else '✗ Database unreachable')
"

# Test 3: Check API endpoints
python -m pytest backend/tests/ -v

# Test 4: Check linting
ruff check app/
```

### Frontend Validation
```bash
# Test 1: TypeScript compilation
npx tsc --noEmit

# Test 2: Build succeeds
npm run build

# Test 3: Lint
npm run lint  # if configured
```

### API Contract Test
```bash
# Create test.sh
#!/bin/bash

BASE_URL="http://localhost:8000"

echo "Testing API endpoints..."

# Test health
echo "1. GET /health"
curl -s $BASE_URL/health | jq .

# Test registration
echo "2. POST /auth/register"
curl -s -X POST $BASE_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test@1234"}' | jq .

# Test login
echo "3. POST /auth/token"
TOKEN=$(curl -s -X POST $BASE_URL/auth/token \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test@1234"}' | jq -r '.access_token')
echo "Token: $TOKEN"

# Test protected endpoint
echo "4. GET /auth/me"
curl -s -H "Authorization: Bearer $TOKEN" $BASE_URL/auth/me | jq .
```

---

## Common Issues & Solutions

### Issue: "Module not found: app"
**Solution:** Make sure you're in the backend directory and venv is activated
```bash
cd backend
source venv/bin/activate
```

### Issue: "DATABASE_URL is not configured"
**Solution:** Check your .env file exists and has DATABASE_URL
```bash
cat .env | grep DATABASE_URL
```

### Issue: "Cannot connect to database"
**Solution:** Verify PostgreSQL is running
```bash
# If using Docker:
docker ps | grep arha-postgres

# Or connect directly:
psql -h localhost -U arha_user -d arha_dev
```

### Issue: "npm run build fails"
**Solution:** Clear node_modules and reinstall
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Issue: "Port 8000 already in use"
**Solution:** Kill existing process or use different port
```bash
# Kill process on port 8000
kill -9 $(lsof -t -i :8000)

# Or run on different port
uvicorn app.main:app --port 8001
```

---

## Production Deployment

### Docker Build & Run
```bash
# Build image
cd backend
docker build -t arha-api:latest .

# Run container
docker run -e DATABASE_URL=postgresql://... \
           -e OPENAI_API_KEY=sk-... \
           -e SECRET_KEY=... \
           -e ARHA_PASSPHRASE=... \
           -p 8000:8000 \
           arha-api:latest
```

### Render.com Deployment
1. Push to GitHub
2. Connect repository to Render
3. Create PostgreSQL service
4. Create Web Service linked to Dockerfile
5. Set environment variables in Render dashboard
6. Deploy

### Environment Variables Required
```
ARHA_ENV=production
DATABASE_URL=<your-postgres-url>
SECRET_KEY=<32+ char random string>
ARHA_PASSPHRASE=<16+ char random string>
OPENAI_API_KEY=<your-key>
TAVILY_API_KEY=<your-key>
SERPER_API_KEY=<your-key>
SENDGRID_API_KEY=<your-key>
TELEGRAM_BOT_TOKEN=<your-token>
UPSTASH_REDIS_URL=<optional>
UPSTASH_REDIS_TOKEN=<optional>
```

---

## Verification Checklist

- [ ] Backend Python compilation succeeds
- [ ] Backend starts without errors
- [ ] Health endpoint responds with 200
- [ ] Frontend builds without errors
- [ ] Frontend loads in browser
- [ ] Frontend can connect to backend (check console)
- [ ] Basic API calls work (register, login, etc.)
- [ ] No security warnings in browser console
- [ ] Database tables are created
- [ ] Environment validation works (missing keys throw errors)

---

## Quick Test Summary

To verify all critical fixes are working:

```bash
# Terminal 1: Start backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload

# Terminal 2: Start frontend
cd frontend
npm run dev

# Terminal 3: Run tests
cd backend
pytest tests/ -v

# Browser: Open http://localhost:5173
# Should see ARHA interface loading
```

**Estimated time to full validation: 10-15 minutes**

---

## Need Help?

1. Check CRITICAL_FIXES_REPORT.md for detailed changes
2. Verify .env.example has all required variables
3. Check console output for specific error messages
4. Verify PostgreSQL is running and accessible
5. Check Python/Node.js versions match requirements

---

**Last Updated:** 2026-06-13  
**Status:** All critical fixes applied and ready for testing
