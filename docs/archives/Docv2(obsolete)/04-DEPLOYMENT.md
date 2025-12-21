# Deployment Guide

## 1. Overview
Abstract Wiki Architect is composed of two primary services:
* **Backend:** Python/FastAPI (Port 8000)
* **Frontend:** Next.js (Port 3000) - *Optional UI*

## 2. Local Development (Bare Metal)

### Backend
```bash
# Install dependencies
pip install -r requirements.txt

# Run the API server with hot-reload
uvicorn architect_http_api.main:app --reload --port 8000 --host 0.0.0.0
````

### Frontend (Optional)

```bash
cd abstractwiki-frontend
npm install
npm run dev
```

## 3\. Docker Deployment

We provide Dockerfiles for containerized deployment.

### Backend Container

```bash
# Build
docker build -f docker/Dockerfile.backend -t abstractwiki-backend .

# Run
docker run -d --name abstractwiki-backend \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  abstractwiki-backend
```

*Note: We mount the `./data` volume so you can update the lexicon without rebuilding the image.*

### Frontend Container

```bash
# Build
docker build -f docker/Dockerfile.frontend -t abstractwiki-frontend .

# Run
docker run -d --name abstractwiki-frontend \
  -p 3000:3000 \
  --link abstractwiki-backend \
  -e NEXT_PUBLIC_API_URL=http://abstractwiki-backend:8000 \
  abstractwiki-frontend
```

## 4\. Hybrid Environment: Linux (WSL) & Windows

This setup is ideal for developers who prefer coding on Windows (VS Code) but running the backend in a native Linux environment.

### The Problem

  * **Line Endings:** Windows uses `CRLF`, Linux uses `LF`. Python scripts with `CRLF` can crash in Linux.
  * **Paths:** Windows paths (`C:\`) confuse Linux tools.

### The Solution: WSL 2

Use **Windows Subsystem for Linux (WSL 2)** to run the backend while keeping your IDE in Windows.

#### Step 1: Install WSL

Open PowerShell as Administrator and run:

```powershell
wsl --install
```

Restart your computer if prompted.

#### Step 2: Set Up the Project in WSL

1.  Open your WSL terminal (Ubuntu).
2.  Clone the repository **inside the Linux file system** (e.g., `~/projects/`), NOT on the mounted Windows drive (`/mnt/c/`).
      * *Why?* Faster file I/O and avoids permission issues.
    <!-- end list -->
    ```bash
    cd ~
    mkdir projects
    cd projects
    git clone <your-repo-url>
    ```

#### Step 3: Connect VS Code

1.  Install the **"WSL" extension** in VS Code.
2.  In your WSL terminal, navigate to the project folder and type:
    ```bash
    code .
    ```
    This opens VS Code on Windows, but it "talks" directly to the Linux file system.

#### Step 4: Line Ending Hygiene

To prevent `CRLF` issues, create a `.gitattributes` file in the root directory:

```text
* text=auto eol=lf
```

This forces Git to checkout files with Linux line endings (`LF`), even on Windows.

## 5\. Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `ARCHITECT_ENV` | `dev` or `prod` | `dev` |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING` | `INFO` |
| `WIKIDATA_CACHE_DIR` | Path to store raw dumps | `./data/raw_wikidata` |

