/**
 * Legal Hub - Client Application Logic (LawPlayer Twin Edition)
 * Integrates:
 * 1. LawPlayer Right Side Detail Drawer (綱要知識、內容速覽、歷次修法理由、實務見解、附檔)
 * 2. Mobile-only 0-9 Quick Dial
 * 3. Quick article jump pills (1) (184) (185-3)
 * 4. 6 Navigation modes & full text search
 */

class LegalHubApp {
  constructor() {
    this.currentActId = "criminal_code";
    this.currentMode = "all";
    this.currentAct = null;
    this.selectedArticle = null;
    this.activeDrawerTab = "summary";
    this.dialer = null;

    this.init();
  }

  async init() {
    this.initTheme();
    this.initEventListeners();
    await this.loadActList();
    await this.loadAct(this.currentActId);
    
    // Initialize 0-9 Quick Dialer (enabled only on mobile)
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

    // Act search / filter across full Taiwan legal corpus
    const actSearchInput = document.getElementById("act-search-input");
    if (actSearchInput) {
      actSearchInput.addEventListener("input", (e) => {
        const query = e.target.value.trim();
        this.filterActList(query);
      });
      actSearchInput.addEventListener("keydown", async (e) => {
        if (e.key === "Enter") {
          const query = e.target.value.trim();
          if (query) {
            const resp = await fetch(`/api/acts?q=${encodeURIComponent(query)}`);
            const json = await resp.json();
            if (json.success && json.data.length > 0) {
              this.currentActId = json.data[0].id;
              await this.loadAct(this.currentActId);
              if (actSelect) actSelect.value = this.currentActId;
            }
          }
        }
      });
    }

    // Theme toggle
    const themeBtn = document.getElementById("theme-toggle-btn");
    if (themeBtn) {
      themeBtn.addEventListener("click", () => this.toggleTheme());
    }

    // Dialer toggle button (mobile)
    const dialerBtn = document.getElementById("dialer-toggle-btn");
    if (dialerBtn) {
      dialerBtn.addEventListener("click", () => {
        if (this.dialer) this.dialer.toggle();
      });
    }

    // Drawer close button
    const drawerCloseBtn = document.getElementById("drawer-close-btn");
    if (drawerCloseBtn) {
      drawerCloseBtn.addEventListener("click", () => this.closeDrawer());
    }

    // Drawer tabs
    const drawerTabs = document.querySelectorAll(".drawer-tab");
    drawerTabs.forEach(tab => {
      tab.addEventListener("click", (e) => {
        drawerTabs.forEach(t => t.classList.remove("active"));
        e.currentTarget.classList.add("active");
        this.activeDrawerTab = e.currentTarget.dataset.tab;
        this.renderDrawerContent();
      });
    });

    // Drawer prev / next buttons
    const prevBtn = document.getElementById("drawer-prev-btn");
    const nextBtn = document.getElementById("drawer-next-btn");
    if (prevBtn) prevBtn.addEventListener("click", () => this.navigateArticle(-1));
    if (nextBtn) nextBtn.addEventListener("click", () => this.navigateArticle(1));

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

  async loadActList(query = "") {
    try {
      const resp = await fetch(`/api/acts?q=${encodeURIComponent(query)}`);
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

  async filterActList(query) {
    await this.loadActList(query);
  }

  async loadAct(actId) {
    try {
      const resp = await fetch(`/api/acts/${actId}`);
      const json = await resp.json();
      if (json.success) {
        this.currentAct = json.data;
        this.renderActBanner();
        this.renderSidebarChapters();
        this.renderQuickPills();
        this.renderCurrentView();

        // Default open the first article in LawPlayer drawer on desktop
        if (this.currentAct.articles && this.currentAct.articles.length > 0) {
          if (window.innerWidth >= 1024) {
            this.openArticleDrawer(this.currentAct.articles[0]);
          }
        }
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

  renderQuickPills() {
    const container = document.getElementById("pills-container");
    if (!container || !this.currentAct) return;

    const articles = this.currentAct.articles || [];
    container.innerHTML = articles.map(art => `
      <button class="pill-item ${this.selectedArticle && this.selectedArticle.article_no === art.article_no ? 'active' : ''}" 
              data-art="${art.article_no}" 
              title="第 ${art.article_no} 條 ${art.title || ''}">
        ${art.article_no}
      </button>
    `).join("");

    container.querySelectorAll(".pill-item").forEach(pill => {
      pill.addEventListener("click", (e) => {
        const no = e.currentTarget.dataset.art;
        this.jumpToArticle(no);
      });
    });
  }

  switchMode(mode) {
    this.currentMode = mode;
    if (mode === "query_no" && window.innerWidth <= 768 && this.dialer) {
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

    container.innerHTML = articles.map(art => `
      <article class="article-card ${this.selectedArticle && this.selectedArticle.article_no === art.article_no ? 'active-selected' : ''}" 
               id="art-${art.article_no}" 
               data-art="${art.article_no}">
        <header class="article-header">
          <div class="article-badge-group">
            <span class="article-no">第 ${art.article_no} 條</span>
            ${art.title ? `<span class="article-title-text">${art.title}</span>` : ""}
          </div>
          <span class="chapter-tag">${art.chapter || ""}</span>
        </header>

        <div class="article-body">${art.content}</div>

        <div class="article-card-footer">
          <span style="font-size:0.8rem;color:var(--text-dim);">
            🕒 閱讀時間 ${art.reading_time || "3 分鐘"} ｜ 🏛️ 含 ${art.amendment_history ? art.amendment_history.length : 1} 次修法理由
          </span>
          <button class="btn-open-drawer" data-art="${art.article_no}">
            開啟深度研析 ↗
          </button>
        </div>
      </article>
    `).join("");

    // Bind card and button clicks to open LawPlayer detail drawer
    container.querySelectorAll(".article-card").forEach(card => {
      card.addEventListener("click", (e) => {
        const no = card.dataset.art;
        const art = this.currentAct.articles.find(a => a.article_no === no);
        if (art) this.openArticleDrawer(art);
      });
    });
  }

  openArticleDrawer(art) {
    this.selectedArticle = art;
    const drawer = document.getElementById("lawplayer-drawer");
    if (!drawer) return;

    drawer.classList.remove("hidden");

    // Update active highlight in list
    document.querySelectorAll(".article-card").forEach(c => c.classList.remove("active-selected"));
    const activeCard = document.getElementById(`art-${art.article_no}`);
    if (activeCard) activeCard.classList.add("active-selected");

    // Update pills highlight
    document.querySelectorAll(".pill-item").forEach(p => {
      p.classList.toggle("active", p.dataset.art === art.article_no);
    });

    // Populate drawer header
    document.getElementById("drawer-breadcrumbs").textContent = 
      `${this.currentAct.name} > ${art.chapter || "法規本法"}`;
    document.getElementById("drawer-reading-time").textContent = 
      `閱讀時間 ${art.reading_time || "5 分鐘"}`;
    document.getElementById("drawer-title").textContent = 
      `${this.currentAct.name} 第 ${art.article_no} 條`;
    document.getElementById("drawer-subtitle").textContent = art.title || "條文釋義";
    document.getElementById("drawer-article-text").textContent = art.content;
    document.getElementById("drawer-curr-nav").textContent = 
      `第 ${art.article_no} 條 ${art.title || ""}`;

    // Populate external AI links
    const queryTerm = encodeURIComponent(`${this.currentAct.name} 第 ${art.article_no} 條 ${art.title || ''}`);
    document.getElementById("ai-perplexity-btn").href = `https://www.perplexity.ai/search?q=${queryTerm}`;
    document.getElementById("ai-chatgpt-btn").href = `https://chatgpt.com/?q=${queryTerm}`;
    document.getElementById("ai-grok-btn").href = `https://x.com/i/grok?text=${queryTerm}`;

    // Update prev/next button states
    this.updateDrawerNavButtons();

    // Render tab content
    this.renderDrawerContent();
  }

  closeDrawer() {
    const drawer = document.getElementById("lawplayer-drawer");
    if (drawer) drawer.classList.add("hidden");
  }

  updateDrawerNavButtons() {
    if (!this.selectedArticle || !this.currentAct) return;
    const articles = this.currentAct.articles || [];
    const idx = articles.findIndex(a => a.article_no === this.selectedArticle.article_no);
    
    const prevBtn = document.getElementById("drawer-prev-btn");
    const nextBtn = document.getElementById("drawer-next-btn");

    if (prevBtn) prevBtn.disabled = idx <= 0;
    if (nextBtn) nextBtn.disabled = idx < 0 || idx >= articles.length - 1;
  }

  navigateArticle(direction) {
    if (!this.selectedArticle || !this.currentAct) return;
    const articles = this.currentAct.articles || [];
    const idx = articles.findIndex(a => a.article_no === this.selectedArticle.article_no);
    const nextIdx = idx + direction;

    if (nextIdx >= 0 && nextIdx < articles.length) {
      const nextArt = articles[nextIdx];
      this.openArticleDrawer(nextArt);
      // Also scroll into view in list
      const el = document.getElementById(`art-${nextArt.article_no}`);
      if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }

  renderDrawerContent() {
    const container = document.getElementById("drawer-content");
    const art = this.selectedArticle;
    if (!container || !art) return;

    if (this.activeDrawerTab === "summary") {
      // 綱要知識 (重點摘要、白話與解析、Q&A)
      const qaHtml = (art.vernacular_qa || []).map(item => `
        <div class="qa-item">
          <h3 class="qa-question">${item.question}</h3>
          <p class="qa-answer">${item.answer}</p>
        </div>
      `).join("");

      container.innerHTML = `
        <div class="callout-box">
          <div class="callout-title">💡 重點摘要</div>
          <div>${art.summary || "本條為法規範圍核心要件。"}</div>
        </div>

        <div style="margin-bottom:1.5rem;">
          <h4 style="font-size:1.1rem;font-weight:700;color:var(--text-main);margin-bottom:0.75rem;">
            📖 白話與解析 <span style="font-size:0.75rem;color:var(--text-dim);font-weight:normal;">AI輔助整理，以法條為準</span>
          </h4>
          ${qaHtml || `<p style="color:var(--text-muted);font-size:0.95rem;">${art.legislative_reasons || "暫無白話解析"}</p>`}
        </div>
      `;
    } else if (this.activeDrawerTab === "quick_view") {
      // 內容速覽 (要件拆解、主要爭點、關聯條文)
      const elementsHtml = (art.elements || []).map(e => `
        <li style="margin-bottom:0.4rem;color:var(--text-muted);">${e}</li>
      `).join("");

      const issuesHtml = (art.key_issues || []).map(issue => `
        <li style="margin-bottom:0.4rem;color:var(--accent-amber);font-weight:500;">⚖️ ${issue}</li>
      `).join("");

      const relHtml = (art.related_articles || []).map(r => `
        <span style="display:inline-block;background:var(--bg-surface-elevated);border:1px solid var(--border-color);padding:0.25rem 0.6rem;border-radius:6px;font-size:0.85rem;color:var(--accent-primary);margin-right:0.4rem;margin-bottom:0.4rem;">${r}</span>
      `).join("");

      container.innerHTML = `
        <div style="margin-bottom:1.25rem;">
          <h4 style="font-size:1rem;font-weight:700;color:var(--accent-cyan);margin-bottom:0.5rem;">📌 條文構成要件拆解</h4>
          <ul style="padding-left:1.25rem;font-size:0.95rem;line-height:1.7;">${elementsHtml || "<li>依法條客觀要件定之</li>"}</ul>
        </div>

        <div style="margin-bottom:1.25rem;">
          <h4 style="font-size:1rem;font-weight:700;color:var(--accent-amber);margin-bottom:0.5rem;">🎯 核心爭點速覽</h4>
          <ul style="list-style:none;padding-left:0;font-size:0.95rem;line-height:1.7;">${issuesHtml || "<li>暫無爭點記錄</li>"}</ul>
        </div>

        <div>
          <h4 style="font-size:1rem;font-weight:700;color:var(--text-main);margin-bottom:0.5rem;">🔗 跨法規關聯條文</h4>
          <div>${relHtml || "無關聯條文"}</div>
        </div>
      `;
    } else if (this.activeDrawerTab === "legislative_history") {
      // 歷次修法理由 (分開每個條文、新舊條文對照、大修條號變動歷史)
      const historyList = art.amendment_history || [];
      if (historyList.length === 0) {
        container.innerHTML = `
          <div class="amendment-card">
            <span class="amendment-date-badge">現行條文立法理由</span>
            <p class="amendment-reason">${art.legislative_reasons || "無歷次修法記錄"}</p>
          </div>
        `;
        return;
      }

      container.innerHTML = `
        <div style="margin-bottom:1rem;font-size:0.9rem;color:var(--text-dim);">
          📚 本條文共收錄 <strong>${historyList.length}</strong> 次修正沿革與立法理由（含歷次條文架構大修）：
        </div>
        ${historyList.map(item => `
          <div class="amendment-card">
            <div>
              <span class="amendment-date-badge">${item.date}</span>
              ${item.change_type ? `<span class="amendment-type-tag">${item.change_type}</span>` : ""}
            </div>
            <div class="amendment-reason">${item.reason}</div>
            ${item.old_content ? `
              <div class="diff-box">
                <div class="diff-old"><strong>修正前：</strong><br>${item.old_content}</div>
                <div class="diff-new"><strong>修正後：</strong><br>${item.new_content || art.content}</div>
              </div>
            ` : ""}
          </div>
        `).join("")}
      `;
    } else if (this.activeDrawerTab === "insights") {
      // 實務見解 (裁判、判例、憲法法庭判決)
      const insightsHtml = (art.practical_insights || []).map(ins => `
        <div class="insight-card" style="margin-bottom:1rem;">
          <div class="insight-ref">⚖️ ${ins.court || "實務裁判"} ｜ ${ins.ref || ""}</div>
          <div class="insight-summary" style="line-height:1.75;font-size:0.95rem;">${ins.summary}</div>
        </div>
      `).join("");

      container.innerHTML = `
        <div style="margin-bottom:1rem;">
          <h4 style="font-size:1rem;font-weight:700;color:var(--accent-primary);margin-bottom:0.75rem;">
            🏛️ 最高法院具參考價值裁判、判例與憲法法庭解釋
          </h4>
          ${insightsHtml || "<p style='color:var(--text-muted);'>暫無精選實務見解</p>"}
        </div>
      `;
    } else if (this.activeDrawerTab === "attachments") {
      // 附檔與對照
      const attsHtml = (art.attachments || []).map(att => `
        <div style="background:var(--bg-surface-elevated);border:1px solid var(--border-color);padding:1rem;border-radius:8px;margin-bottom:1rem;">
          <div style="font-weight:700;font-size:1rem;margin-bottom:0.3rem;">📎 ${att.title}</div>
          <p style="font-size:0.85rem;color:var(--text-muted);margin-bottom:0.75rem;">${att.description || "法規主管機關公告之標準法規命令附表"}</p>
          <a href="${att.url}" target="_blank" rel="noopener noreferrer" class="attachment-badge">
            下載 / 線上閱讀 PDF ↗
          </a>
        </div>
      `).join("");

      container.innerHTML = `
        <div style="margin-bottom:1.5rem;">
          <h4 style="font-size:1rem;font-weight:700;color:var(--accent-emerald);margin-bottom:0.75rem;">
            📄 條文法定附檔與判定標準表
          </h4>
          ${attsHtml || "<p style='color:var(--text-muted);'>本條文無專屬附檔</p>"}
        </div>

        <div style="margin-top:1.5rem;border-top:1px solid var(--border-color);padding-top:1rem;">
          <h4 style="font-size:1rem;font-weight:700;color:var(--text-main);margin-bottom:0.75rem;">
            🌐 外部資料庫同步對照
          </h4>
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
      `;
    }
  }

  jumpToArticle(articleNo) {
    const art = (this.currentAct.articles || []).find(a => a.article_no === str(articleNo));
    if (art) {
      this.openArticleDrawer(art);
    }
    const el = document.getElementById(`art-${articleNo}`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.classList.remove("highlight-pulse");
      void el.offsetWidth;
      el.classList.add("highlight-pulse");
    }
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
    const art = (this.currentAct.articles || []).find(a => a.article_no === String(articleNo));
    if (art) {
      this.openArticleDrawer(art);
      return true;
    }
    return false;
  }
}

function str(val) {
  return String(val || "").trim();
}

// Bootstrap on load
window.addEventListener("DOMContentLoaded", () => {
  window.app = new LegalHubApp();
});
