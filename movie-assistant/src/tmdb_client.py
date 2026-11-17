"""TMDB API HTTP client wrapper with caching and rate limit guard."""

import datetime
import logging
import time
from typing import Any, Optional
import requests

logger = logging.getLogger("tmdb_client")
logging.basicConfig(level=logging.INFO)

BASE_URL = "https://api.themoviedb.org/3"
POSTER_BASE_URL = "https://image.tmdb.org/t/p/w200"
CACHE_TTL_SECONDS = 3600  # 1 hour
DAILY_LIMIT = 1000
WARNING_THRESHOLD = 800


class TMDBClient:
    """HTTP client wrapper for TMDB v3 API.

    Features:
    - In-memory dictionary cache with 1-hour TTL.
    - Retry logic with backoff for 429 Too Many Requests responses.
    - Daily call tracking with warning threshold logging.
    - Bearer authentication header support.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key.strip() if api_key and api_key.strip() else None
        if self.api_key == "your_key_here":
            self.api_key = None

        self.base_url = BASE_URL
        self.poster_base_url = POSTER_BASE_URL
        self.cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self.ttl_seconds = CACHE_TTL_SECONDS

        # Rate limit and metric tracking
        self.api_calls_today = 0
        self.current_date = datetime.date.today()
        self.session = requests.Session()
        self._genre_name_to_id: dict[str, int] = {}
        self._genre_id_to_name: dict[int, str] = {}

    @property
    def is_configured(self) -> bool:
        """Check whether a non-empty API key is configured."""
        return bool(self.api_key)

    def _check_daily_limit(self) -> None:
        """Track daily API call counter and warn if approaching threshold."""
        today = datetime.date.today()
        if today != self.current_date:
            self.current_date = today
            self.api_calls_today = 0

        self.api_calls_today += 1
        if self.api_calls_today > WARNING_THRESHOLD:
            logger.warning(
                "Approaching daily TMDB request limit: %d requests made today (> %d threshold).",
                self.api_calls_today,
                WARNING_THRESHOLD,
            )

    def _get(self, endpoint: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Execute a GET request with caching, Bearer authentication, and 429 retries."""
        params_dict = params or {}
        sorted_params = tuple(sorted((str(k), str(v)) for k, v in params_dict.items()))
        cache_key = f"{endpoint}:{sorted_params}"

        now = time.time()
        # Check cache
        if cache_key in self.cache:
            timestamp, cached_data = self.cache[cache_key]
            if now - timestamp < self.ttl_seconds:
                logger.debug("Cache hit for key: %s", cache_key)
                return cached_data
            del self.cache[cache_key]

        if not self.is_configured:
            raise ValueError("TMDB_API_KEY is missing or invalid. Please configure it in your .env file.")

        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

        # For compatibility with standard TMDB 32-char hex API keys
        req_params = dict(params_dict)
        if self.api_key and len(self.api_key) <= 32 and "api_key" not in req_params:
            req_params["api_key"] = self.api_key

        max_retries = 2
        last_exception: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                self._check_daily_limit()
                response = self.session.get(url, headers=headers, params=req_params, timeout=10.0)

                if response.status_code == 429:
                    if attempt < max_retries:
                        logger.warning("Received 429 Too Many Requests from TMDB. Retrying in 2 seconds...")
                        time.sleep(2.0)
                        continue
                    response.raise_for_status()

                response.raise_for_status()
                data: dict[str, Any] = response.json()

                # Store in cache
                self.cache[cache_key] = (time.time(), data)
                return data

            except requests.RequestException as exc:
                last_exception = exc
                if attempt < max_retries:
                    status = getattr(exc.response, "status_code", None)
                    wait_time = 2.0 if status == 429 else 1.5
                    logger.warning("Request error (%s). Retrying attempt %d in %.1fs...", exc, attempt + 1, wait_time)
                    time.sleep(wait_time)
                    # Recreate session in case connection pool had closed socket
                    self.session = requests.Session()
                    continue
                break

        logger.error("TMDB API request failed for %s: %s", endpoint, last_exception)
        raise RuntimeError(f"TMDB API request failed: {last_exception}") from last_exception

    def search_movie(self, title: str) -> Optional[dict[str, Any]]:
        """Search movie by title and return the first matching movie."""
        if not title or not title.strip():
            return None

        data = self._get("/search/movie", {"query": title.strip(), "language": "en-US"})
        results = data.get("results", [])
        if not results:
            return None

        first = results[0]
        return {
            "id": first.get("id"),
            "title": first.get("title"),
            "release_date": first.get("release_date"),
            "vote_average": first.get("vote_average"),
            "poster_path": first.get("poster_path"),
            "overview": first.get("overview", ""),
            "genre_ids": first.get("genre_ids", []),
        }

    def get_movie_details(self, movie_id: int) -> dict[str, Any]:
        """Fetch full details for a movie."""
        return self._get(f"/movie/{movie_id}", {"append_to_response": "genres"})

    def get_recommendations(self, movie_id: int, page: int = 1) -> list[dict[str, Any]]:
        """Get recommended movies for a given movie ID."""
        data = self._get(f"/movie/{movie_id}/recommendations", {"page": page})
        return data.get("results", [])

    def get_similar(self, movie_id: int) -> list[dict[str, Any]]:
        """Get similar movies as fallback for a movie ID."""
        data = self._get(f"/movie/{movie_id}/similar")
        return data.get("results", [])

    def _load_genre_map(self) -> None:
        """Fetch and cache genre name to ID mapping."""
        if self._genre_name_to_id:
            return
        data = self._get("/genre/movie/list", {"language": "en-US"})
        genres = data.get("genres", [])
        for g in genres:
            gid = g["id"]
            gname = g["name"].strip()
            self._genre_name_to_id[gname.lower()] = gid
            self._genre_id_to_name[gid] = gname

        # Aliases
        aliases = {
            "sci-fi": "science fiction",
            "scifi": "science fiction",
            "sf": "science fiction",
            "romcom": "romance",
            "animated": "animation",
        }
        for alias, canonical in aliases.items():
            if canonical in self._genre_name_to_id:
                self._genre_name_to_id[alias] = self._genre_name_to_id[canonical]

    def genre_names_from_ids(self, genre_ids: list[int]) -> list[str]:
        """Resolve a list of genre IDs to names."""
        try:
            self._load_genre_map()
        except Exception:
            return []
        return [self._genre_id_to_name[gid] for gid in genre_ids if gid in self._genre_id_to_name]

    def discover_by_genre(self, genre_name: str, page: int = 1) -> list[dict[str, Any]]:
        """Discover movies by genre name."""
        self._load_genre_map()
        normalized = genre_name.strip().lower()

        genre_id = self._genre_name_to_id.get(normalized)
        if not genre_id:
            # Substring match if exact match not found
            for name, gid in self._genre_name_to_id.items():
                if normalized in name or name in normalized:
                    genre_id = gid
                    break

        if not genre_id:
            logger.warning("Genre '%s' not recognized.", genre_name)
            return []

        data = self._get(
            "/discover/movie",
            {
                "with_genres": genre_id,
                "sort_by": "vote_average.desc",
                "vote_count.gte": 100,
                "language": "en-US",
                "page": page,
            },
        )
        return data.get("results", [])

    def discover_by_language(
        self,
        language_code: str,
        genre_name: Optional[str] = None,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """Discover movies by original language (ISO 639-1 code) and optional genre."""
        params: dict[str, Any] = {
            "with_original_language": language_code.strip().lower(),
            "sort_by": "vote_average.desc",
            "vote_count.gte": 150,
            "language": "en-US",
            "page": page,
        }

        if genre_name:
            self._load_genre_map()
            gid = self._genre_name_to_id.get(genre_name.strip().lower())
            if gid:
                params["with_genres"] = gid

        data = self._get("/discover/movie", params)
        return data.get("results", [])

    def discover_movies(
        self,
        filters: Optional[dict[str, Any]] = None,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """Discover movies using dynamic multi-criteria filters."""
        f = filters or {}
        sort_by = f.get("sort_by") or "vote_average.desc"
        params: dict[str, Any] = {
            "language": "en-US",
            "page": page,
            "sort_by": sort_by,
        }

        # Language filter
        lang = f.get("language")
        if lang:
            params["with_original_language"] = str(lang).strip().lower()

        # Genre filter
        genre_val = f.get("genre") or f.get("genre_name")
        if genre_val:
            self._load_genre_map()
            gid = self._genre_name_to_id.get(str(genre_val).strip().lower())
            if gid:
                params["with_genres"] = gid

        # Rating filter
        min_rating = f.get("min_rating")
        if min_rating is not None:
            try:
                params["vote_average.gte"] = float(min_rating)
            except (ValueError, TypeError):
                pass

        # Year range filters
        year_from = f.get("year_from")
        if year_from:
            try:
                params["primary_release_date.gte"] = f"{int(year_from):04d}-01-01"
            except (ValueError, TypeError):
                pass

        year_to = f.get("year_to")
        if year_to:
            try:
                params["primary_release_date.lte"] = f"{int(year_to):04d}-12-31"
            except (ValueError, TypeError):
                pass

        # Adaptive vote_count threshold to ensure high quality while avoiding zero results
        if year_from and int(year_from) >= 2024:
            params["vote_count.gte"] = 30
        elif params.get("with_original_language") and params["with_original_language"] != "en":
            params["vote_count.gte"] = 80
        else:
            params["vote_count.gte"] = 100

        data = self._get("/discover/movie", params)
        return data.get("results", [])

    def get_top_rated(self, page: int = 1) -> list[dict[str, Any]]:
        """Fetch top-rated movies."""
        data = self._get("/movie/top_rated", {"language": "en-US", "page": page})
        return data.get("results", [])

    def build_poster_url(self, path: Optional[str]) -> Optional[str]:
        """Build full poster image URL from TMDB poster_path."""
        if path:
            return f"{self.poster_base_url}{path}"
        return None

    def get_metrics(self) -> dict[str, Any]:
        """Return cache and API usage metrics."""
        remaining = max(0, DAILY_LIMIT - self.api_calls_today)
        return {
            "cache_size": len(self.cache),
            "api_calls_today": self.api_calls_today,
            "rate_limit_remaining": f"{remaining} / {DAILY_LIMIT} daily remaining (est.)",
        }
