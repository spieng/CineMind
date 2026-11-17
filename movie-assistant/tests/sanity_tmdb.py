"""Sanity test script for Layer A: TMDBClient."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tmdb_client import TMDBClient

load_dotenv()

def run_sanity_check():
    print("=" * 60)
    print("Layer A Sanity Test: TMDBClient")
    print("=" * 60)

    api_key = os.getenv("TMDB_API_KEY", "").strip()

    if not api_key or api_key == "your_key_here":
        print("[INFO] No real TMDB_API_KEY set in .env. Testing degraded mode & mock...")
        client = TMDBClient(None)
        assert not client.is_configured, "Client should report is_configured=False"
        print("  ✓ Correctly detects unconfigured API key.")

        # Test build_poster_url helper
        sample_path = "/9gk7adHYeDvHkCSEqAvQNLV5Uge.jpg"
        url = client.build_poster_url(sample_path)
        assert url == f"https://image.tmdb.org/t/p/w200{sample_path}", "Poster URL incorrect"
        assert client.build_poster_url(None) is None, "None poster path should return None"
        print("  ✓ build_poster_url works as expected.")

        # Test cache mechanism using simulated entry
        client.cache["/simulated:()"] = (10000000000, {"results": [{"id": 1, "title": "Mock Inception"}]})
        metrics = client.get_metrics()
        assert metrics["cache_size"] == 1
        print("  ✓ Cache storage & metrics verified.")
        print("[SUCCESS] Layer A sanity check passed in degraded/offline mode.")
        print("Tip: Add a real TMDB_API_KEY in .env to run a live test with TMDB's servers.")
        return

    print(f"[INFO] Found TMDB_API_KEY ({api_key[:4]}...{api_key[-4:] if len(api_key) > 8 else ''}). Testing live TMDB API...")
    client = TMDBClient(api_key)
    assert client.is_configured, "Client should report is_configured=True"

    # 1. Search Movie
    print("\n[1] Calling search_movie('Inception')...")
    movie = client.search_movie("Inception")
    if not movie:
        print("  [ERROR] Inception search returned None!")
        sys.exit(1)

    print(f"  ✓ Found movie: ID={movie.get('id')}, Title='{movie.get('title')}', Rating={movie.get('vote_average')}")
    print(f"  ✓ Poster URL: {client.build_poster_url(movie.get('poster_path'))}")

    # 2. Recommendations
    print("\n[2] Calling get_recommendations for Inception...")
    recs = client.get_recommendations(movie["id"])
    print(f"  ✓ Retrieved {len(recs)} recommendation results.")

    # 3. Discover by genre
    print("\n[3] Calling discover_by_genre('Action')...")
    action_movies = client.discover_by_genre("Action")
    print(f"  ✓ Retrieved {len(action_movies)} action movie results.")

    # 4. Cache Verification
    print("\n[4] Verifying cache hit on repeated search...")
    initial_calls = client.api_calls_today
    _ = client.search_movie("Inception")
    assert client.api_calls_today == initial_calls, "Repeated search should hit cache without incrementing API calls"
    print(f"  ✓ Cache hit verified! Cache size: {client.get_metrics()['cache_size']}")

    print("\n" + "=" * 60)
    print("Layer A: ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_sanity_check()
