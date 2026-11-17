"""Rule-based intent and entity parser for Movie Assistant."""

import difflib
import re
from typing import Any

POPULAR_TITLES = [
    "Inception",
    "The Matrix",
    "Interstellar",
    "Toy Story",
    "The Dark Knight",
    "Avatar",
    "Titanic",
    "Pulp Fiction",
    "Fight Club",
    "Forrest Gump",
    "The Godfather",
    "Gladiator",
    "The Shawshank Redemption",
    "Oppenheimer",
    "Spider-Man",
    "Avengers",
    "Jurassic Park",
    "Star Wars",
    "The Lion King",
    "Goodfellas",
    "Whiplash",
    "Spirited Away",
]

GENRE_MAP = {
    "action": "Action",
    "adventure": "Adventure",
    "animation": "Animation",
    "animated": "Animation",
    "cartoon": "Animation",
    "comedy": "Comedy",
    "funny": "Comedy",
    "crime": "Crime",
    "documentary": "Documentary",
    "drama": "Drama",
    "family": "Family",
    "fantasy": "Fantasy",
    "history": "History",
    "historical": "History",
    "horror": "Horror",
    "scary": "Horror",
    "music": "Music",
    "musical": "Music",
    "mystery": "Mystery",
    "romance": "Romance",
    "romantic": "Romance",
    "romcom": "Romance",
    "science fiction": "Science Fiction",
    "sci-fi": "Science Fiction",
    "scifi": "Science Fiction",
    "sf": "Science Fiction",
    "thriller": "Thriller",
    "suspense": "Thriller",
    "war": "War",
    "western": "Western",
}

LANGUAGE_MAP = {
    "korean": ("ko", "Korean"),
    "korea": ("ko", "Korean"),
    "k-drama": ("ko", "Korean"),
    "kdrama": ("ko", "Korean"),
    "hindi": ("hi", "Hindi"),
    "bollywood": ("hi", "Hindi"),
    "japanese": ("ja", "Japanese"),
    "japan": ("ja", "Japanese"),
    "anime": ("ja", "Japanese"),
    "spanish": ("es", "Spanish"),
    "spain": ("es", "Spanish"),
    "french": ("fr", "French"),
    "france": ("fr", "French"),
    "german": ("de", "German"),
    "germany": ("de", "German"),
    "italian": ("it", "Italian"),
    "italy": ("it", "Italian"),
    "chinese": ("zh", "Chinese"),
    "china": ("zh", "Chinese"),
    "cantonese": ("cn", "Cantonese"),
    "mandarin": ("zh", "Mandarin"),
    "tamil": ("ta", "Tamil"),
    "kollywood": ("ta", "Tamil"),
    "telugu": ("te", "Telugu"),
    "tollywood": ("te", "Telugu"),
    "malayalam": ("ml", "Malayalam"),
    "mollywood": ("ml", "Malayalam"),
    "kannada": ("kn", "Kannada"),
    "sandalwood": ("kn", "Kannada"),
    "english": ("en", "English"),
    "russian": ("ru", "Russian"),
    "russia": ("ru", "Russian"),
    "turkish": ("tr", "Turkish"),
    "turkey": ("tr", "Turkish"),
    "portuguese": ("pt", "Portuguese"),
    "brazilian": ("pt", "Portuguese"),
    "arabic": ("ar", "Arabic"),
    "swedish": ("sv", "Swedish"),
}


def extract_chat_filters(msg: str) -> dict[str, Any]:
    """Extract conversational filters (rating, era, year, sort) from text."""
    filters: dict[str, Any] = {}

    # 1. Rating filters
    rate_match = re.search(r"\b(?:rated|rating)\s*(?:above|>|>=|over|at\s+least)?\s*([0-9](?:\.[0-9])?)\b", msg)
    if rate_match:
        try:
            filters["min_rating"] = float(rate_match.group(1))
        except ValueError:
            pass
    else:
        plus_match = re.search(r"\b([0-9](?:\.[0-9])?)\s*\+\s*(?:rating|stars?)?\b", msg)
        if plus_match:
            try:
                filters["min_rating"] = float(plus_match.group(1))
            except ValueError:
                pass

    # 2. Era filters (e.g. 90s, 80s, 2010s, 2000s)
    era_match = re.search(r"\b(?:from\s+the\s+|in\s+the\s+)?((?:19)?[5-9]0|20[0-2]0)s\b", msg)
    if era_match:
        era_str = era_match.group(1)
        start_year = int(era_str) if len(era_str) == 4 else int("19" + era_str)
        filters["year_from"] = start_year
        filters["year_to"] = start_year + 9

    # 3. Year filters: "after 2015", "before 2000", "released in 2023"
    after_match = re.search(r"\b(?:after|since)\s+(19[5-9]\d|20[0-2]\d)\b", msg)
    if after_match:
        filters["year_from"] = int(after_match.group(1))

    before_match = re.search(r"\b(?:before|prior\s+to)\s+(19[5-9]\d|20[0-2]\d)\b", msg)
    if before_match:
        filters["year_to"] = int(before_match.group(1))

    in_year_match = re.search(r"\b(?:in|from|released\s+in)\s+(19[5-9]\d|20[0-2]\d)\b", msg)
    if in_year_match and not era_match and not after_match and not before_match:
        yr = int(in_year_match.group(1))
        filters["year_from"] = yr
        filters["year_to"] = yr

    # 4. Sort by
    if re.search(r"\b(most\s+popular|trending|popular)\b", msg):
        filters["sort_by"] = "popularity.desc"

    return filters


def parse_intent(user_message: str) -> dict[str, Any]:
    """Parse user text message into an intent and associated entities.

    Possible intents:
    - recommend_by_title
    - recommend_by_genre
    - recommend_for_user
    - top_rated
    - greeting
    - help
    - unknown
    """
    raw = (user_message or "").strip()
    msg = raw.lower()

    if not msg:
        return {"intent": "greeting", "entities": {}, "filters": {}}

    chat_filters = extract_chat_filters(msg)

    # 1. Greetings (isolated greeting or starting with greeting)
    if re.fullmatch(r"(hi|hello|hey|greetings|howdy|sup|good (morning|afternoon|evening))[!\.]*", msg):
        return {"intent": "greeting", "entities": {}}

    # 2. Help request
    if re.fullmatch(r"(help|commands|what can you do|how does this work|features|options)[!\.\?]*", msg):
        return {"intent": "help", "entities": {}}

    # 3. Follow-up / Request for MORE movies without a specific genre or title
    # e.g., "more", "more movies", "recommend more", "recommend more movies", "show me more", "another one"
    more_patterns = [
        r"^(?:(?:can\s+you\s+)?(?:recommend|suggest|give\s+me|show\s+me)\s+)?(?:some\s+)?more(?:\s+movies?)?[!\.\?]*$",
        r"^(?:more|another|next|different|other)\s*(?:movies?|one|films?)?[!\.\?]*$",
        r"^show\s+more[!\.\?]*$",
        r"^give\s+me\s+more[!\.\?]*$",
    ]
    for pattern in more_patterns:
        if re.search(pattern, msg):
            return {"intent": "more", "entities": {"is_more": True}}

    # 4. Personalized recommendation / seeds ("recommend for me", "recommend based on", etc.)
    seed_patterns = [
        r"(?:recommend\s+(?:for\s+(?:me|user)|personalized)|based\s+on\s+(?:seeds?|favorites?|my\s+likes?)|seeds?:?)\s*(?:based\s+on\s*:?|:\s*)?(.*)",
        r"(?:recommend\s+based\s+on)\s+(.*)",
    ]
    for pattern in seed_patterns:
        match = re.search(pattern, msg)
        if match:
            seed_text = match.group(1).strip()
            # Split by comma or 'and'
            raw_seeds = re.split(r",|\band\b", seed_text)
            seeds = [s.strip(" \"'.;") for s in raw_seeds if s.strip(" \"'.;")]
            if not seeds:
                seeds = ["Inception", "The Dark Knight", "Interstellar"]
            return {"intent": "recommend_for_user", "entities": {"seeds": seeds[:3]}}

    # 4. Top Rated
    top_rated_patterns = [
        r"\b(top\s*rated|best\s*movies?|highest\s*rated|all[\s-]time\s*favorites?|top\s*(?:10|5|movies?)|best\s*films?)\b"
    ]
    for pattern in top_rated_patterns:
        if re.search(pattern, msg):
            return {"intent": "top_rated", "entities": {}}

    # 5. Recommend by Title
    # Explicit title extraction patterns
    title_patterns = [
        r"(?:movies?|films?)\s+(?:like|similar\s+to)\s+[\"']?([^\"'\.\?!]+)[\"']?",
        r"(?:recommend|suggest)\s+(?:(?:something|movies?|films?)\s+)?(?:like|similar\s+to)\s+[\"']?([^\"'\.\?!]+)[\"']?",
        r"(?:more\s+like|similar\s+to|if\s+i\s+like)\s+[\"']?([^\"'\.\?!]+)[\"']?",
        r"like\s+[\"']([^\"']+)[\"']",
    ]
    for pattern in title_patterns:
        match = re.search(pattern, msg)
        if match:
            extracted_title = match.group(1).strip(" \"'.,!?")
            # Remove filler words at end if any
            extracted_title = re.sub(r"\b(please|thanks|thank you)\b.*$", "", extracted_title).strip()
            if extracted_title:
                return {
                    "intent": "recommend_by_title",
                    "entities": {"title": extracted_title},
                }

    # 6. Recommend by Language (with optional Genre)
    for lang_key, (lang_code, lang_name) in sorted(LANGUAGE_MAP.items(), key=lambda x: -len(x[0])):
        pattern = rf"\b{re.escape(lang_key)}\b"
        if re.search(pattern, msg):
            is_more = bool(re.search(r"\b(more|another|different|next)\b", msg))
            # Check if a genre is also specified (e.g., "Korean thriller")
            matched_genre = None
            for g_key, canonical_genre in sorted(GENRE_MAP.items(), key=lambda x: -len(x[0])):
                if re.search(rf"\b{re.escape(g_key)}\b", msg):
                    matched_genre = canonical_genre
                    break
            return {
                "intent": "recommend_by_language",
                "entities": {
                    "language_code": lang_code,
                    "language_name": lang_name,
                    "genre": matched_genre,
                    "is_more": is_more,
                    "filters": chat_filters,
                },
            }

    # 7. Recommend by Genre
    # Look for genre keywords
    for keyword, canonical_genre in sorted(GENRE_MAP.items(), key=lambda x: -len(x[0])):
        pattern = rf"\b{re.escape(keyword)}\b"
        if re.search(pattern, msg):
            is_more = bool(re.search(r"\b(more|another|different|next)\b", msg))
            return {
                "intent": "recommend_by_genre",
                "entities": {"genre": canonical_genre, "is_more": is_more, "filters": chat_filters},
            }

    # 7. Check if user typed a quoted movie title, e.g. "Inception"
    quoted = re.findall(r"[\"']([^\"']+)[\"']", raw)
    if quoted:
        return {
            "intent": "recommend_by_title",
            "entities": {"title": quoted[0].strip()},
        }

    # 8. Fuzzy match against POPULAR_TITLES
    close_matches = difflib.get_close_matches(msg, POPULAR_TITLES, n=1, cutoff=0.7)
    if close_matches:
        return {
            "intent": "recommend_by_title",
            "entities": {"title": close_matches[0]},
        }

    # 9. Fallback: If user types "recommend <something>", assume title
    rec_title_match = re.search(r"recommend\s+(?:movie\s+)?([a-zA-Z0-9\s:_-]+)", msg)
    if rec_title_match:
        cand = rec_title_match.group(1).strip()
        invalid_titles = [
            "a movie", "movies", "something", "anything",
            "more", "more movies", "more movie", "some more", "other movies",
            "another", "different"
        ]
        if cand not in invalid_titles and not any(cand.startswith(w) for w in ["more ", "another "]):
            return {
                "intent": "recommend_by_title",
                "entities": {"title": cand},
            }

    if chat_filters:
        return {
            "intent": "filtered_discovery",
            "entities": {"filters": chat_filters},
        }

    return {"intent": "unknown", "entities": {}}
