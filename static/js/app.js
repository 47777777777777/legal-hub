/**
 * Legal Hub - Client Application Logic
 * Integrates 6 navigation tabs, LawPlayer-style article view, and API communication.
 */

class LegalHubApp {
  constructor() {
    this.currentActId = "criminal_code";
    this.currentMode = "all"; // 'all', 'chapters', 'query_no', 'search', 'history', 'legislative'
    this.currentAct = null;
    this.dialer = null;

    this.init();
  }

  async init() {
    this.initTheme();
    this.initEventListeners();
    await this.loadActList();
    await this.loadAct(this.currentActId);
    
    // Initialize 0-9 Quick Dialer
    this.dialer = new QuickDialer(this);
  }

  initTheme() {
    const savedTheme = localStorage.getItem("legal_hub_theme") || "dark";
    document.documentElement.setAttribute("data-theme", savedTheme);
    this.updateThemeButton(savedTheme);
  }

  updateThemeButton(theme) {
    const btn = document.getElementById("theme-toggle-btn");
    if (btn) {
      btn.innerHTML = theme === "dark" ? "☀️ 淺色" : "🌙 深色";
    }
  }

  toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme") || "dark";
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("legal_hub_theme", next);
    this.updateThemeButton(next);
  }

  initEventListeners() {
    // Act selector
    const actSelect = document.getElementById("act-select");
    if (actSelect) {
      actSelect.addEventListener("change", (e) => {
        this.currentActId = e.target.value;
        this.loadAct(this.currentActId);
      });
    }

    // Theme toggle
    const themeBtn = document.getElementById("theme-toggle-btn");
    if (themeBtn) {
      themeBtn.addEventListener("click", () => this.toggleTheme());
    }

    // Dialer toggle
    const dialerBtn = document.getElementById("dialer-toggle-btn");
    if (dialerBtn) {
      dialerBtn.addEventListener("click", () => {
        if (this.dialer) this.dialer.toggle();
      });
    }

    // 6 Navigation Tabs
    const tabBtns = document.querySelectorAll(".tab-btn");
    tabBtns.forEach(btn => {
      btn.addEventListener("click", (e) => {
        tabBtns.forEach(b => b.classList.remove("active"));
        e.currentTarget.classList.add("active");
        const mode = e.currentTarget.dataset.mode;
        this.switchMode(mode);
      });
    });

    // Search input & button
    const searchBtn = document.getElementById("search-btn");
    const searchInput = document.getElementById("search-input");
    if (searchBtn && searchInput) {
      searchBtn.addEventListener("click", () => this.performSearch(searchInput.value));
      searchInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") this.performSearch(searchInput.value);
      });
    }
  }

  async loadActList() {
    try {
      const resp = await fetch("/api/acts");
      const json = await resp.json();
      if (json.success) {
        const select = document.getElementById("act-select");
        if (select) {
          select.innerHTML = json.data.map(act => 
            `<option value="${act.id}" ${act.id === this.currentActId ? "selected" : ""}>${act.name}</option>`
          ).join("");
        }
      }
    } catch (err) {
      console.error("Failed to load acts list:", err);
    }
  }

  async loadAct(actId) {
    try {
      const resp = await fetch(`/api/acts/${actId}`);
      const json = await resp.json();
      if (json.success) {
        this.currentAct = json.data;
        this.renderActBanner();
        this.renderSidebarChapters();
        this.renderCurrentView();
      }
    } catch (err) {
      console.error(`Failed to load act ${actId}:`, err);
    }
  }

  renderActBanner() {
    if (!this.currentAct) return;
    const banner = document.getElementById("act-banner");
    if (!banner) return;

    const attsHtml = (this.currentAct.attachments || []).map(att => `
      <a href="${att.url}" target="_blank" rel="noopener noreferrer" class="attachment-badge">
        📎 ${att.title}
      </a>
    `).join("");

    banner.innerHTML = `
      <div class="act-title-row">
        <h1 class="act-title">${this.currentAct.name}</h1>
        ${this.currentAct.name_en ? `<span class="act-en-badge">${this.currentAct.name_en}</span>` : ""}
      </div>
      <div class="act-meta-row">
        <div class="meta-item">修正日期：<strong>${this.currentAct.last_modified || "現行法規"}</strong></div>
        <div class="meta-item">法規類別：<strong>${this.currentAct.category || "未分類"}</strong></div>
        ${attsHtml ? `<div class="meta-item">附檔：${attsHtml}</div>` : ""}
      </div>
      ${this.currentAct.org_reform_notice ? `
        <div class="org-notice">
          ※ ${this.currentAct.org_reform_notice}
        </div>
      ` : ""}
      <div class="nav-tabs-group">
        <button class="tab-btn ${this.currentMode === 'all' ? 'active' : ''}" data-mode="all">所有條文</button>
        <button class="tab-btn ${this.currentMode === 'chapters' ? 'active' : ''}" data-mode="chapters">編章節</button>
        <button class="tab-btn ${this.currentMode === 'query_no' ? 'active' : ''}" data-mode="query_no">條號查詢</button>
        <button class="tab-btn ${this.currentMode === 'search' ? 'active' : ''}" data-mode="search">條文檢索</button>
        <button class="tab-btn ${this.currentMode === 'history' ? 'active' : ''}" data-mode="history">沿革</button>
        <button class="tab-btn ${this.currentMode === 'legislative' ? 'active' : ''}" data-mode="legislative">立法歷程(附帶決議)</button>
      </div>
    `;

    // Re-bind tab clicks
    banner.querySelectorAll(".tab-btn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        banner.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
        e.currentTarget.classList.add("active");
        this.switchMode(e.currentTarget.dataset.mode);
      });
    });
  }

  renderSidebarChapters() {
    const list = document.getElementById("sidebar-chapter-list");
    if (!list || !this.currentAct) return;

    if (!this.currentAct.chapters || this.currentAct.chapters.length === 0) {
      list.innerHTML = `<div style="color:var(--text-dim);font-size:0.85rem;">暫無編章資料</div>`;
      return;
    }

    list.innerHTML = this.currentAct.chapters.map(ch => `
      <div class="chapter-item">
        <div class="chapter-title">📑 ${ch.title}</div>
        <ul class="section-list">
          ${(ch.sections || []).map(sec => `
            <li>
              <a href="#" class="section-link" data-chapter="${sec.title}">${sec.title}</a>
            </li>
          `).join("")}
        </ul>
      </div>
    `).join("");

    list.querySelectorAll(".section-link").forEach(link => {
      link.addEventListener("click", (e) => {
        e.preventDefault();
        const chName = e.currentTarget.dataset.chapter;
        this.filterByChapter(chName);
      });
    });
  }

  switchMode(mode) {
    this.currentMode = mode;
    if (mode === "query_no" && this.dialer) {
      this.dialer.toggle(true);
    }
    this.renderCurrentView();
  }

  renderCurrentView() {
    const container = document.getElementById("articles-container");
    if (!container || !this.currentAct) return;

    if (this.currentMode === "history") {
      this.renderHistoryView(container);
    } else if (this.currentMode === "legislative") {
      this.renderLegislativeView(container);
    } else {
      this.renderArticlesList(this.currentAct.articles || [], container);
    }
  }

  renderArticlesList(articles, container) {
    if (!articles || articles.length === 0) {
      container.innerHTML = `
        <div style="text-align:center;padding:3rem;color:var(--text-muted);">
          🔍 未找到相關條文
        </div>
      `;
      return;
    }

    container.innerHTML = articles.map(art => this.generateArticleCardHtml(art)).join("");

    // Bind LawPlayer supplemental accordion toggles
    container.querySelectorAll(".supp-header").forEach(header => {
      header.addEventListener("click", (e) => {
        const content = e.currentTarget.nextElementSibling;
        const isOpen = content.classList.contains("open");
        content.classList.toggle("open", !isOpen);
        e.currentTarget.querySelector(".supp-chevron").textContent = isOpen ? "▶" : "▼";
      });
    });
  }

  generateArticleCardHtml(art) {
    const insightsHtml = (art.practical_insights || []).map(ins => `
      <div class="insight-card">
        <div class="insight-ref">⚖️ ${ins.court || "實務裁判"} ｜ ${ins.ref || ""}</div>
        <div class="insight-summary">${ins.summary}</div>
      </div>
    `).join("");

    const artAttsHtml = (art.attachments || []).map(att => `
      <a href="${att.url}" target="_blank" rel="noopener noreferrer" class="attachment-badge" style="margin-right:0.5rem;">
        📎 ${att.title}
      </a>
    `).join("");

    return `
      <article class="article-card" id="art-${art.article_no}">
        <header class="article-header">
          <div class="article-badge-group">
            <span class="article-no">第 ${art.article_no} 條</span>
            ${art.title ? `<span class="article-title-text">${art.title}</span>` : ""}
          </div>
          <span class="chapter-tag">${art.chapter || ""}</span>
        </header>

        <div class="article-body">${art.content}</div>

        ${artAttsHtml ? `<div style="margin-bottom:1rem;">${artAttsHtml}</div>` : ""}

        <!-- LawPlayer Supplemental Accordion -->
        <div class="supplemental-container">
          <div class="supp-header">
            <span class="supp-chevron">▶</span>
            <span>🏛️ 法律人補充研析（立法理由、實務見解、延伸對照）</span>
          </div>
          <div class="supp-content">
            ${art.legislative_reasons ? `
              <div class="supp-sub-title">📜 立法理由</div>
              <p class="supp-text">${art.legislative_reasons}</p>
            ` : ""}

            ${insightsHtml ? `
              <div class="supp-sub-title">⚖️ 具參考價值裁判與實務見解</div>
              ${insightsHtml}
            ` : ""}

            <div class="external-links">
              ${art.lawplayer_link ? `
                <a href="${art.lawplayer_link}" target="_blank" rel="noopener noreferrer" class="ext-btn ext-btn-lawplayer">
                  直達法律人 LawPlayer 條文頁 ↗
                </a>
              ` : ""}
              <a href="https://www-lawbank-com-tw.autorpa.lib.ccu.edu.tw:8443/" target="_blank" rel="noopener noreferrer" class="ext-btn ext-btn-lawbank">
                中正大學 AutoRPA 法源對照 ↗
              </a>
            </div>
          </div>
        </div>
      </article>
    `;
  }

  renderHistoryView(container) {
    const historyList = this.currentAct.history || [];
    container.innerHTML = `
      <div class="article-card">
        <h2 style="font-size:1.3rem;margin-bottom:1rem;color:var(--accent-primary);">📜 ${this.currentAct.name} - 沿革歷程</h2>
        <div class="history-timeline">
          ${historyList.map(h => `<div class="timeline-item"><p>${h}</p></div>`).join("")}
        </div>
      </div>
    `;
  }

  renderLegislativeView(container) {
    const items = this.currentAct.legislative_process || [];
    container.innerHTML = `
      <div class="article-card">
        <h2 style="font-size:1.3rem;margin-bottom:1rem;color:var(--accent-emerald);">🏛️ ${this.currentAct.name} - 立法歷程與附帶決議</h2>
        <div class="history-timeline">
          ${items.map(item => `<div class="timeline-item"><p>${item}</p></div>`).join("")}
        </div>
      </div>
    `;
  }

  async performSearch(query) {
    const container = document.getElementById("articles-container");
    if (!query || !query.trim()) {
      this.renderArticlesList(this.currentAct.articles || [], container);
      return;
    }

    try {
      const resp = await fetch(`/api/acts/${this.currentActId}/search?q=${encodeURIComponent(query.trim())}`);
      const json = await resp.json();
      if (json.success) {
        this.renderArticlesList(json.data.items, container);
      }
    } catch (err) {
      console.error("Search failed:", err);
    }
  }

  filterByChapter(chapterName) {
    const container = document.getElementById("articles-container");
    const filtered = (this.currentAct.articles || []).filter(a => a.chapter && a.chapter.includes(chapterName));
    this.renderArticlesList(filtered, container);
  }

  async loadAndJumpArticle(articleNo) {
    // If not in current DOM, check via API
    try {
      const resp = await fetch(`/api/acts/${this.currentActId}/articles/${articleNo}`);
      const json = await resp.json();
      if (json.success) {
        // Switch to all view and append if necessary
        this.currentMode = "all";
        this.renderCurrentView();
        return true;
      }
    } catch (e) {
      // Not found
    }
    return false;
  }
}

// Bootstrap on load
window.addEventListener("DOMContentLoaded", () => {
  window.app = new LegalHubApp();
});
