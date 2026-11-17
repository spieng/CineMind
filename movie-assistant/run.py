"""Server entrypoint to start Movie Assistant application."""

import sys
from pathlib import Path
import uvicorn

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

if __name__ == "__main__":
    print("=" * 60)
    print("Starting Movie Recommender AI Server")
    print("Web UI available at: http://127.0.0.1:8000")
    print("Interactive API docs: http://127.0.0.1:8000/docs")
    print("=" * 60)
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)
