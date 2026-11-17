/**
 * CineMind AI - Movie Recommender Chatbot Frontend Controller
 * Pure Vanilla JavaScript (No frameworks, No build step)
 */

document.addEventListener("DOMContentLoaded", () => {
  const messagesContainer = document.getElementById("messages-container");
  const chatForm = document.getElementById("chat-form");
  const userInput = document.getElementById("user-input");
  const sendBtn = document.getElementById("send-btn");
  const clearBtn = document.getElementById("clear-btn");
  const statusCard = document.getElementById("status-card");
  const statusText = document.getElementById("status-text");
  const statusDesc = document.getElementById("status-desc");
  const apiKeyWarning = document.getElementById("api-key-warning");
  const metricCache = document.getElementById("metric-cache");
  const metricCalls = document.getElementById("metric-calls");
  const metricRemaining = document.getElementById("metric-remaining");
  const examplesList = document.getElementById("examples-list");

  // Filter elements
  const filterToggleBtn = document.getElementById("filter-toggle-btn");
  const filterDrawer = document.getElementById("filter-drawer");
  const filterBadge = document.getElementById("filter-badge");
  const filterGenre = document.getElementById("filter-genre");
  const filterLang = document.getElementById("filter-lang");
  const filterRating = document.getElementById("filter-rating");
  const filterEra = document.getElementById("filter-era");
  const filterSort = document.getElementById("filter-sort");
  const applyFiltersBtn = document.getElementById("apply-filters-btn");
  const resetFiltersBtn = document.getElementById("reset-filters-btn");
  const activeFiltersBar = document.getElementById("active-filters-bar");
  const activeChipsContainer = document.getElementById("active-chips-container");
  const clearAllFiltersBtn = document.getElementById("clear-all-filters-btn");

  let isAwaitingResponse = false;

  // Initialize App
  init();

  async function init() {
    await checkHealth();
    await updateMetrics();
    await loadExamples();
    setupEventListeners();
    showWelcomeMessage();
  }

  function setupEventListeners() {
    chatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      handleSend();
    });

    clearBtn.addEventListener("click", async () => {
      messagesContainer.innerHTML = "";
      showWelcomeMessage();
      try {
        await fetch("/api/reset", { method: "POST" });
        await updateMetrics();
      } catch (err) {
        console.warn("Failed to reset session:", err);
      }
    });

    // Delegate clicks on example buttons
    examplesList.addEventListener("click", (e) => {
      const chip = e.target.closest(".example-chip");
      if (chip && !isAwaitingResponse) {
        const query = chip.getAttribute("data-query") || chip.textContent.trim();
        userInput.value = query;
        handleSend();
      }
    });

    // Filter toggle
    if (filterToggleBtn && filterDrawer) {
      filterToggleBtn.addEventListener("click", () => {
        filterDrawer.classList.toggle("collapsed");
        filterToggleBtn.classList.toggle("active", !filterDrawer.classList.contains("collapsed"));
      });
    }

    // Filter change listeners
    [filterGenre, filterLang, filterRating, filterEra, filterSort].forEach((sel) => {
      if (sel) {
        sel.addEventListener("change", updateFilterUI);
      }
    });

    // Apply filters button
    if (applyFiltersBtn) {
      applyFiltersBtn.addEventListener("click", () => {
        const filters = getActiveFilters();
        const parts = [];
        if (filters.genre) parts.push(filters.genre);
        if (filters.language) parts.push(`in ${filterLang.options[filterLang.selectedIndex].text}`);
        if (filters.min_rating) parts.push(`rated ★${filters.min_rating}+`);
        if (filters.year_from && filters.year_to) parts.push(`from ${filters.year_from}–${filters.year_to}`);

        const promptText = parts.length > 0
          ? `Discover ${parts.join(" ")} movies`
          : "Discover top-rated movies";
        userInput.value = promptText;
        handleSend();
      });
    }

    // Reset filters buttons
    if (resetFiltersBtn) {
      resetFiltersBtn.addEventListener("click", resetFilters);
    }
    if (clearAllFiltersBtn) {
      clearAllFiltersBtn.addEventListener("click", resetFilters);
    }
  }

  /**
   * Get active filters as an object
   */
  function getActiveFilters() {
    const filters = {};
    if (filterGenre && filterGenre.value) {
      filters.genre = filterGenre.value;
    }
    if (filterLang && filterLang.value) {
      filters.language = filterLang.value;
    }
    if (filterRating && filterRating.value) {
      filters.min_rating = parseFloat(filterRating.value);
    }
    if (filterEra && filterEra.value) {
      const val = filterEra.value;
      if (val === "2020-now") {
        filters.year_from = 2020;
      } else if (val === "2010-2019") {
        filters.year_from = 2010;
        filters.year_to = 2019;
      } else if (val === "2000-2009") {
        filters.year_from = 2000;
        filters.year_to = 2009;
      } else if (val === "1990-1999") {
        filters.year_from = 1990;
        filters.year_to = 1999;
      } else if (val === "pre-1990") {
        filters.year_to = 1989;
      }
    }
    if (filterSort && filterSort.value) {
      filters.sort_by = filterSort.value;
    }
    return filters;
  }

  /**
   * Refresh Filter UI chips and badge
   */
  function updateFilterUI() {
    const filters = getActiveFilters();
    activeChipsContainer.innerHTML = "";

    const activeList = [];
    if (filters.genre) {
      activeList.push({ label: `Genre: ${filters.genre}`, reset: () => { filterGenre.value = ""; } });
    }
    if (filters.language) {
      const langName = filterLang.options[filterLang.selectedIndex].text.split(" ")[0];
      activeList.push({ label: `Lang: ${langName}`, reset: () => { filterLang.value = ""; } });
    }
    if (filters.min_rating) {
      activeList.push({ label: `Min ★ ${filters.min_rating}`, reset: () => { filterRating.value = ""; } });
    }
    if (filterEra && filterEra.value) {
      const eraText = filterEra.options[filterEra.selectedIndex].text;
      activeList.push({ label: `Era: ${eraText}`, reset: () => { filterEra.value = ""; } });
    }

    if (activeList.length > 0) {
      activeFiltersBar.classList.remove("hidden");
      if (filterBadge) {
        filterBadge.textContent = activeList.length;
        filterBadge.classList.remove("hidden");
      }
      activeList.forEach((item) => {
        const chip = document.createElement("span");
        chip.className = "active-chip";
        chip.innerHTML = `${escapeHtml(item.label)} <span class="active-chip-remove" title="Remove filter">&times;</span>`;
        chip.querySelector(".active-chip-remove").addEventListener("click", () => {
          item.reset();
          updateFilterUI();
        });
        activeChipsContainer.appendChild(chip);
      });
    } else {
      activeFiltersBar.classList.add("hidden");
      if (filterBadge) {
        filterBadge.classList.add("hidden");
      }
    }
  }

  function resetFilters() {
    if (filterGenre) filterGenre.value = "";
    if (filterLang) filterLang.value = "";
    if (filterRating) filterRating.value = "";
    if (filterEra) filterEra.value = "";
    if (filterSort) filterSort.value = "vote_average.desc";
    updateFilterUI();
  }

  /**
   * Check system health and TMDB configuration
   */
  async function checkHealth() {
    try {
      const res = await fetch("/api/health");
      const data = await res.json();

      statusCard.className = "status-card";
      if (data.status === "ok" && data.tmdb_configured) {
        statusCard.classList.add("status-ok");
        statusText.textContent = "TMDB Connected";
        statusDesc.textContent = "Live recommendations ready";
        apiKeyWarning.classList.add("hidden");
      } else {
        statusCard.classList.add("status-degraded");
        statusText.textContent = "Degraded Mode";
        statusDesc.textContent = "TMDB Key Unconfigured";
        apiKeyWarning.classList.remove("hidden");
      }
    } catch (err) {
      console.error("Health check error:", err);
      statusCard.className = "status-card status-degraded";
      statusText.textContent = "Offline / Disconnected";
      statusDesc.textContent = "Cannot reach server";
    }
  }

  /**
   * Fetch and render live metrics from backend
   */
  async function updateMetrics() {
    try {
      const res = await fetch("/api/metrics");
      if (!res.ok) return;
      const data = await res.json();

      metricCache.textContent = data.cache_size ?? 0;
      metricCalls.textContent = data.api_calls_today ?? 0;
      metricRemaining.textContent = data.rate_limit_remaining ?? "TMDB Free Tier (~1000/day)";
    } catch (err) {
      console.warn("Failed to fetch metrics:", err);
    }
  }

  /**
   * Load examples from API to populate or ensure synchronization
   */
  async function loadExamples() {
    try {
      const res = await fetch("/api/examples");
      if (!res.ok) return;
      const examples = await res.json();
      if (Array.isArray(examples) && examples.length > 0) {
        examplesList.innerHTML = "";
        examples.forEach((ex) => {
          const btn = document.createElement("button");
          btn.className = "example-chip";
          btn.setAttribute("data-query", ex);
          btn.textContent = ex;
          examplesList.appendChild(btn);
        });
      }
    } catch (err) {
      console.warn("Failed to load examples:", err);
    }
  }

  /**
   * Display initial welcome message
   */
  function showWelcomeMessage() {
    const welcomeHtml = `
      <p>👋 Hello! I am your <strong>AI Movie Assistant</strong>.</p>
      <p style="margin-top: 6px;">Powered by live TMDB movie data with smart caching and rate-limiting. Here's what you can ask:</p>
      <ul style="margin: 8px 0 0 20px; font-size: 0.88rem; line-height: 1.6;">
        <li><strong>By title:</strong> <em>"movies like Inception"</em> or <em>"similar to The Matrix"</em></li>
        <li><strong>By genre:</strong> <em>"recommend a comedy"</em> or <em>"show me horror films"</em></li>
        <li><strong>By language:</strong> <em>"recommend a Korean movie"</em> or <em>"top Hindi movies"</em></li>
        <li><strong>Top-rated:</strong> <em>"top rated movies"</em></li>
        <li><strong>By seeds:</strong> <em>"recommend based on Interstellar, Avatar"</em></li>
      </ul>
    `;
    appendBotMessage(welcomeHtml, [], true);
  }

  /**
   * Handle user form submission
   */
  async function handleSend() {
    const text = userInput.value.trim();
    if (!text || isAwaitingResponse) return;

    // Append user message
    appendUserMessage(text);
    userInput.value = "";
    setLoadingState(true);

    // Show typing indicator
    const typingIndicator = showTypingIndicator();

    try {
      const activeFilters = getActiveFilters();
      const payload = { message: text };
      if (Object.keys(activeFilters).length > 0) {
        payload.filters = activeFilters;
      }

      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      removeTypingIndicator(typingIndicator);

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }

      const data = await response.json();
      appendBotMessage(data.reply, data.recommendations || []);
      await updateMetrics();
      await checkHealth();
    } catch (error) {
      console.error("Chat error:", error);
      removeTypingIndicator(typingIndicator);
      appendBotMessage(
        "I'm having trouble reaching the movie database right now. Please try again in a moment.",
        []
      );
    } finally {
      setLoadingState(false);
      userInput.focus();
    }
  }

  /**
   * Append a user chat bubble
   */
  function appendUserMessage(text) {
    const row = document.createElement("div");
    row.className = "message-row user";

    const bubble = document.createElement("div");
    bubble.className = "chat-bubble";
    bubble.textContent = text;

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = "👤";

    row.appendChild(avatar);
    row.appendChild(bubble);
    messagesContainer.appendChild(row);
    scrollToBottom();
  }

  /**
   * Append a bot message and render any recommendation cards
   */
  function appendBotMessage(replyText, recommendations, isHtml = false) {
    const row = document.createElement("div");
    row.className = "message-row bot";

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = "🤖";

    const body = document.createElement("div");
    body.className = "message-body";

    const bubble = document.createElement("div");
    bubble.className = "chat-bubble";

    // Format markdown-like bold/italic in reply text or render direct HTML
    if (isHtml) {
      bubble.innerHTML = replyText;
    } else {
      bubble.innerHTML = formatReplyText(replyText);
    }

    // If TMDB key missing alert is detected in reply
    if (replyText.includes("Please configure your TMDB API key in .env")) {
      const alertBox = document.createElement("div");
      alertBox.className = "api-key-warning";
      alertBox.style.marginTop = "10px";
      alertBox.innerHTML = `
        <strong>Action Needed:</strong> Create a free TMDB account at
        <a href="https://www.themoviedb.org/settings/api" target="_blank" style="color:#60a5fa; text-decoration:underline;">themoviedb.org/settings/api</a>,
        copy your API key into <code>.env</code> as <code>TMDB_API_KEY=your_key</code>, and restart the server.
      `;
      bubble.appendChild(alertBox);
    }

    body.appendChild(bubble);

    // Render recommendation cards if available
    if (recommendations && recommendations.length > 0) {
      const cardsGrid = document.createElement("div");
      cardsGrid.className = "cards-grid";

      recommendations.forEach((rec) => {
        const card = createMovieCard(rec);
        cardsGrid.appendChild(card);
      });

      body.appendChild(cardsGrid);
    }

    row.appendChild(avatar);
    row.appendChild(body);
    messagesContainer.appendChild(row);
    scrollToBottom();
  }

  /**
   * Construct a single movie recommendation card
   */
  function createMovieCard(movie) {
    const card = document.createElement("div");
    card.className = "movie-card";

    // Poster wrapper
    const posterWrapper = document.createElement("div");
    posterWrapper.className = "card-poster-wrapper";

    if (movie.poster_url) {
      const img = document.createElement("img");
      img.className = "card-poster-img";
      img.src = movie.poster_url;
      img.alt = `${movie.title} poster`;
      img.loading = "lazy";
      img.onerror = () => {
        // Fallback to placeholder if image fails to load
        posterWrapper.innerHTML = `
          <div class="card-poster-placeholder">
            <span class="placeholder-icon">🎬</span>
            <span class="placeholder-title">${escapeHtml(movie.title)}</span>
          </div>
        `;
      };
      posterWrapper.appendChild(img);
    } else {
      posterWrapper.innerHTML = `
        <div class="card-poster-placeholder">
          <span class="placeholder-icon">🎬</span>
          <span class="placeholder-title">${escapeHtml(movie.title)}</span>
        </div>
      `;
    }

    // Rating badge
    const ratingBadge = document.createElement("div");
    ratingBadge.className = "card-rating-badge";
    const ratingVal = movie.rating ? movie.rating.toFixed(1) : "N/A";
    ratingBadge.innerHTML = `<span>★</span> ${ratingVal}`;
    posterWrapper.appendChild(ratingBadge);

    // Content container
    const content = document.createElement("div");
    content.className = "card-content";

    // Header line: Title & Year
    const headerLine = document.createElement("div");
    headerLine.className = "card-header-line";

    const titleEl = document.createElement("h4");
    titleEl.className = "movie-title";
    titleEl.textContent = movie.title;
    headerLine.appendChild(titleEl);

    if (movie.year && movie.year !== "N/A") {
      const yearEl = document.createElement("span");
      yearEl.className = "movie-year";
      yearEl.textContent = movie.year;
      headerLine.appendChild(yearEl);
    }
    content.appendChild(headerLine);

    // Genres chips
    if (movie.genres && movie.genres.length > 0) {
      const genresContainer = document.createElement("div");
      genresContainer.className = "genre-chips";
      movie.genres.slice(0, 3).forEach((genre) => {
        const tag = document.createElement("span");
        tag.className = "genre-tag";
        tag.textContent = genre;
        genresContainer.appendChild(tag);
      });
      content.appendChild(genresContainer);
    }

    // Reason
    if (movie.reason) {
      const reasonEl = document.createElement("div");
      reasonEl.className = "card-reason";
      reasonEl.textContent = movie.reason;
      content.appendChild(reasonEl);
    }

    card.appendChild(posterWrapper);
    card.appendChild(content);
    return card;
  }

  /**
   * Typing Indicator Helpers
   */
  function showTypingIndicator() {
    const row = document.createElement("div");
    row.className = "message-row bot typing-row";

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = "🤖";

    const indicator = document.createElement("div");
    indicator.className = "typing-indicator";
    indicator.innerHTML = `
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
    `;

    row.appendChild(avatar);
    row.appendChild(indicator);
    messagesContainer.appendChild(row);
    scrollToBottom();
    return row;
  }

  function removeTypingIndicator(indicatorEl) {
    if (indicatorEl && indicatorEl.parentNode) {
      indicatorEl.parentNode.removeChild(indicatorEl);
    }
  }

  function setLoadingState(loading) {
    isAwaitingResponse = loading;
    sendBtn.disabled = loading;
    userInput.disabled = loading;
  }

  function scrollToBottom() {
    messagesContainer.scrollTo({
      top: messagesContainer.scrollHeight,
      behavior: "smooth",
    });
  }

  function formatReplyText(text) {
    if (!text) return "";
    let formatted = escapeHtml(text);
    // Replace *text* with <em>text</em>
    formatted = formatted.replace(/\*([^*]+)\*/g, "<strong>$1</strong>");
    // Replace newlines with <br>
    formatted = formatted.replace(/\n/g, "<br>");
    return formatted;
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});
