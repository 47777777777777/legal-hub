/**
 * Legal Hub - statute reader
 * - One scroll container inside the drawer (#study-drawer-scroll-body)
 * - Multi-act research tabs, bookmarks (localStorage), hash permalinks
 * - Monochrome SVG icons only (see icons.js)
 */

const ESC_MAP = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ESC_MAP[c]);
}

/** Escape text and wrap case-insensitive matches of q in <mark>. */
function hl(text, q) {
  text = String(text == null ? "" : text);
  if (!q) return esc(text);
  const re = new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi");
  let out = "";
  let last = 0;
  let m;
  while ((m = re.exec(text)) !== null) {
    if (m[0].length === 0) {
      re.lastIndex++;
      continue;
    }
    out += esc(text.slice(last, m.index)) + "<mark>" + esc(m[0]) + "</mark>";
    last = m.index + m[0].length;
  }
  return out + esc(text.slice(last));
}

function hydrateIcons(root) {
  (root || document).querySelectorAll("[data-icon]").forEach((el) => {
    if (el.dataset.hydrated) return;
    el.innerHTML = icon(el.dataset.icon, parseInt(el.dataset.size || "16", 10));
    el.dataset.hydrated = "1";
  });
}

function sectionHeading(iconName, title, note) {
  return `<h3 class="sub-heading">${icon(iconName, 18)}<span>${title}</span>${note ? `<span class="sub-note">${note}</span>` : ""}</h3>`;
}

class LegalHubApp {
  constructor() {
    this.currentActId = "criminal_code";
    this.currentAct = null;
    this.selectedArticleNo = null;
    this.activeTab = "key_knowledge";
    this.dialer = null;
    this.fontSize = 16;
    this.searchQuery = "";
    this.activeChapterIdx = 0;
    this.openTabs = [{ id: "criminal_code", name: "中華民國刑法" }];
    this.bookmarks = this.loadBookmarks();

    this.init();
  }

  async init() {
    hydrateIcons();
    this.initTheme();
    this.setExpandIcon(false);
    this.initEventListeners();
    this.renderResearchTabs();

    const route = this.parseHashRoute();
    if (route && route.actId) {
      this.currentActId = route.actId;
      this.openTabs = [{ id: route.actId, name: route.actId }];
      await this.loadAct(route.actId);
      if (route.articleNo) {
        this.scrollToArticleCard(route.articleNo);
        this.openStudyDrawer(route.articleNo);
      }
    } else {
      await this.loadAct(this.currentActId);
    }

    if (window.QuickDialer) {
      this.dialer = new QuickDialer(this);
    }
  }

  // ---------------- Theme / font ----------------
  initTheme() {
    const saved = localStorage.getItem("legal_hub_theme") || "dark";
    document.documentElement.setAttribute("data-theme", saved);
    this.updateThemeButton(saved);
  }

  updateThemeButton(theme) {
    const btn = document.getElementById("theme-toggle-btn");
    if (btn) btn.innerHTML = icon(theme === "dark" ? "sun" : "moon", 17);
  }

  toggleTheme() {
    const cur = document.documentElement.getAttribute("data-theme") || "dark";
    const next = cur === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("legal_hub_theme", next);
    this.updateThemeButton(next);
  }

  adjustFontSize(delta) {
    this.fontSize = Math.max(14, Math.min(24, this.fontSize + delta));
    document.documentElement.style.setProperty("--font-size-base", `${this.fontSize}px`);
  }

  setExpandIcon(expanded) {
    const btn = document.getElementById("drawer-expand-btn");
    if (btn) btn.innerHTML = icon(expanded ? "minimize" : "maximize", 17);
  }

  // ---------------- Bookmarks ----------------
  loadBookmarks() {
    try {
      return JSON.parse(localStorage.getItem("legal_hub_bookmarks") || "[]");
    } catch (e) {
      return [];
    }
  }

  saveBookmarks() {
    localStorage.setItem("legal_hub_bookmarks", JSON.stringify(this.bookmarks));
  }

  isBookmarked(actId, articleNo) {
    return this.bookmarks.some((b) => b.actId === actId && b.articleNo === articleNo);
  }

  toggleBookmark(actId, articleNo) {
    const idx = this.bookmarks.findIndex((b) => b.actId === actId && b.articleNo === articleNo);
    if (idx >= 0) {
      this.bookmarks.splice(idx, 1);
    } else {
      let title = "";
      let snippet = "";
      if (this.currentAct && this.currentAct.articles) {
        const art = this.currentAct.articles.find((a) => a.article_no === articleNo);
        if (art) {
          title = art.title || "";
          snippet = (art.content || "").substring(0, 80) + "...";
        }
      }
      this.bookmarks.unshift({
        actId,
        actName: (this.currentAct && this.currentAct.name) || actId,
        articleNo,
        title,
        snippet,
        timestamp: new Date().toLocaleString()
      });
    }
    this.saveBookmarks();
    this.updateBookmarkButtonState(articleNo);
    this.refreshStreamBookmarkMarks();
  }

  updateBookmarkButtonState(articleNo) {
    const btn = document.getElementById("drawer-bookmark-btn");
    if (!btn) return;
    const on = this.isBookmarked(this.currentActId, articleNo);
    btn.innerHTML = icon(on ? "bookmark-filled" : "bookmark", 17);
    btn.classList.toggle("is-active", on);
  }

  refreshStreamBookmarkMarks() {
    document.querySelectorAll(".stream-article-card").forEach((card) => {
      const on = this.isBookmarked(this.currentActId, card.dataset.articleNo);
      const mark = card.querySelector(".card-bookmark-mark");
      if (mark) mark.classList.toggle("hidden", !on);
    });
  }

  // ---------------- Hash routing ----------------
  parseHashRoute() {
    const m = window.location.hash.match(/#\/act\/([^/]+)(?:\/article\/([^/]+))?/);
    return m ? { actId: m[1], articleNo: m[2] || null } : null;
  }

  updateHashRoute(actId, articleNo) {
    let hash = `#/act/${actId}`;
    if (articleNo) hash += `/article/${articleNo}`;
    window.history.replaceState(null, "", hash);
  }

  // ---------------- Research tabs ----------------
  renderResearchTabs() {
    const container = document.getElementById("research-tabs-list");
    if (!container) return;

    container.innerHTML = this.openTabs
      .map(
        (tab) => `
      <div class="research-tab-item ${tab.id === this.currentActId ? "active" : ""}" data-act-id="${esc(tab.id)}">
        <span>${esc(tab.name)}</span>
        ${this.openTabs.length > 1 ? `<button class="tab-close-btn" data-close="${esc(tab.id)}" title="關閉分頁" aria-label="關閉分頁">${icon("x", 13)}</button>` : ""}
      </div>`
      )
      .join("");

    container.querySelectorAll(".research-tab-item").forEach((el) => {
      el.addEventListener("click", (e) => {
        const closeBtn = e.target.closest(".tab-close-btn");
        if (closeBtn) {
          e.stopPropagation();
          this.closeResearchTab(closeBtn.dataset.close);
          return;
        }
        this.switchResearchTab(el.dataset.actId);
      });
    });
  }

  switchResearchTab(actId) {
    if (this.currentActId === actId) return;
    this.currentActId = actId;
    this.closeStudyDrawer();
    this.renderResearchTabs();
    this.loadAct(actId);
    this.updateHashRoute(actId);
  }

  openResearchTab(actId, actName) {
    if (!this.openTabs.find((t) => t.id === actId)) {
      this.openTabs.push({ id: actId, name: actName });
    }
    this.switchResearchTab(actId);
    this.renderResearchTabs();
  }

  closeResearchTab(actId) {
    if (this.openTabs.length <= 1) return;
    const idx = this.openTabs.findIndex((t) => t.id === actId);
    if (idx < 0) return;
    this.openTabs.splice(idx, 1);
    if (this.currentActId === actId) {
      const next = this.openTabs[Math.max(0, idx - 1)];
      this.currentActId = "";
      this.switchResearchTab(next.id);
    } else {
      this.renderResearchTabs();
    }
  }

  // ---------------- Events ----------------
  bindClearable(inputEl, clearEl, onChange) {
    if (!inputEl) return;
    const sync = () => {
      if (clearEl) clearEl.classList.toggle("hidden", !inputEl.value);
    };
    inputEl.addEventListener("input", () => {
      sync();
      if (onChange) onChange(inputEl.value.trim());
    });
    if (clearEl) {
      clearEl.addEventListener("click", () => {
        inputEl.value = "";
        sync();
        if (onChange) onChange("");
        inputEl.focus();
      });
    }
  }

  initEventListeners() {
    // Global act search (Enter opens best match)
    const actSearchInput = document.getElementById("act-search-input");
    this.bindClearable(actSearchInput, document.getElementById("act-search-clear"), null);
    if (actSearchInput) {
      actSearchInput.addEventListener("keydown", async (e) => {
        if (e.key !== "Enter") return;
        const query = e.target.value.trim();
        if (!query) return;
        try {
          const resp = await fetch(`/api/acts?q=${encodeURIComponent(query)}`);
          const json = await resp.json();
          if (json.success && json.data.length > 0) {
            const hit = json.data[0];
            this.openResearchTab(hit.id, hit.name);
            actSearchInput.blur();
          }
        } catch (err) {
          console.error(err);
        }
      });
    }

    // In-act search
    this.bindClearable(
      document.getElementById("search-input"),
      document.getElementById("search-clear"),
      (q) => this.filterStreamArticles(q)
    );

    document.getElementById("theme-toggle-btn").addEventListener("click", () => this.toggleTheme());
    document.getElementById("font-plus-btn").addEventListener("click", () => this.adjustFontSize(1));
    document.getElementById("font-minus-btn").addEventListener("click", () => this.adjustFontSize(-1));

    const dialerBtn = document.getElementById("dialer-toggle-btn");
    if (dialerBtn) {
      dialerBtn.addEventListener("click", () => {
        if (this.dialer) this.dialer.toggle();
      });
    }

    // Open-act modal
    const modal = document.getElementById("add-tab-modal");
    document.getElementById("add-tab-btn").addEventListener("click", () => {
      this.renderPopularActsModal();
      modal.classList.remove("hidden");
    });
    document.getElementById("add-tab-modal-close").addEventListener("click", () => modal.classList.add("hidden"));
    modal.addEventListener("click", (e) => {
      if (e.target === modal) modal.classList.add("hidden");
    });
    const tabSearchInput = document.getElementById("tab-search-input");
    tabSearchInput.addEventListener("input", (e) => this.searchActsInModal(e.target.value.trim()));

    // Drawer
    document.getElementById("drawer-close-btn").addEventListener("click", () => this.closeStudyDrawer());
    document.getElementById("drawer-backdrop").addEventListener("click", () => this.closeStudyDrawer());
    document.getElementById("drawer-bookmark-btn").addEventListener("click", () => {
      if (this.selectedArticleNo) this.toggleBookmark(this.currentActId, this.selectedArticleNo);
    });
    document.getElementById("drawer-pdf-btn").addEventListener("click", () => window.print());
    document.getElementById("drawer-expand-btn").addEventListener("click", () => {
      const panel = document.getElementById("study-drawer-panel");
      this.setExpandIcon(panel.classList.toggle("expanded"));
    });

    document.addEventListener("keydown", (e) => {
      const tag = document.activeElement ? document.activeElement.tagName : "";
      if (e.key === "Escape") {
        this.closeStudyDrawer();
        modal.classList.add("hidden");
        return;
      }
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if (e.key === "ArrowLeft") this.navigateAdjacentArticle(-1);
      else if (e.key === "ArrowRight") this.navigateAdjacentArticle(1);
    });
  }

  // ---------------- Open-act modal ----------------
  renderPopularActsModal() {
    const grid = document.getElementById("popular-acts-grid");
    const popular = [
      ["criminal_code", "中華民國刑法"],
      ["civil_code", "中華民國民法"],
      ["constitution", "中華民國憲法"],
      ["criminal_procedure_code", "刑事訴訟法"],
      ["civil_procedure_code", "民事訴訟法"],
      ["labor_standards_act", "勞動基準法"],
      ["admin_procedure_act", "行政程序法"],
      ["traffic_act", "道路交通管理處罰條例"],
      ["company_act", "公司法"]
    ];
    grid.innerHTML = popular
      .map(([id, name]) => `<button class="popular-act-chip" data-act-id="${id}" data-act-name="${name}">${name}</button>`)
      .join("");
    grid.querySelectorAll(".popular-act-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        this.openResearchTab(chip.dataset.actId, chip.dataset.actName);
        document.getElementById("add-tab-modal").classList.add("hidden");
      });
    });
  }

  async searchActsInModal(query) {
    const box = document.getElementById("tab-search-results");
    if (!query) {
      box.innerHTML = "";
      return;
    }
    try {
      const resp = await fetch(`/api/acts?q=${encodeURIComponent(query)}`);
      const json = await resp.json();
      const list = json.success ? json.data.slice(0, 12) : [];
      box.innerHTML = list.length
        ? list
            .map(
              (act) => `<button class="act-result-row" data-act-id="${esc(act.id)}" data-act-name="${esc(act.name)}">
                <span>${esc(act.name)}</span><span class="act-result-cat">${esc(act.category || "")}</span></button>`
            )
            .join("")
        : `<div class="empty-note">查無相符法規</div>`;
      box.querySelectorAll(".act-result-row").forEach((row) => {
        row.addEventListener("click", () => {
          this.openResearchTab(row.dataset.actId, row.dataset.actName);
          document.getElementById("add-tab-modal").classList.add("hidden");
        });
      });
    } catch (e) {
      box.innerHTML = `<div class="empty-note">搜尋失敗，請稍後再試</div>`;
    }
  }

  // ---------------- Data ----------------
  async loadAct(actId) {
    try {
      const resp = await fetch(`/api/acts/${actId}`);
      const json = await resp.json();
      if (!json.success) return;
      this.currentAct = json.data;
      this.searchQuery = "";
      const si = document.getElementById("search-input");
      if (si) si.value = "";
      document.getElementById("search-clear").classList.add("hidden");

      const tab = this.openTabs.find((t) => t.id === actId);
      if (tab) tab.name = this.currentAct.name;
      this.renderResearchTabs();
      this.renderActBanner();
      this.renderChapterToc();
      this.renderStatuteStream(this.currentAct.articles || []);
    } catch (e) {
      console.error(`Failed to load act ${actId}`, e);
    }
  }

  renderActBanner() {
    const banner = document.getElementById("act-banner");
    if (!banner || !this.currentAct) return;
    const n = (this.currentAct.articles || []).length;
    banner.innerHTML = `
      <span class="meta-chip">${esc(this.currentAct.category || "法規")}</span>
      <span class="meta-chip">最後修正：${esc(this.currentAct.last_modified || "現行有效")}</span>
      <span class="meta-chip">共 ${n} 條</span>`;
  }

  getChapters() {
    const chapters = [];
    const seen = new Set();
    ((this.currentAct && this.currentAct.articles) || []).forEach((art) => {
      const ch = art.chapter || "全文";
      if (!seen.has(ch)) {
        seen.add(ch);
        chapters.push({ chapter: ch, firstArticleNo: art.article_no });
      }
    });
    return chapters;
  }

  renderChapterToc() {
    const tocList = document.getElementById("sidebar-chapter-list");
    if (!tocList || !this.currentAct) return;
    this.activeChapterIdx = 0;
    tocList.innerHTML = this.getChapters()
      .map(
        (item, idx) =>
          `<div class="chapter-item ${idx === 0 ? "active" : ""}" data-idx="${idx}" data-target-art="${esc(item.firstArticleNo)}">${esc(item.chapter)}</div>`
      )
      .join("");

    tocList.querySelectorAll(".chapter-item").forEach((item) => {
      item.addEventListener("click", () => {
        if (this.searchQuery) this.clearSearch();
        this.activeChapterIdx = parseInt(item.dataset.idx, 10);
        this.syncTocActive();
        this.scrollToArticleCard(item.dataset.targetArt, "start");
      });
    });
  }

  /** In search mode no chapter is "current"; otherwise highlight the active one. */
  syncTocActive() {
    document.querySelectorAll("#sidebar-chapter-list .chapter-item").forEach((el) => {
      const active = !this.searchQuery && parseInt(el.dataset.idx, 10) === this.activeChapterIdx;
      el.classList.toggle("active", active);
    });
  }

  renderStatuteStream(articles) {
    const list = document.getElementById("statute-stream-list");
    const stats = document.getElementById("stream-stats");
    const q = this.searchQuery;
    if (!list) return;

    if (!articles || articles.length === 0) {
      list.innerHTML = `<div class="empty-note big">查無符合「${esc(q)}」的條文</div>`;
      if (stats) stats.textContent = "0 條";
      return;
    }
    if (stats) stats.textContent = q ? `找到 ${articles.length} 條` : `共 ${articles.length} 條`;

    let html = "";
    let lastChapter = null;
    articles.forEach((art) => {
      // Chapter dividers only in browse mode; in search mode each card carries its own chapter badge.
      if (!q && art.chapter && art.chapter !== lastChapter) {
        lastChapter = art.chapter;
        html += `<div class="chapter-divider">${esc(lastChapter)}</div>`;
      }
      const marked = this.isBookmarked(this.currentActId, art.article_no);
      html += `
        <article class="stream-article-card" id="article-card-${esc(art.article_no)}" data-article-no="${esc(art.article_no)}">
          <div class="article-card-header">
            <div class="article-card-no">
              <span>第 ${hl(art.article_no, q)} 條</span>
              ${art.title ? `<span class="article-card-title">${hl(art.title, q)}</span>` : ""}
              <span class="card-bookmark-mark ${marked ? "" : "hidden"}" title="已加入書籤">${icon("bookmark-filled", 14)}</span>
            </div>
            <div class="article-card-actions">
              ${q && art.chapter ? `<span class="chapter-badge">${esc(art.chapter)}</span>` : ""}
              <button class="article-study-btn" data-article-no="${esc(art.article_no)}">研析</button>
            </div>
          </div>
          <div class="article-card-content">${hl(art.content, q)}</div>
        </article>`;
    });
    list.innerHTML = html;
    list.scrollTop = 0;

    list.querySelectorAll(".stream-article-card").forEach((card) => {
      card.addEventListener("click", () => this.openStudyDrawer(card.dataset.articleNo));
    });
  }

  filterStreamArticles(query) {
    if (!this.currentAct || !this.currentAct.articles) return;
    this.searchQuery = query;
    this.syncTocActive();
    if (!query) {
      this.renderStatuteStream(this.currentAct.articles);
      return;
    }
    const q = query.toLowerCase();
    const filtered = this.currentAct.articles.filter(
      (art) =>
        String(art.article_no).toLowerCase().includes(q) ||
        (art.title && art.title.toLowerCase().includes(q)) ||
        (art.content && art.content.toLowerCase().includes(q))
    );
    this.renderStatuteStream(filtered);
  }

  clearSearch() {
    const input = document.getElementById("search-input");
    if (input) input.value = "";
    document.getElementById("search-clear").classList.add("hidden");
    this.searchQuery = "";
    this.renderStatuteStream((this.currentAct && this.currentAct.articles) || []);
    this.syncTocActive();
  }

  scrollToArticleCard(articleNo, block) {
    const card = document.getElementById(`article-card-${articleNo}`);
    if (!card) return false;
    card.scrollIntoView({ behavior: "smooth", block: block || "center" });
    document.querySelectorAll(".stream-article-card.active").forEach((c) => c.classList.remove("active"));
    card.classList.add("active");
    return true;
  }

  /** Used by the mobile dialer. Returns true when the article exists in the current act. */
  async loadAndJumpArticle(articleNo) {
    if (!this.currentAct) return false;
    const exists = (this.currentAct.articles || []).some((a) => a.article_no === articleNo);
    if (!exists) return false;
    if (this.searchQuery) this.clearSearch();
    // wait one frame so the freshly rendered list is in the DOM
    await new Promise((r) => requestAnimationFrame(r));
    this.scrollToArticleCard(articleNo);
    await this.openStudyDrawer(articleNo);
    return true;
  }

  // ---------------- Drawer ----------------
  async openStudyDrawer(articleNo) {
    this.selectedArticleNo = articleNo;
    this.updateHashRoute(this.currentActId, articleNo);
    this.updateBookmarkButtonState(articleNo);

    document.getElementById("drawer-article-badge").textContent = `第 ${articleNo} 條`;

    let art = (this.currentAct.articles || []).find((a) => a.article_no === articleNo) || {
      article_no: articleNo,
      content: ""
    };
    try {
      const resp = await fetch(`/api/acts/${this.currentActId}/articles/${articleNo}`);
      const json = await resp.json();
      if (json.success && json.data) art = json.data;
    } catch (e) {
      console.warn("Failed to fetch article details", e);
    }

    const crumb = [this.currentAct.name, art.chapter].filter(Boolean).join("  ›  ");
    const crumbEl = document.getElementById("drawer-breadcrumb");
    crumbEl.textContent = crumb;
    crumbEl.title = crumb;

    const scrollBody = document.getElementById("study-drawer-scroll-body");
    const nLinks = (art.related_articles || []).length + (art.attachments || []).length + (art.practical_insights || []).length;
    const nAmend = (art.amendment_history || []).length;
    const tabBtn = (id, iconName, label, count) =>
      `<button class="drawer-tab-btn ${this.activeTab === id ? "active" : ""}" data-tab="${id}">${icon(iconName, 16)}<span>${label}</span>${count ? `<span class="tab-count">${count}</span>` : ""}</button>`;

    scrollBody.innerHTML = `
      <section class="drawer-hero-section">
        <h1 class="drawer-hero-title">${esc(this.currentAct.name)} 第 ${esc(art.article_no)} 條</h1>
        ${art.title ? `<div class="drawer-hero-subtitle">${esc(art.title)}</div>` : ""}
        <div class="drawer-hero-article-box">
          <button class="article-box-copy-action" id="drawer-copy-article-btn" title="複製條文">${icon("copy", 14)}<span>複製</span></button>
          ${esc(art.content)}
        </div>
      </section>

      <nav class="drawer-tabs-bar">
        ${tabBtn("key_knowledge", "lightbulb", "關鍵知識", 0)}
        ${tabBtn("content_links", "link", "內容連結", nLinks)}
        ${tabBtn("legislative_history", "file", "立法理由", nAmend)}
        ${tabBtn("my_bookmarks", "star", "我的收藏", this.bookmarks.length)}
      </nav>

      <div class="drawer-tab-content-area" id="drawer-tab-content-area">
        ${this.generateTabContentHtml(art)}
      </div>

      <footer class="drawer-bottom-nav">
        <button class="drawer-nav-btn" id="drawer-prev-btn">${icon("arrowLeft", 15)}<span>上一條</span></button>
        <button class="drawer-nav-btn ghost" id="drawer-permalink-btn" title="在新分頁開啟此條">
          <span>第 ${esc(art.article_no)} 條</span>${icon("external", 14)}
        </button>
        <button class="drawer-nav-btn" id="drawer-next-btn"><span>下一條</span>${icon("arrowRight", 15)}</button>
      </footer>`;

    scrollBody.scrollTop = 0;

    scrollBody.querySelector("#drawer-copy-article-btn").addEventListener("click", (e) => {
      const text = `${this.currentAct.name} 第 ${art.article_no} 條 ${art.title || ""}\n${art.content}`;
      this.copyToClipboard(text, e.currentTarget);
    });
    scrollBody.querySelector("#drawer-permalink-btn").addEventListener("click", () => {
      window.open(`${window.location.origin}${window.location.pathname}#/act/${this.currentActId}/article/${art.article_no}`, "_blank");
    });

    this.bindDrawerTabs(scrollBody, art);
    this.bindDrawerNavButtons(scrollBody, art);
    this.bindDynamicContent(scrollBody);

    document.getElementById("study-drawer").classList.remove("hidden");
  }

  closeStudyDrawer() {
    document.getElementById("study-drawer").classList.add("hidden");
    if (this.currentActId) this.updateHashRoute(this.currentActId);
  }

  navigateAdjacentArticle(direction) {
    if (!this.currentAct || !this.selectedArticleNo) return;
    if (document.getElementById("study-drawer").classList.contains("hidden")) return;
    const articles = this.currentAct.articles || [];
    const idx = articles.findIndex((a) => a.article_no === this.selectedArticleNo);
    const target = articles[idx + direction];
    if (target) {
      this.scrollToArticleCard(target.article_no);
      this.openStudyDrawer(target.article_no);
    }
  }

  bindDrawerTabs(parentEl, art) {
    parentEl.querySelectorAll(".drawer-tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        parentEl.querySelectorAll(".drawer-tab-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        this.activeTab = btn.dataset.tab;
        const area = parentEl.querySelector("#drawer-tab-content-area");
        area.innerHTML = this.generateTabContentHtml(art);
        this.bindDynamicContent(area);
      });
    });
  }

  bindDrawerNavButtons(parentEl, art) {
    const articles = this.currentAct.articles || [];
    const idx = articles.findIndex((a) => a.article_no === art.article_no);
    const prev = parentEl.querySelector("#drawer-prev-btn");
    const next = parentEl.querySelector("#drawer-next-btn");
    prev.disabled = idx <= 0;
    next.disabled = idx < 0 || idx >= articles.length - 1;
    prev.addEventListener("click", () => this.navigateAdjacentArticle(-1));
    next.addEventListener("click", () => this.navigateAdjacentArticle(1));
  }

  /** FAQ accordion, bookmark list actions, in-page tab links. */
  bindDynamicContent(root) {
    root.querySelectorAll(".faq-q-trigger").forEach((header) => {
      header.addEventListener("click", () => {
        const body = header.nextElementSibling;
        if (!body) return;
        const open = body.classList.toggle("open");
        header.classList.toggle("open", open);
      });
    });

    root.querySelectorAll("[data-goto-tab]").forEach((el) => {
      el.addEventListener("click", () => {
        const target = document.querySelector(`.drawer-tab-btn[data-tab="${el.dataset.gotoTab}"]`);
        if (target) target.click();
      });
    });

    root.querySelectorAll(".bookmark-jump-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const { actId, artNo } = btn.dataset;
        if (actId !== this.currentActId) {
          this.openResearchTab(actId, actId);
          // wait for the act to finish loading
          for (let i = 0; i < 40 && !(this.currentAct && this.currentAct.id === actId); i++) {
            await new Promise((r) => setTimeout(r, 100));
          }
        }
        this.loadAndJumpArticle(artNo);
      });
    });

    root.querySelectorAll(".bookmark-delete-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        this.toggleBookmark(btn.dataset.actId, btn.dataset.artNo);
        const area = document.getElementById("drawer-tab-content-area");
        area.innerHTML = this.renderMyBookmarksHtml();
        this.bindDynamicContent(area);
      });
    });
  }

  generateTabContentHtml(art) {
    switch (this.activeTab) {
      case "content_links":
        return this.renderContentLinksHtml(art);
      case "legislative_history":
        return this.renderLegislativeHtml(art);
      case "my_bookmarks":
        return this.renderMyBookmarksHtml();
      default:
        return this.renderKeyKnowledgeHtml(art);
    }
  }

  // ---------------- Tab: 關鍵知識 ----------------
  renderKeyKnowledgeHtml(art) {
    const parsed = this.parseArticleElements(art);
    let html = "";

    html += `
      <div class="callout-box">
        <div class="callout-title">${icon("lightbulb", 16)}<span>重點摘要</span></div>
        <div>${art.summary || parsed.autoSummary}</div>
      </div>`;

    const qas = art.vernacular_qa && art.vernacular_qa.length ? art.vernacular_qa : parsed.autoVernacular;
    html += `<section>${sectionHeading("book", "白話與實務解讀")}
      ${qas
        .map(
          (item) => `<div class="card">
            <div class="card-title">${item.question || item.q}</div>
            <div class="card-body">${item.answer || item.a}</div>
          </div>`
        )
        .join("")}
    </section>`;

    html += `<section>${sectionHeading("scale", "法律定性")}
      <div class="card"><div class="card-body">${art.legal_definition || parsed.autoLegalDef}</div></div>
    </section>`;

    html += `<section>${sectionHeading("landmark", "構成要件與法律效果")}
      <div class="card kv-card">
        <div class="kv"><div class="kv-label">規範客體 / 行為態樣</div><div class="kv-val">${parsed.behaviorType}</div></div>
        <div class="kv"><div class="kv-label">主觀責任要求</div><div class="kv-val">${parsed.intentType}</div></div>
        <div class="kv"><div class="kv-label">法定效果 / 刑度範疇</div><div class="kv-val kv-accent">${parsed.penaltyType}</div></div>
        <div class="kv"><div class="kv-label">訴訟追訴特性</div><div class="kv-val">${parsed.prosecutionType}</div></div>
      </div>
    </section>`;

    html += `<section>${sectionHeading("branch", "思考脈絡與流程圖")}
      <div class="card flowchart-container">
        <div class="flow-step-box">行為事實發生</div>
        <div class="flow-indicator">↓</div>
        <div class="flow-decision-diamond">行為時是否有成文法律明文規定？</div>
        <div class="flow-branch-row">
          <div class="flow-sub-branch">
            <span class="flow-no">否 →</span>
            <div class="flow-outcome-no-crime">不構成犯罪（罪刑法定）</div>
          </div>
          <div class="flow-sub-branch">
            <span class="flow-yes">是 ↓</span>
            <div class="flow-decision-diamond">是否為不利於行為人之類推適用？</div>
            <div class="flow-branch-row">
              <div class="flow-sub-branch">
                <span class="flow-no">是 →</span>
                <div class="flow-outcome-no-crime">禁止，不成立犯罪</div>
              </div>
              <div class="flow-sub-branch">
                <span class="flow-yes">否 ↓</span>
                <div class="flow-decision-diamond">是否為事後立法追溯處罰？</div>
                <div class="flow-branch-row">
                  <div class="flow-sub-branch">
                    <span class="flow-no">是 →</span>
                    <div class="flow-outcome-no-crime">禁止溯及既往，不罰</div>
                  </div>
                  <div class="flow-sub-branch">
                    <span class="flow-yes">否 ↓</span>
                    <div class="flow-outcome-penalty">依法成立並處罰</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>`;

    const faqs = art.faqs && art.faqs.length ? art.faqs : parsed.autoFaqs;
    html += `<section>${sectionHeading("help", "大家也在問", `${faqs.length}`)}
      ${faqs
        .map(
          (faq) => `<div class="faq-item-box">
            <div class="faq-q-trigger"><span>${faq.q}</span><span class="faq-chevron">${icon("plus", 15)}</span></div>
            <div class="faq-a-content">${faq.a || faq.answer}</div>
          </div>`
        )
        .join("")}
    </section>`;

    if (art.comparison_table && art.comparison_table.headers) {
      const ct = art.comparison_table;
      html += `<section>${sectionHeading("table", "容易搞混", ct.title || "")}
        <div class="comp-table-container"><table class="table-clean">
          <thead><tr>${ct.headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead>
          <tbody>${ct.rows.map((row) => `<tr>${row.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody>
        </table></div>
      </section>`;
    }

    const letters = art.official_letters || [];
    if (letters.length) {
      html += `<section>${sectionHeading("file", "相關函釋", `${letters.length} 則`)}
        <div class="card list-card">
          ${letters
            .map(
              (c) => `<div class="official-letter-card">
                <div><span class="letter-no">${c.no}</span><span class="letter-meta">${c.organ} ${c.date}</span></div>
                <a href="https://judgment.judicial.gov.tw/FJUD/default.aspx" target="_blank" rel="noopener noreferrer" class="jump-link-btn">檢索${icon("external", 13)}</a>
              </div>`
            )
            .join("")}
        </div>
      </section>`;
    }

    html += `<div class="inline-link-row"><span>${nAmendLabel(art)}</span>
      <button class="text-link" data-goto-tab="legislative_history">查看立法理由與新舊條文對照 ${icon("arrowRight", 14)}</button></div>`;

    return html;
  }

  // ---------------- Tab: 內容連結 ----------------
  renderContentLinksHtml(art) {
    const rels = art.related_articles || [];
    const atts = art.attachments || [];
    const insights = art.practical_insights || [];
    const actName = esc(this.currentAct.name);

    return `
      <section>${sectionHeading("link", "跨法規關聯條文", `${rels.length}`)}
        ${
          rels.length
            ? `<div class="chip-row">${rels.map((r) => `<span class="ref-chip">${r}</span>`).join("")}</div>`
            : `<div class="empty-note">尚無關聯條文標註</div>`
        }
      </section>

      <section>${sectionHeading("gavel", "實務判解", `${insights.length}`)}
        ${
          insights.length
            ? insights
                .map(
                  (ins) => `<div class="card">
                    <div class="card-title accent">${ins.court || "最高法院"}　${ins.ref || ""}</div>
                    <div class="card-body">${ins.summary}</div>
                  </div>`
                )
                .join("")
            : `<div class="empty-note">尚無收錄判解，可由下方資料庫檢索</div>`
        }
      </section>

      <section>${sectionHeading("search", "資料庫檢索")}
        <div class="link-grid">
          <a href="https://judgment.judicial.gov.tw/FJUD/default.aspx" target="_blank" rel="noopener noreferrer" class="judgment-link-btn"><span>司法院裁判書系統（${actName} 第 ${esc(art.article_no)} 條）</span>${icon("external", 14)}</a>
          <a href="https://www-lawbank-com-tw.autorpa.lib.ccu.edu.tw:8443/" target="_blank" rel="noopener noreferrer" class="judgment-link-btn"><span>法源法律網（AutoRPA）</span>${icon("external", 14)}</a>
          <a href="https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/anglekmc/ttswebx?@0:0:1:lawkm@@0.1702332962648232" target="_blank" rel="noopener noreferrer" class="judgment-link-btn"><span>月旦知識庫（AutoRPA）</span>${icon("external", 14)}</a>
          <a href="https://law.moj.gov.tw" target="_blank" rel="noopener noreferrer" class="judgment-link-btn"><span>全國法規資料庫</span>${icon("external", 14)}</a>
        </div>
      </section>

      ${
        atts.length
          ? `<section>${sectionHeading("file", "附件", `${atts.length}`)}
              <div class="link-grid">${atts
                .map((a) => `<a href="${a.url}" target="_blank" rel="noopener noreferrer" class="judgment-link-btn"><span>${a.title}</span>${icon("external", 14)}</a>`)
                .join("")}</div>
            </section>`
          : ""
      }`;
  }

  // ---------------- Tab: 立法理由 ----------------
  renderLegislativeHtml(art) {
    const history = art.amendment_history || [];
    if (!history.length) {
      return `<section>${sectionHeading("file", "立法理由")}
        <div class="card"><div class="card-body">${
          art.legislative_reasons ||
          `本條為${esc(this.currentAct.name)}現行規定${art.chapter ? `，位於「${esc(art.chapter)}」` : ""}。歷次修正理由尚未收錄，請至立法院法律系統查詢。`
        }</div></div></section>`;
    }
    return `<section>${sectionHeading("file", "歷次制定與修正", `${history.length}`)}
      ${history
        .map(
          (item) => `<div class="card">
            <div class="card-title accent">${item.date}　${item.change_type || "修正"}</div>
            <div class="card-body">${item.reason}</div>
            ${
              item.old_content
                ? `<div class="diff-block">
                    <div class="diff-row del"><span class="diff-tag">修正前</span>${item.old_content}</div>
                    <div class="diff-row add"><span class="diff-tag">修正後</span>${item.new_content || art.content}</div>
                  </div>`
                : ""
            }
          </div>`
        )
        .join("")}
    </section>`;
  }

  // ---------------- Tab: 我的收藏 ----------------
  renderMyBookmarksHtml() {
    if (!this.bookmarks.length) {
      return `<div class="empty-state">
        <div class="empty-state-icon">${icon("bookmark", 28)}</div>
        <div class="empty-state-title">尚未收藏任何條文</div>
        <p>在條文研析面板右上角點選書籤圖示，即可收藏在這裡。資料只存在這個瀏覽器，不需登入。</p>
      </div>`;
    }
    return `<section>${sectionHeading("star", "我的收藏", `${this.bookmarks.length}`)}
      ${this.bookmarks
        .map(
          (b) => `<div class="card">
            <div class="card-title accent">${esc(b.actName)} 第 ${esc(b.articleNo)} 條${b.title ? `　${esc(b.title)}` : ""}</div>
            <div class="card-body">${esc(b.snippet || "")}</div>
            <div class="card-actions">
              <button class="drawer-nav-btn bookmark-jump-btn" data-act-id="${esc(b.actId)}" data-art-no="${esc(b.articleNo)}">${icon("zap", 14)}<span>前往</span></button>
              <button class="drawer-nav-btn ghost danger bookmark-delete-btn" data-act-id="${esc(b.actId)}" data-art-no="${esc(b.articleNo)}">${icon("trash", 14)}<span>移除</span></button>
            </div>
          </div>`
        )
        .join("")}
    </section>`;
  }

  // ---------------- Heuristic element parsing ----------------
  parseArticleElements(art) {
    const content = art.content || "";
    const actName = this.currentAct.name;

    let autoSummary = `規範${actName}${art.chapter ? `「${art.chapter}」` : ""}之核心要件與法律效果。`;
    if (content.includes("處") && (content.includes("年") || content.includes("役") || content.includes("罰金"))) {
      autoSummary = "本條明定犯罪構成要件與刑罰效果。";
    } else if (content.includes("賠償") || content.includes("請求權")) {
      autoSummary = "本條規範損害賠償請求權基礎與歸責條件。";
    } else if (content.includes("保障") || content.includes("自由")) {
      autoSummary = "本條為權利保障條款，拘束國家機關行使公權力。";
    }

    const autoVernacular = [
      {
        question: "這一條在規範什麼？",
        answer: `本條為${actName}之規定。主張或適用時，須對照條文列舉的要件逐項檢視。`
      }
    ];
    const autoLegalDef = `本條為${actName}之明文規定${art.chapter ? `，體系上位於「${art.chapter}」` : ""}。`;
    const autoFaqs = [
      { q: "主張本條要件時，舉證責任在誰？", a: "原則上由主張權利或請求適用本條之一方，就符合要件之事實負舉證責任。" },
      { q: "本條常見爭點是什麼？", a: "多集中於不確定法律概念之解釋、舉證責任分配，以及與其他法規之競合關係。" }
    ];

    let behaviorType = "法定一般規範行為";
    if (content.includes("故意") || content.includes("過失")) behaviorType = "作為或不作為行為";
    if (content.includes("駕駛")) behaviorType = "交通工具駕駛行為";
    if (content.includes("公務員")) behaviorType = "公務職權行使行為";

    let intentType = "依條文而定";
    if (content.includes("過失")) intentType = "故意或過失均處罰";
    else if (content.includes("故意")) intentType = "故意";
    if (content.includes("意圖")) intentType = "須具特定意圖";

    let penaltyType = "民事法律效果";
    if (content.includes("有期徒刑") || content.includes("拘役")) {
      const m = content.match(/處([^，。]+)/);
      penaltyType = m ? m[1].trim() : "自由刑或罰金";
    } else if (content.includes("罰鍰")) {
      penaltyType = "行政罰鍰";
    }

    let prosecutionType = "非刑事程序";
    if (content.includes("告訴乃論")) prosecutionType = "告訴乃論";
    else if (content.includes("處") && (content.includes("年") || content.includes("拘役"))) prosecutionType = "公訴罪（檢察官依職權追訴）";

    return { autoSummary, autoVernacular, autoLegalDef, autoFaqs, behaviorType, intentType, penaltyType, prosecutionType };
  }

  // ---------------- Utilities ----------------
  async copyToClipboard(text, triggerEl) {
    const original = triggerEl.innerHTML;
    try {
      await navigator.clipboard.writeText(text);
      triggerEl.innerHTML = `${icon("check", 14)}<span>已複製</span>`;
      triggerEl.classList.add("done");
    } catch (err) {
      triggerEl.innerHTML = `<span>複製失敗</span>`;
    }
    setTimeout(() => {
      triggerEl.innerHTML = original;
      triggerEl.classList.remove("done");
    }, 1500);
  }
}

function nAmendLabel(art) {
  const n = (art.amendment_history || []).length;
  return n ? `立法沿革：共 ${n} 版` : "立法沿革";
}

document.addEventListener("DOMContentLoaded", () => {
  window.legalHubApp = new LegalHubApp();
});
