"""Sanity test script for Layer C: API Endpoints using FastAPI TestClient."""

import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from fastapi.testclient import TestClient
from api.main import app

def run_api_tests():
    print("=" * 60)
    print("Layer C Sanity Test: FastAPI Endpoints")
    print("=" * 60)

    with TestClient(app) as client:
        # 1. Health check
        print("\n[1] Testing GET /api/health...")
        res = client.get("/api/health")
        assert res.status_code == 200, f"Health check failed with {res.status_code}: {res.text}"
        data = res.json()
        print(f"  ✓ Health status: {data['status']}, tmdb_configured: {data['tmdb_configured']}")
        assert "status" in data and "tmdb_configured" in data and "message" in data

        # 2. Examples
        print("\n[2] Testing GET /api/examples...")
        res = client.get("/api/examples")
        assert res.status_code == 200
        examples = res.json()
        print(f"  ✓ Received {len(examples)} examples: {examples[:2]}...")
        assert len(examples) == 6

        # 3. Metrics
        print("\n[3] Testing GET /api/metrics...")
        res = client.get("/api/metrics")
        assert res.status_code == 200
        metrics = res.json()
        print(f"  ✓ Metrics: cache_size={metrics['cache_size']}, api_calls_today={metrics['api_calls_today']}")
        assert "cache_size" in metrics and "api_calls_today" in metrics and "rate_limit_remaining" in metrics

        # 4. Chat Endpoint: Greeting
        print("\n[4] Testing POST /api/chat (greeting)...")
        res = client.post("/api/chat", json={"message": "hello"})
        assert res.status_code == 200
        chat_data = res.json()
        print(f"  ✓ Greeting reply: {chat_data['reply']}")
        assert chat_data["intent"] == "greeting"

        # 5. Chat Endpoint: Unknown query
        print("\n[5] Testing POST /api/chat ('asdfgh')...")
        res = client.post("/api/chat", json={"message": "asdfgh"})
        assert res.status_code == 200
        chat_data = res.json()
        print(f"  ✓ Fallback reply: {chat_data['reply']}")
        assert chat_data["intent"] == "unknown"

        # 6. Chat Endpoint: Validation error check
        print("\n[6] Testing POST /api/chat with empty string (should return 422 Unprocessable Entity)...")
        res = client.post("/api/chat", json={"message": ""})
        assert res.status_code == 422
        print("  ✓ Schema validation correctly rejected empty message with 422.")

        # 7. OpenAPI / Swagger check
        print("\n[7] Testing GET /openapi.json...")
        res = client.get("/openapi.json")
        assert res.status_code == 200
        openapi_spec = res.json()
        assert openapi_spec["info"]["title"] == "Movie Recommender AI"
        print("  ✓ Swagger OpenAPI spec generated cleanly.")

    print("\n" + "=" * 60)
    print("Layer C: ALL API TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_api_tests()
