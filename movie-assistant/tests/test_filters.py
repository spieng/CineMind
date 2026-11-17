"""Test script verifying UI and conversational filtering."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from fastapi.testclient import TestClient
from api.main import app

load_dotenv(BASE_DIR / ".env")

def test_filtering():
    print("=" * 60)
    print("Testing Filter Options (UI & Chat)")
    print("=" * 60)

    with TestClient(app) as client:
        # 1. UI Filtered discovery via payload.filters
        print("\n[1] Testing UI filter payload: Genre=Action, min_rating=8.0, year_from=2010...")
        payload1 = {
            "message": "Discover top action movies",
            "filters": {
                "genre": "Action",
                "min_rating": 8.0,
                "year_from": 2010,
                "sort_by": "vote_average.desc",
            },
        }
        res1 = client.post("/api/chat", json=payload1)
        assert res1.status_code == 200, f"Error: {res1.text}"
        data1 = res1.json()
        print(f"Reply: {data1['reply']}")
        for m in data1["recommendations"]:
            print(f"  • {m['title']} ({m['year']}) - Rating: {m['rating']} - Reason: {m['reason']}")
            assert float(m["rating"]) >= 7.5, f"Rating {m['rating']} below expected threshold"
            if m["year"] != "N/A":
                assert int(m["year"]) >= 2010, f"Year {m['year']} before 2010"

        # 2. Conversational Filter parsing: Korean movies rated 8+
        print("\n[2] Testing conversational filtering in message: 'Korean movies rated 8+'...")
        payload2 = {"message": "Korean movies rated 8+"}
        res2 = client.post("/api/chat", json=payload2)
        assert res2.status_code == 200
        data2 = res2.json()
        print(f"Reply: {data2['reply']}")
        for m in data2["recommendations"]:
            print(f"  • {m['title']} ({m['year']}) - Rating: {m['rating']}")
            assert float(m["rating"]) >= 7.8

        # 3. Conversational Era Filter: 90s comedy
        print("\n[3] Testing era filter in message: 'comedy movies from the 90s'...")
        payload3 = {"message": "comedy movies from the 90s"}
        res3 = client.post("/api/chat", json=payload3)
        assert res3.status_code == 200
        data3 = res3.json()
        print(f"Reply: {data3['reply']}")
        for m in data3["recommendations"]:
            print(f"  • {m['title']} ({m['year']}) - Rating: {m['rating']}")
            if m["year"] != "N/A":
                assert 1990 <= int(m["year"]) <= 1999

        # 4. Pagination / Follow up with filters: "more"
        print("\n[4] Testing follow-up 'more' with previously applied filters...")
        res4 = client.post("/api/chat", json={"message": "more movies"})
        assert res4.status_code == 200
        data4 = res4.json()
        print(f"Reply: {data4['reply']}")
        ids3 = {m["id"] for m in data3["recommendations"] if m.get("id")}
        ids4 = {m["id"] for m in data4["recommendations"] if m.get("id")}
        assert not ids3.intersection(ids4), "Follow-up batch should contain fresh, non-overlapping movies"
        print("  ✓ Successfully paginated to next batch of filtered movies without duplicates.")

    print("\n" + "=" * 60)
    print("ALL FILTERING TESTS PASSED SUCCESSFULLY! ✅")
    print("=" * 60)

if __name__ == "__main__":
    test_filtering()
