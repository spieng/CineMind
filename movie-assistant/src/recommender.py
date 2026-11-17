"""Movie Recommender engine mapping intents to TMDB calls and ranked results."""

import logging
from typing import Any, Optional
from .tmdb_client import TMDBClient

logger = logging.getLogger("recommender")


class MovieRecommender:
    """Orchestrates movie recommendations via TMDBClient."""

    def __init__(self, client: TMDBClient):
        self.client = client

    def _format_movie(self, movie: dict[str, Any], reason: str) -> dict[str, Any]:
        """Convert a raw TMDB movie dict into the standardized Recommendation schema."""
        title = movie.get("title") or movie.get("name") or "Unknown Title"

        # Extract 4-digit release year
        release_date = movie.get("release_date") or ""
        year = release_date[:4] if len(release_date) >= 4 else "N/A"

        # Resolve genres
        genres: list[str] = []
        if "genres" in movie and isinstance(movie["genres"], list):
            genres = [g.get("name") for g in movie["genres"] if isinstance(g, dict) and g.get("name")]
        elif "genre_ids" in movie and isinstance(movie["genre_ids"], list):
            genres = self.client.genre_names_from_ids(movie["genre_ids"])

        # Format rating
        vote_avg = movie.get("vote_average")
        try:
            rating = round(float(vote_avg), 1) if vote_avg is not None else 0.0
        except (ValueError, TypeError):
            rating = 0.0

        poster_url = self.client.build_poster_url(movie.get("poster_path"))

        return {
            "id": movie.get("id"),
            "title": title,
            "year": year,
            "genres": genres,
            "rating": rating,
            "poster_url": poster_url,
            "reason": reason,
        }

    def recommend_like(
        self,
        title: str,
        top_n: int = 5,
        exclude_ids: Optional[set[int]] = None,
    ) -> Optional[list[dict[str, Any]]]:
        """Recommend movies similar to a given title.

        Returns None if title cannot be found on TMDB.
        """
        matched = self.client.search_movie(title)
        if not matched:
            return None

        movie_id = matched["id"]
        matched_title = matched.get("title", title)
        excluded = set(exclude_ids or set())
        excluded.add(movie_id)

        # Try recommendations endpoint first
        recs = self.client.get_recommendations(movie_id, page=1)

        # Fallback to similar endpoint if recommendations are empty
        if not recs:
            logger.info("Recommendations empty for ID %d, falling back to /similar.", movie_id)
            recs = self.client.get_similar(movie_id)

        # Filter out already seen movies
        unseen = [m for m in recs if m.get("id") not in excluded]

        # If not enough, fetch page 2
        if len(unseen) < top_n:
            more_recs = self.client.get_recommendations(movie_id, page=2)
            unseen.extend([m for m in more_recs if m.get("id") not in excluded and m not in unseen])

        results: list[dict[str, Any]] = []
        for item in unseen[:top_n]:
            results.append(
                self._format_movie(
                    item,
                    reason=f"Because you liked {matched_title}",
                )
            )

        return results

    def recommend_by_genre(
        self,
        genre: str,
        top_n: int = 5,
        page: int = 1,
        exclude_ids: Optional[set[int]] = None,
    ) -> list[dict[str, Any]]:
        """Discover top-rated movies for a given genre, avoiding duplicates."""
        excluded = exclude_ids or set()
        raw_movies = self.client.discover_by_genre(genre, page=page)

        # Filter out already seen movies
        unseen = [m for m in raw_movies if m.get("id") not in excluded]

        # If we have fewer than top_n unseen movies on this page, fetch the next page
        current_page = page
        while len(unseen) < top_n and current_page < page + 3:
            current_page += 1
            next_batch = self.client.discover_by_genre(genre, page=current_page)
            if not next_batch:
                break
            for m in next_batch:
                if m.get("id") not in excluded and m.get("id") not in [u.get("id") for u in unseen]:
                    unseen.append(m)

        # Ensure sorted by rating descending
        sorted_movies = sorted(
            unseen,
            key=lambda m: float(m.get("vote_average") or 0.0),
            reverse=True,
        )

        results: list[dict[str, Any]] = []
        for item in sorted_movies[:top_n]:
            results.append(
                self._format_movie(
                    item,
                    reason=f"Top-rated {genre.capitalize()} pick",
                )
            )

        return results

    def recommend_by_language(
        self,
        language_code: str,
        language_name: str,
        genre: Optional[str] = None,
        top_n: int = 5,
        page: int = 1,
        exclude_ids: Optional[set[int]] = None,
    ) -> list[dict[str, Any]]:
        """Discover top-rated movies for a specific language and optional genre."""
        excluded = exclude_ids or set()
        raw_movies = self.client.discover_by_language(language_code, genre_name=genre, page=page)

        unseen = [m for m in raw_movies if m.get("id") not in excluded]

        current_page = page
        while len(unseen) < top_n and current_page < page + 3:
            current_page += 1
            next_batch = self.client.discover_by_language(
                language_code, genre_name=genre, page=current_page
            )
            if not next_batch:
                break
            for m in next_batch:
                if m.get("id") not in excluded and m.get("id") not in [u.get("id") for u in unseen]:
                    unseen.append(m)

        sorted_movies = sorted(
            unseen,
            key=lambda m: float(m.get("vote_average") or 0.0),
            reverse=True,
        )

        reason = (
            f"Top-rated {language_name} {genre.capitalize()} pick"
            if genre
            else f"Top-rated {language_name} cinema pick"
        )

        results: list[dict[str, Any]] = []
        for item in sorted_movies[:top_n]:
            results.append(self._format_movie(item, reason=reason))

        return results

    def recommend_filtered(
        self,
        filters: dict[str, Any],
        top_n: int = 5,
        page: int = 1,
        exclude_ids: Optional[set[int]] = None,
    ) -> list[dict[str, Any]]:
        """Multi-filter recommendation with pagination and deduplication."""
        excluded = exclude_ids or set()
        raw_movies = self.client.discover_movies(filters, page=page)

        unseen = [m for m in raw_movies if m.get("id") not in excluded]

        current_page = page
        while len(unseen) < top_n and current_page < page + 3:
            current_page += 1
            next_batch = self.client.discover_movies(filters, page=current_page)
            if not next_batch:
                break
            for m in next_batch:
                if m.get("id") not in excluded and m.get("id") not in [u.get("id") for u in unseen]:
                    unseen.append(m)

        # Build dynamic reason based on active filters
        parts = []
        if filters.get("genre"):
            parts.append(str(filters["genre"]).capitalize())
        if filters.get("language_name"):
            parts.append(str(filters["language_name"]).capitalize())
        elif filters.get("language"):
            parts.append(f"Language: {filters['language'].upper()}")
        if filters.get("min_rating"):
            parts.append(f"★ {filters['min_rating']}+")
        if filters.get("year_from") and filters.get("year_to"):
            if filters["year_from"] == filters["year_to"]:
                parts.append(f"Year {filters['year_from']}")
            else:
                parts.append(f"{filters['year_from']}–{filters['year_to']}")
        elif filters.get("year_from"):
            parts.append(f"{filters['year_from']}+")
        elif filters.get("year_to"):
            parts.append(f"Pre-{filters['year_to']}")

        filter_desc = " • ".join(parts) if parts else "Selected Filters"
        reason = f"Matches filters ({filter_desc})"

        results: list[dict[str, Any]] = []
        for item in unseen[:top_n]:
            results.append(self._format_movie(item, reason=reason))

        return results

    def recommend_for_user(self, seed_titles: list[str], top_n: int = 5) -> list[dict[str, Any]]:
        """Personalized picks aggregated from up to 3 seed titles."""
        if not seed_titles:
            seed_titles = ["Inception", "The Dark Knight", "Interstellar"]

        seeds = seed_titles[:3]
        aggregated_movies: dict[int, dict[str, Any]] = {}

        for seed in seeds:
            matched = self.client.search_movie(seed)
            if not matched:
                continue
            movie_id = matched["id"]
            matched_title = matched.get("title", seed)

            recs = self.client.get_recommendations(movie_id)
            if not recs:
                recs = self.client.get_similar(movie_id)

            for item in recs:
                item_id = item.get("id")
                if not item_id or item_id == movie_id:
                    continue
                if item_id not in aggregated_movies:
                    aggregated_movies[item_id] = {
                        "movie": item,
                        "source_seeds": [matched_title],
                        "rating": float(item.get("vote_average") or 0.0),
                    }
                else:
                    if matched_title not in aggregated_movies[item_id]["source_seeds"]:
                        aggregated_movies[item_id]["source_seeds"].append(matched_title)

        if not aggregated_movies:
            # Fallback to top rated if seeds couldn't be resolved
            return self.top_rated(top_n=top_n)

        # Rank by number of overlapping seeds first, then vote_average
        ranked = sorted(
            aggregated_movies.values(),
            key=lambda x: (len(x["source_seeds"]), x["rating"]),
            reverse=True,
        )

        results: list[dict[str, Any]] = []
        for entry in ranked[:top_n]:
            sources = ", ".join(entry["source_seeds"])
            results.append(
                self._format_movie(
                    entry["movie"],
                    reason=f"Matches your taste in {sources}",
                )
            )

        return results

    def top_rated(
        self,
        top_n: int = 5,
        page: int = 1,
        exclude_ids: Optional[set[int]] = None,
    ) -> list[dict[str, Any]]:
        """Fetch all-time top-rated movies, avoiding duplicates."""
        excluded = exclude_ids or set()
        raw_movies = self.client.get_top_rated(page=page)

        unseen = [m for m in raw_movies if m.get("id") not in excluded]
        if len(unseen) < top_n:
            more = self.client.get_top_rated(page=page + 1)
            unseen.extend([m for m in more if m.get("id") not in excluded and m not in unseen])

        results: list[dict[str, Any]] = []
        for item in unseen[:top_n]:
            results.append(
                self._format_movie(
                    item,
                    reason="All-time TMDB favorite",
                )
            )

        return results
