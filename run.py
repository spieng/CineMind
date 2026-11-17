"""Root launcher for Movie Assistant."""

import sys
from pathlib import Path
import uvicorn

# Add movie-assistant to sys.path
PROJECT_DIR = Path(__file__).resolve().parent / "movie-assistant"
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from api.main import app

if __name__ == "__main__":
    print("=" * 60)
    print("Starting Movie Recommender AI Server")
    print("Web UI available at: http://127.0.0.1:8000")
    print("Interactive API docs: http://127.0.0.1:8000/docs")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=8000)
