"""Sanity test script for Layer B: Intent Parser, Recommender, and MovieAssistant."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.intent_parser import parse_intent
from src.chatbot import MovieAssistant

load_dotenv()

def test_intent_parser():
    print("\n--- Testing Intent Parser ---")
    test_cases = [
        ("movies like Inception", "recommend_by_title", "Inception"),
        ("recommend something like The Matrix", "recommend_by_title", "The Matrix"),
        ("recommend a comedy", "recommend_by_genre", "Comedy"),
        ("show me horror films", "recommend_by_genre", "Horror"),
        ("top rated movies", "top_rated", None),
        ("recommend based on Interstellar, Avatar", "recommend_for_user", ["Interstellar", "Avatar"]),
        ("hello", "greeting", None),
        ("help", "help", None),
        ("asdfgh", "unknown", None),
    ]

    for query, expected_intent, expected_entity in test_cases:
        res = parse_intent(query)
        assert res["intent"] == expected_intent, f"Query '{query}' expected {expected_intent}, got {res['intent']}"
        if expected_intent == "recommend_by_title":
            assert res["entities"]["title"].lower() == expected_entity.lower(), f"Expected title {expected_entity}, got {res['entities']['title']}"
        elif expected_intent == "recommend_by_genre":
            assert res["entities"]["genre"] == expected_entity, f"Expected genre {expected_entity}, got {res['entities']['genre']}"
        elif expected_intent == "recommend_for_user":
            for seed in expected_entity:
                assert any(seed.lower() in s.lower() for s in res["entities"]["seeds"])
        print(f"  ✓ '{query}' -> intent: {res['intent']}, entities: {res['entities']}")


def test_chatbot():
    print("\n--- Testing MovieAssistant ---")
    api_key = os.getenv("TMDB_API_KEY", "").strip()

    assistant = MovieAssistant(api_key if api_key and api_key != "your_key_here" else None)

    # 1. Greeting
    r = assistant.reply("hello")
    print(f"  ✓ Greeting reply: {r['reply']}")
    assert "Hi!" in r["reply"]
    assert r["intent"] == "greeting"

    # 2. Unknown query
    r = assistant.reply("asdfgh")
    print(f"  ✓ Unknown query reply: {r['reply']}")
    assert r["intent"] == "unknown"

    # 3. Recommendation query check
    r = assistant.reply("movies like Inception")
    if not assistant.client.is_configured:
        print(f"  ✓ Degraded mode reply: {r['reply']}")
        assert "Please configure your TMDB API key in .env" in r["reply"]
    else:
        print(f"  ✓ Live reply: {r['reply']}")
        print(f"  ✓ Recommendations count: {len(r['recommendations'])}")
        assert len(r["recommendations"]) > 0
        first = r["recommendations"][0]
        print(f"    First pick: {first['title']} ({first['year']}) - Rating: {first['rating']} - Reason: {first['reason']}")
        assert "title" in first and "year" in first and "rating" in first

    print("\n" + "=" * 60)
    print("Layer B: ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    test_intent_parser()
    test_chatbot()
