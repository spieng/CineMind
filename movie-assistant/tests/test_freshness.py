"""Test script verifying recommendation pagination and freshness (no repeated movies)."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.chatbot import MovieAssistant

load_dotenv(BASE_DIR / ".env")

def test_comedy_pagination():
    print("=" * 60)
    print("Testing Comedy Recommendation Freshness & Pagination")
    print("=" * 60)

    api_key = os.getenv("TMDB_API_KEY", "").strip()
    if not api_key or api_key == "your_key_here":
        print("[SKIP] TMDB_API_KEY not configured. Cannot test live TMDB pagination.")
        return

    assistant = MovieAssistant(api_key)

    # Batch 1: First comedy request
    print("\n[Query 1] 'recommend a comedy'")
    res1 = assistant.reply("recommend a comedy")
    recs1 = res1.get("recommendations", [])
    titles1 = [m["title"] for m in recs1]
    ids1 = [m["id"] for m in recs1]
    print(f"Reply: {res1['reply']}")
    print(f"Movies Batch 1 ({len(titles1)}): {titles1}")
    assert len(titles1) == 5, f"Expected 5 movies, got {len(titles1)}"

    # Batch 2: "recommend more movies"
    print("\n[Query 2] 'recommend more movies'")
    res2 = assistant.reply("recommend more movies")
    recs2 = res2.get("recommendations", [])
    titles2 = [m["title"] for m in recs2]
    ids2 = [m["id"] for m in recs2]
    print(f"Reply: {res2['reply']}")
    print(f"Movies Batch 2 ({len(titles2)}): {titles2}")
    assert len(titles2) == 5, f"Expected 5 movies, got {len(titles2)}"

    # Batch 3: "more comedy"
    print("\n[Query 3] 'more comedy'")
    res3 = assistant.reply("more comedy")
    recs3 = res3.get("recommendations", [])
    titles3 = [m["title"] for m in recs3]
    ids3 = [m["id"] for m in recs3]
    print(f"Reply: {res3['reply']}")
    print(f"Movies Batch 3 ({len(titles3)}): {titles3}")
    assert len(titles3) == 5, f"Expected 5 movies, got {len(titles3)}"

    # Verify no overlap between batch 1, 2, and 3
    overlap_1_2 = set(ids1).intersection(set(ids2))
    overlap_2_3 = set(ids2).intersection(set(ids3))
    overlap_1_3 = set(ids1).intersection(set(ids3))

    assert not overlap_1_2, f"Overlap found between Batch 1 and 2: {overlap_1_2}"
    assert not overlap_2_3, f"Overlap found between Batch 2 and 3: {overlap_2_3}"
    assert not overlap_1_3, f"Overlap found between Batch 1 and 3: {overlap_1_3}"

    total_unique = len(set(ids1 + ids2 + ids3))
    print(f"\n✓ Total unique comedy movies recommended across 3 queries: {total_unique} / 15")
    print("=" * 60)
    print("PAGINATION & DEDUPLICATION TEST PASSED SUCCESSFULLY! ✅")
    print("=" * 60)

if __name__ == "__main__":
    test_comedy_pagination()
