# 🎬 CineMind AI - Movie Recommender Chatbot

A live, text-based Movie Recommender Chatbot built for a college AI lab project. Powered by FastAPI and the official TMDB (The Movie Database) live API with intelligent response caching, rate-limiting safeguards, rule-based intent parsing, and a vanilla HTML/CSS/JS frontend.

---

## 🏗️ Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                   Browser (Vanilla HTML/CSS/JS)             │
│            • Live Status   • Chat Feed   • Poster Cards     │
└──────────────────────────────┬──────────────────────────────┘
                               │  POST /api/chat
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                        │
│                 (api/main.py, api/routes.py)                │
└──────────────────────────────┬──────────────────────────────┘
                               │  reply(message)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    MovieAssistant Orchestrator              │
│                         (src/chatbot.py)                    │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
               ▼                              ▼
    ┌──────────────────────┐      ┌─────────────────────────┐
    │     IntentParser     │      │     MovieRecommender    │
    │ (src/intent_parser)  │      │   (src/recommender.py)  │
    └──────────────────────┘      └───────────┬─────────────┘
                                              │
                                              ▼
                                  ┌─────────────────────────┐
                                  │       TMDBClient        │
                                  │  • In-Memory 1-Hour TTL │
                                  │  • 429 Retry Backoff    │
                                  │  • Request Guard & Warn │
                                  └───────────┬─────────────┘
                                              │  Bearer Auth
                                              ▼
                                 ┌──────────────────────────┐
                                 │   TMDB Live REST API v3  │
                                 │ (api.themoviedb.org/3)   │
                                 └──────────────────────────┘
```

---

## 🔑 How to Get a Free TMDB API Key

1. **Sign Up**: Go to [https://www.themoviedb.org/signup](https://www.themoviedb.org/signup) and create a free account.
2. **Verify Email**: Check your inbox and click the verification link sent by TMDB.
3. **Navigate to API Settings**: Log in and visit [https://www.themoviedb.org/settings/api](https://www.themoviedb.org/settings/api).
4. **Request an API Key**:
   - Click **Create** or **Request an API Key**.
   - Select **Developer** (free for educational / personal projects).
   - Accept the terms of service.
   - Fill in simple details (Application Name: e.g., "College AI Movie Recommender", Application URL: `http://localhost:8000`, Summary: "College AI Lab Project").
5. **Copy Your Key**:
   - Once approved (instantly), copy your **API Key (v3 auth)** (a 32-character hex string) or your **API Read Access Token (v4 auth)**. Either one is supported!
6. **Save to `.env`**:
   - In the project directory, open `.env` and paste your key:
     ```bash
     TMDB_API_KEY=your_copied_key_here
     ```

---

## 🚀 Setup & Installation

### 1. Prerequisites
- Python 3.10+ installed

### 2. Clone or Enter Project Directory
```bash
cd movie-assistant
```

### 3. Create Environment File
Copy `.env.example` to `.env`:
```bash
# Windows PowerShell:
Copy-Item .env.example .env

# Linux / macOS:
cp .env.example .env
```
Edit `.env` and insert your TMDB API key:
```ini
TMDB_API_KEY=your_key_here
```
*(Note: If you start without a key, the server runs in graceful degraded mode with clear setup instructions.)*

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Run the Server
```bash
python run.py
```
The server will start at:
- **Chatbot Web Interface**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger API Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative ReDoc Docs**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 💬 Sample Queries

| Query Type | Example Prompt | Description |
| :--- | :--- | :--- |
| **Similar by Title** | `movies like Inception` | Searches TMDB for "Inception", queries `/movie/{id}/recommendations`, falls back to `/similar` |
| **Genre Discovery** | `recommend a comedy` | Maps "comedy" to Genre ID 35, queries `/discover/movie` sorted by rating |
| **Language Discovery** | `recommend a Korean movie` / `top Hindi movies` | Uses TMDB's `with_original_language` parameter (Korean, Hindi, Japanese, Spanish, French, etc.) |
| **Multi-Filter Chat** | `comedy movies from the 90s` / `Korean movies rated 8+` | Combines language, genre, minimum rating, and release eras directly from text |
| **Interactive UI Filters**| Use the top `⚙️ Filters` drawer | Select Genre, Language, Min Rating (★ 7.0–8.5+), Era (2020s, 90s, Classic), and Sort By |
| **Language + Genre** | `recommend a Spanish comedy` | Discovers movies matching both language code and genre ID |
| **Top-Rated** | `top rated movies` | Fetches TMDB's all-time highest-rated movies |
| **Personalized Seeds**| `recommend based on Interstellar, Avatar` | Aggregates and ranks recommendations across up to 3 seed movies |
| **Follow-Up / More** | `recommend more movies` / `more comedy` | Paginates through TMDB results, excluding already-seen movies |
| **Greeting & Help** | `hello` / `help` | Welcomes user and explains available commands |
| **Graceful Fallback**| `asdfgh` | Handles unknown queries with helpful prompt suggestions |

---

## 🧠 Design Decisions

### 1. Why Live TMDB API Instead of Static Datasets?
- **Always Up-to-Date**: Static datasets (like Kaggle or MovieLens 100k) become outdated quickly and do not include new releases, trending films, or accurate current ratings.
- **Rich Recommendation Graph**: TMDB provides dedicated endpoints (`/movie/{id}/recommendations` and `/movie/{id}/similar`) generated from machine-learning algorithms and community viewing habits.
- **High-Resolution Media & Posters**: TMDB hosts official movie poster images, release dates, and structured genre tags directly consumable via CDN URLs without local asset storage.
- **Zero Heavy Downloads**: Eliminates the requirement to download, unpack, or load multi-gigabyte CSV or SQLite datasets into memory.

### 2. How Rate Limits & Caching are Handled
- **In-Memory Response Cache**: Every TMDB API call is cached in memory (`dict` keyed by endpoint and sorted query parameters) with a **1-hour TTL** (Time To Live). Repeated queries (such as popular titles or genre lists) return instantaneously from cache without consuming rate limits.
- **429 Exponential Backoff**: If TMDB returns HTTP status `429 (Too Many Requests)`, the client automatically pauses (2s) and retries up to 2 times before failing.
- **Daily Request Budget Tracking**: The client monitors cumulative requests per calendar day against TMDB's free-tier threshold and logs proactive warnings when exceeding 800 requests.

### 3. Rule-Based Intent Parser (Zero Heavy Dependencies)
- Avoids large NLP runtimes (spaCy, PyTorch, Transformers) to ensure lightning-fast startup and portability on lab machines.
- Utilizes regular expressions, canonical genre mapping, seed title splitting, and Python's built-in `difflib` for fuzzy matching against popular titles.

---

## 📂 Project Structure

```text
movie-assistant/
├── .env.example                 # TMDB_API_KEY=your_key_here
├── .env                         # Local environment file (API keys)
├── src/
│   ├── __init__.py
│   ├── tmdb_client.py           # HTTP wrapper + cache + rate-limit guard
│   ├── recommender.py           # intent → API calls → ranked results
│   ├── intent_parser.py         # rule-based intent + entity extraction
│   └── chatbot.py               # MovieAssistant orchestration
├── api/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app & static file mounting
│   ├── schemas.py               # Pydantic models
│   └── routes.py                # /api/chat, /api/health, /api/metrics, /api/examples
├── templates/
│   └── index.html               # Semantic HTML UI layout
├── static/
│   ├── css/style.css            # Vanilla CSS styling with cinematic dark theme
│   └── js/chat.js               # Vanilla JS chat controller & card renderer
├── tests/
│   ├── sanity_tmdb.py           # Layer A verification
│   ├── sanity_chatbot.py        # Layer B verification
│   └── sanity_api.py            # Layer C verification
├── run.py                       # Server runner
├── requirements.txt             # Pinned project dependencies
└── README.md                    # Documentation & lab guide
```

---

## 🧪 Testing Layers

Run the test suite for each layer:
```bash
# Layer A: TMDB Client & Cache
python tests/sanity_tmdb.py

# Layer B: Intent Parser & Chatbot Orchestrator
python tests/sanity_chatbot.py

# Layer C: FastAPI Endpoints & Validation
python tests/sanity_api.py
```
