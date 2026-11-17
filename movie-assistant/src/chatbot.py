"""MovieAssistant orchestration class connecting intent parser and recommender."""

import logging
from typing import Any, Optional
from .intent_parser import parse_intent
from .recommender import MovieRecommender
from .tmdb_client import TMDBClient

logger = logging.getLogger("chatbot")


class MovieAssistant:
    """Orchestrates conversations, intent parsing, and movie recommendations."""

    def __init__(self, tmdb_key: Optional[str] = None):
        self.client = TMDBClient(tmdb_key)
        self.recommender = MovieRecommender(self.client)
        self.seen_movie_ids: set[int] = set()
        self.last_query: dict[str, Any] = {}
        self.genre_pages: dict[str, int] = {}
        self.language_pages: dict[str, int] = {}
        self.top_rated_page: int = 1
        self.filter_page: int = 1

    def _track_recommendations(self, recs: list[dict[str, Any]]) -> None:
        """Record recommended movie IDs to prevent duplicate recommendations in the session."""
        for r in recs:
            mid = r.get("id")
            if mid:
                self.seen_movie_ids.add(mid)

    def reply(
        self,
        user_message: str,
        filters: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Process user message and return structured response."""
        try:
            parsed = parse_intent(user_message)
            intent = parsed.get("intent", "unknown")
            entities = parsed.get("entities", {})

            # Merge UI filters with conversational chat filters
            active_filters = dict(filters or {})
            chat_filters = entities.get("filters", {})
            for k, v in chat_filters.items():
                if v is not None:
                    active_filters[k] = v

            # 1. Greeting
            if intent == "greeting":
                return {
                    "reply": "Hi! I can recommend movies by title, genre, or from seeds. Try 'movies like Inception'.",
                    "recommendations": [],
                    "intent": intent,
                }

            # 2. Help
            if intent == "help":
                return {
                    "reply": (
                        "I can recommend movies by title, genre, or your favorite seeds!\n"
                        "• By title: 'movies like Inception'\n"
                        "• By genre: 'recommend a comedy'\n"
                        "• Top rated: 'top rated movies'\n"
                        "• By seeds: 'recommend based on Interstellar, Avatar'\n"
                        "• More: 'recommend more movies' or 'more comedy'"
                    ),
                    "recommendations": [],
                    "intent": intent,
                }

            # 3. Unknown intent fallback
            if intent == "unknown":
                return {
                    "reply": "I can recommend by title, genre, or seeds. Try 'movies like The Matrix' or 'recommend a comedy'.",
                    "recommendations": [],
                    "intent": "unknown",
                }

            # For intents requiring live movie data, check if TMDB API is configured
            if not self.client.is_configured:
                return {
                    "reply": "Please configure your TMDB API key in .env to fetch movie recommendations.",
                    "recommendations": [],
                    "intent": intent,
                }

            # 4. Handle "more" / follow-up requests without an explicit new query
            if intent == "more":
                if self.last_query:
                    prev_intent = self.last_query.get("intent")
                    prev_entities = self.last_query.get("entities", {})

                    if prev_intent == "filtered_discovery" or self.last_query.get("filters"):
                        prev_f = self.last_query.get("filters", {})
                        self.filter_page += 1
                        recs = self.recommender.recommend_filtered(
                            prev_f, top_n=5, page=self.filter_page, exclude_ids=self.seen_movie_ids
                        )
                        self._track_recommendations(recs)
                        return {
                            "reply": "Here are more movies matching your filters:",
                            "recommendations": recs,
                            "intent": "filtered_discovery",
                        }

                    if prev_intent == "recommend_by_genre":
                        genre = prev_entities.get("genre", "Comedy")
                        page = self.genre_pages.get(genre, 1)
                        recs = self.recommender.recommend_by_genre(
                            genre, top_n=5, page=page, exclude_ids=self.seen_movie_ids
                        )
                        self.genre_pages[genre] = page + 1
                        self._track_recommendations(recs)
                        return {
                            "reply": f"Here are more top-rated {genre} picks:",
                            "recommendations": recs,
                            "intent": "recommend_by_genre",
                        }

                    if prev_intent == "recommend_by_language":
                        lang_code = prev_entities.get("language_code", "ko")
                        lang_name = prev_entities.get("language_name", "Korean")
                        genre = prev_entities.get("genre")
                        key = f"{lang_code}:{genre or ''}"
                        page = self.language_pages.get(key, 1)
                        recs = self.recommender.recommend_by_language(
                            lang_code,
                            lang_name,
                            genre=genre,
                            top_n=5,
                            page=page,
                            exclude_ids=self.seen_movie_ids,
                        )
                        self.language_pages[key] = page + 1
                        self._track_recommendations(recs)
                        genre_str = f" {genre}" if genre else ""
                        return {
                            "reply": f"Here are more top-rated {lang_name}{genre_str} picks:",
                            "recommendations": recs,
                            "intent": "recommend_by_language",
                        }

                    if prev_intent == "recommend_by_title":
                        title = prev_entities.get("title", "")
                        recs = (
                            self.recommender.recommend_like(title, top_n=5, exclude_ids=self.seen_movie_ids) or []
                        )
                        self._track_recommendations(recs)
                        return {
                            "reply": f"Here are more movies like *{title}*:",
                            "recommendations": recs,
                            "intent": "recommend_by_title",
                        }

                    if prev_intent == "top_rated":
                        self.top_rated_page += 1
                        recs = self.recommender.top_rated(
                            top_n=5, page=self.top_rated_page, exclude_ids=self.seen_movie_ids
                        )
                        self._track_recommendations(recs)
                        return {
                            "reply": "Here are more all-time favorites from TMDB:",
                            "recommendations": recs,
                            "intent": "top_rated",
                        }

                    if prev_intent == "recommend_for_user":
                        seeds = prev_entities.get("seeds", [])
                        raw_recs = self.recommender.recommend_for_user(seeds, top_n=10)
                        recs = [r for r in raw_recs if r.get("id") not in self.seen_movie_ids][:5]
                        self._track_recommendations(recs)
                        return {
                            "reply": "Here are more personalized picks based on your seeds:",
                            "recommendations": recs,
                            "intent": "recommend_for_user",
                        }

                # If no previous query, default to top rated
                recs = self.recommender.top_rated(top_n=5, page=self.top_rated_page, exclude_ids=self.seen_movie_ids)
                self.top_rated_page += 1
                self._track_recommendations(recs)
                return {
                    "reply": "Here are top-rated movies you might like:",
                    "recommendations": recs,
                    "intent": "top_rated",
                }

            # 5. Recommend by Title
            if intent == "recommend_by_title":
                title = entities.get("title", "").strip()
                if not title:
                    return {
                        "reply": "Which movie would you like recommendations for? (e.g., 'movies like Inception')",
                        "recommendations": [],
                        "intent": intent,
                    }

                recs = self.recommender.recommend_like(title, top_n=5, exclude_ids=self.seen_movie_ids)
                if recs is None:
                    return {
                        "reply": f"I couldn't find '{title}' on TMDB. Try another title?",
                        "recommendations": [],
                        "intent": intent,
                    }
                if not recs:
                    # If we ran out of unseen similar movies, clear exclusion for this title
                    recs = self.recommender.recommend_like(title, top_n=5, exclude_ids=None)
                    if not recs:
                        return {
                            "reply": f"I found '{title}', but couldn't find similar recommendations right now. Try another title?",
                            "recommendations": [],
                            "intent": intent,
                        }

                self._track_recommendations(recs)
                self.last_query = {"intent": intent, "entities": {"title": title}}

                prefix = "Here are more" if entities.get("is_more") else "Because you liked"
                return {
                    "reply": f"{prefix} *{title}*, try:",
                    "recommendations": recs,
                    "intent": intent,
                }

            # 6. Recommend by Genre
            if intent == "recommend_by_genre":
                genre = entities.get("genre", "Comedy")
                is_more = entities.get("is_more", False)
                page = self.genre_pages.get(genre, 1)

                active_filters["genre"] = genre
                has_extra_filters = any(
                    k in active_filters for k in ["year_from", "year_to", "min_rating", "language", "sort_by"]
                )

                if has_extra_filters:
                    recs = self.recommender.recommend_filtered(
                        active_filters, top_n=5, page=page, exclude_ids=self.seen_movie_ids
                    )
                else:
                    recs = self.recommender.recommend_by_genre(
                        genre, top_n=5, page=page, exclude_ids=self.seen_movie_ids
                    )

                self.genre_pages[genre] = page + 1
                self._track_recommendations(recs)
                self.last_query = {"intent": intent, "entities": {"genre": genre}, "filters": active_filters}

                prefix = "Here are more" if is_more or page > 1 else "Here are"
                filter_suffix = ""
                if active_filters.get("year_from") and active_filters.get("year_to"):
                    filter_suffix = f" from {active_filters['year_from']}–{active_filters['year_to']}"
                elif active_filters.get("min_rating"):
                    filter_suffix = f" (★ {active_filters['min_rating']}+)"
                return {
                    "reply": f"{prefix} top-rated {genre} picks{filter_suffix}:",
                    "recommendations": recs,
                    "intent": intent,
                }

            # 7. Recommend by Language (e.g., Korean, Hindi, Japanese, Spanish)
            if intent == "recommend_by_language":
                lang_code = entities.get("language_code", "ko")
                lang_name = entities.get("language_name", "Korean")
                genre = entities.get("genre")
                is_more = entities.get("is_more", False)
                key = f"{lang_code}:{genre or ''}"
                page = self.language_pages.get(key, 1)

                active_filters["language"] = lang_code
                active_filters["language_name"] = lang_name
                if genre:
                    active_filters["genre"] = genre

                has_extra_filters = any(
                    k in active_filters for k in ["year_from", "year_to", "min_rating", "sort_by"]
                )

                if has_extra_filters:
                    recs = self.recommender.recommend_filtered(
                        active_filters, top_n=5, page=page, exclude_ids=self.seen_movie_ids
                    )
                else:
                    recs = self.recommender.recommend_by_language(
                        lang_code,
                        lang_name,
                        genre=genre,
                        top_n=5,
                        page=page,
                        exclude_ids=self.seen_movie_ids,
                    )

                self.language_pages[key] = page + 1
                self._track_recommendations(recs)
                self.last_query = {"intent": intent, "entities": entities, "filters": active_filters}

                prefix = "Here are more" if is_more or page > 1 else "Here are"
                genre_str = f" {genre}" if genre else ""
                filter_suffix = ""
                if active_filters.get("min_rating"):
                    filter_suffix = f" (★ {active_filters['min_rating']}+)"
                elif active_filters.get("year_from") and active_filters.get("year_to"):
                    filter_suffix = f" from {active_filters['year_from']}–{active_filters['year_to']}"

                return {
                    "reply": f"{prefix} top-rated {lang_name}{genre_str} picks{filter_suffix}:",
                    "recommendations": recs,
                    "intent": intent,
                }

            # 7. Recommend for User (Seeds)
            if intent == "recommend_for_user":
                seeds = entities.get("seeds", [])
                raw_recs = self.recommender.recommend_for_user(seeds, top_n=10)
                recs = [r for r in raw_recs if r.get("id") not in self.seen_movie_ids][:5]
                if not recs:
                    recs = raw_recs[:5]

                self._track_recommendations(recs)
                self.last_query = {"intent": intent, "entities": {"seeds": seeds}}

                seed_str = ", ".join(seeds) if seeds else "your favorites"
                return {
                    "reply": f"Personalized picks based on your seeds ({seed_str}):",
                    "recommendations": recs,
                    "intent": intent,
                }

            # 8. Top Rated
            if intent == "top_rated":
                if active_filters:
                    self.filter_page = 1
                    recs = self.recommender.recommend_filtered(
                        active_filters, top_n=5, page=self.filter_page, exclude_ids=self.seen_movie_ids
                    )
                    self._track_recommendations(recs)
                    self.last_query = {"intent": "filtered_discovery", "filters": active_filters}
                    return {
                        "reply": "Here are top-rated movies matching your filters:",
                        "recommendations": recs,
                        "intent": "filtered_discovery",
                    }

                recs = self.recommender.top_rated(
                    top_n=5, page=self.top_rated_page, exclude_ids=self.seen_movie_ids
                )
                self.top_rated_page += 1
                self._track_recommendations(recs)
                self.last_query = {"intent": intent, "entities": {}}

                return {
                    "reply": "All-time favorites from TMDB:",
                    "recommendations": recs,
                    "intent": intent,
                }

            # 9. Filtered Discovery (via UI filter panel or conversational criteria)
            if intent == "filtered_discovery" or active_filters:
                self.filter_page = 1
                recs = self.recommender.recommend_filtered(
                    active_filters, top_n=5, page=self.filter_page, exclude_ids=self.seen_movie_ids
                )
                self._track_recommendations(recs)
                self.last_query = {"intent": "filtered_discovery", "filters": active_filters}

                # Construct dynamic description
                desc_parts = []
                if active_filters.get("genre"):
                    desc_parts.append(str(active_filters["genre"]))
                if active_filters.get("language_name"):
                    desc_parts.append(str(active_filters["language_name"]))
                elif active_filters.get("language"):
                    desc_parts.append(f"Language: {active_filters['language'].upper()}")
                if active_filters.get("min_rating"):
                    desc_parts.append(f"★ {active_filters['min_rating']}+")
                if active_filters.get("year_from") and active_filters.get("year_to"):
                    if active_filters["year_from"] == active_filters["year_to"]:
                        desc_parts.append(f"Year {active_filters['year_from']}")
                    else:
                        desc_parts.append(f"{active_filters['year_from']}–{active_filters['year_to']}")
                elif active_filters.get("year_from"):
                    desc_parts.append(f"{active_filters['year_from']}+")
                elif active_filters.get("year_to"):
                    desc_parts.append(f"Pre-{active_filters['year_to']}")

                filter_text = f" ({', '.join(desc_parts)})" if desc_parts else ""
                return {
                    "reply": f"Here are movies matching your filters{filter_text}:",
                    "recommendations": recs,
                    "intent": "filtered_discovery",
                }

            # 10. Fallback / Unknown intent
            return {
                "reply": "I can recommend by title, genre, or seeds. Try 'movies like The Matrix' or 'recommend a comedy'.",
                "recommendations": [],
                "intent": "unknown",
            }

        except Exception as exc:
            logger.error("Error generating assistant reply: %s", exc, exc_info=True)
            return {
                "reply": "I'm having trouble reaching the movie database right now. Please try again in a moment.",
                "recommendations": [],
                "intent": "error",
            }
