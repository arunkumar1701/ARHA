# ARHA V1

ARHA is a privacy-first local career intelligence app for Arun. It manages resumes, verifies real job opportunities, scores matches deterministically, tracks approvals, and prepares application materials only after explicit approval.

## Structure

- `backend/` - FastAPI app, encrypted SQLite storage, resume/job/scoring services, tests.
- `frontend/` - React/Vite dashboard.
- `render.yaml` - Render cron worker skeleton for public-source discovery only.

## Backend Quick Start

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Set `ARHA_PASSPHRASE` before first use to control the local encryption key:

```powershell
$env:ARHA_PASSPHRASE="choose-a-long-local-passphrase"
```

## Frontend Quick Start

```powershell
cd frontend
npm install
npm run dev
```

## Privacy Rules Implemented

- Resume text, application packages, approval metadata, and profile-like fields are encrypted in SQLite.
- No application, email, upload, or referral action is executed by ARHA.
- Application package generation requires a prior approval record.
- Application package generation also requires an approved resume optimization for that job.
- Approved resume changes create encrypted resume versions and never overwrite the original upload.
- Jobs must have verifiable source URLs to be recommended.
- If data cannot be verified, ARHA returns: `I do not currently have sufficient verified information to complete this request.`

## Resume Strategist Workflow

For a selected job, ARHA can generate a resume optimization report comparing the current resume with job requirements, ATS keywords, role focus, and company recruitment style.

The workflow is:

```text
Job Found
Resume Analysis
Resume Improvement Suggestions
User Approval
Resume Version Creation
ATS Validation
Company Verification
Application Package Creation
Final User Approval
```

No optimized resume version is created unless the user approves the suggested changes.
