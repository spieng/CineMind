"""End-to-end verification script testing web endpoints, static files, and responses."""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from fastapi.testclient import TestClient
from api.main import app

def test_full_pipeline():
    print("=" * 60)
    print("Running Full Pipeline Verification")
    print("=" * 60)

    with TestClient(app) as client:
        # 1. Root HTML
        print("\n[1] Verifying GET / (index.html)...")
        res = client.get("/")
        assert res.status_code == 200, f"GET / returned {res.status_code}"
        assert "CineMind AI" in res.text or "Movie Recommender" in res.text
        assert "/static/css/style.css" in res.text
        assert "/static/js/chat.js" in res.text
        print("  ✓ Served index.html with correct static references.")

        # 2. Static CSS
        print("\n[2] Verifying GET /static/css/style.css...")
        res = client.get("/static/css/style.css")
        assert res.status_code == 200
        assert "app-layout" in res.text
        print("  ✓ Static CSS served properly.")

        # 3. Static JS
        print("\n[3] Verifying GET /static/js/chat.js...")
        res = client.get("/static/js/chat.js")
        assert res.status_code == 200
        assert "handleSend" in res.text
        print("  ✓ Static JS served properly.")

        # 4. Health
        print("\n[4] Verifying GET /api/health...")
        res = client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert "status" in data and "tmdb_configured" in data
        print(f"  ✓ /api/health status: {data['status']}, tmdb_configured: {data['tmdb_configured']}")

        # 5. Examples
        print("\n[5] Verifying GET /api/examples...")
        res = client.get("/api/examples")
        assert res.status_code == 200
        examples = res.json()
        assert len(examples) == 6
        assert "movies like Inception" in examples
        print(f"  ✓ /api/examples returned {len(examples)} items.")

        # 6. Metrics
        print("\n[6] Verifying GET /api/metrics...")
        res = client.get("/api/metrics")
        assert res.status_code == 200
        metrics = res.json()
        assert "cache_size" in metrics and "api_calls_today" in metrics
        print(f"  ✓ /api/metrics: {metrics}")

        # 7. Chat: Greeting
        print("\n[7] Verifying POST /api/chat with 'hello'...")
        res = client.post("/api/chat", json={"message": "hello"})
        assert res.status_code == 200
        body = res.json()
        assert body["intent"] == "greeting"
        assert len(body["reply"]) > 0
        print(f"  ✓ Greeting reply: {body['reply']}")

        # 8. Chat: Fallback 'asdfgh'
        print("\n[8] Verifying POST /api/chat with 'asdfgh'...")
        res = client.post("/api/chat", json={"message": "asdfgh"})
        assert res.status_code == 200
        body = res.json()
        assert body["intent"] == "unknown"
        assert "The Matrix" in body["reply"] or "recommend a comedy" in body["reply"]
        print(f"  ✓ Fallback reply: {body['reply']}")

        # 9. Chat: Recommendation queries
        print("\n[9] Verifying POST /api/chat with 'movies like Inception'...")
        res = client.post("/api/chat", json={"message": "movies like Inception"})
        assert res.status_code == 200
        body = res.json()
        assert body["intent"] == "recommend_by_title"
        print(f"  ✓ Recommendation response received. Reply: {body['reply']}")

        # 10. Swagger Docs
        print("\n[10] Verifying GET /docs (Swagger UI)...")
        res = client.get("/docs")
        assert res.status_code == 200
        assert "Swagger UI" in res.text
        print("  ✓ Swagger UI /docs is functional.")

    print("\n" + "=" * 60)
    print("ALL END-TO-END VERIFICATION CHECKS PASSED SUCCESSFULLY! ✅")
    print("=" * 60)

if __name__ == "__main__":
    test_full_pipeline()
