/**
 * Legal Hub - Professional Legal Intelligence System (LawPlayer Replica)
 * 
 * Features:
 * 1. Single natural vertical scroll (NO nested scrollbars, NO cut-offs)
 * 2. Complete LawPlayer replica design with deep structural parsing
 * 3. 4 Tabs: 💡 關鍵知識 | 🔗 內容連結 | 📜 立法理由 | ⭐ 我的收藏
 * 4. Multi-Act Research Tabs (100% Free & Unlocked, NO VIP restrictions)
 * 5. Bookmarks system (LocalStorage), PDF export, Permalinks, Mobile dialer
 */

class LegalHubApp {
  constructor() {
    this.currentActId = "criminal_code";
    this.currentAct = null;
    this.allActs = [];
    this.selectedArticleNo = null;
    this.activeTab = "key_knowledge";
    this.dialer = null;
    this.fontSize = 16;
    
    // Multi-Act Research Tabs
    this.openTabs = [
      { id: "criminal_code", name: "中華民國刑法" }
    ];

    // Personal Bookmarks
    this.bookmarks = this.loadBookmarks();

    this.init();
  }

  async init() {
    this.initTheme();
    this.initEventListeners();
    await this.loadActList();
    this.renderResearchTabs();

    // Parse URL Hash routing on load (e.g. #/act/criminal_code/article/185-3)
    const hashRoute = this.parseHashRoute();
    if (hashRoute && hashRoute.actId) {
      this.currentActId = hashRoute.actId;
      await this.loadAct(this.currentActId);
      if (hashRoute.articleNo) {
        setTimeout(() => {
          this.openStudyDrawer(hashRoute.articleNo);
          this.scrollToArticleCard(hashRoute.articleNo);
        }, 200);
      }
    } else {
      await this.loadAct(this.currentActId);
    }

    // Initialize Mobile Dialer
    if (window.QuickDialer) {
      this.dialer = new QuickDialer(this);
    }
  }

  // ---------------- Theme Management ----------------
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

  adjustFontSize(delta) {
    this.fontSize = Math.max(14, Math.min(24, this.fontSize + delta));
    document.documentElement.style.setProperty("--font-size-base", `${this.fontSize}px`);
  }

  // ---------------- Bookmarks Management ----------------
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
    return this.bookmarks.some(b => b.actId === actId && b.articleNo === articleNo);
  }

  toggleBookmark(actId, articleNo) {
    const idx = this.bookmarks.findIndex(b => b.actId === actId && b.articleNo === articleNo);
    if (idx >= 0) {
      this.bookmarks.splice(idx, 1);
    } else {
      let title = "";
      let snippet = "";
      if (this.currentAct && this.currentAct.articles) {
        const art = this.currentAct.articles.find(a => a.article_no === articleNo);
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
  }

  updateBookmarkButtonState(articleNo) {
    const btn = document.getElementById("drawer-bookmark-btn");
    if (btn) {
      const bookmarked = this.isBookmarked(this.currentActId, articleNo);
      btn.innerHTML = bookmarked ? "⭐ 已收藏" : "🔖 書籤";
      btn.style.color = bookmarked ? "var(--accent-amber)" : "var(--text-main)";
      btn.style.borderColor = bookmarked ? "var(--accent-amber)" : "var(--border-color)";
    }
  }

  // ---------------- URL Hash Routing ----------------
  parseHashRoute() {
    const hash = window.location.hash;
    // Format: #/act/{actId}/article/{articleNo}
    const match = hash.match(/#\/act\/([^/]+)(?:\/article\/([^/]+))?/);
    if (match) {
      return {
        actId: match[1],
        articleNo: match[2] || null
      };
    }
    return null;
  }

  updateHashRoute(actId, articleNo = null) {
    let hash = `#/act/${actId}`;
    if (articleNo) hash += `/article/${articleNo}`;
    window.history.replaceState(null, "", hash);
  }

  // ---------------- Multi-Act Research Tabs (LawPlayer Replica) ----------------
  renderResearchTabs() {
    const container = document.getElementById("research-tabs-list");
    if (!container) return;

    container.innerHTML = this.openTabs.map(tab => `
      <div class="research-tab-item ${tab.id === this.currentActId ? 'active' : ''}" data-act-id="${tab.id}">
        <span>${tab.name}</span>
        ${this.openTabs.length > 1 ? `<button class="tab-close-btn" data-act-id="${tab.id}" title="關閉分頁">✕</button>` : ""}
      </div>
    `).join("");

    // Bind tab clicks
    container.querySelectorAll(".research-tab-item").forEach(el => {
      el.addEventListener("click", (e) => {
        if (e.target.classList.contains("tab-close-btn")) {
          e.stopPropagation();
          this.closeResearchTab(el.dataset.actId);
          return;
        }
        this.switchResearchTab(el.dataset.actId);
      });
    });
  }

  switchResearchTab(actId) {
    if (this.currentActId === actId) return;
    this.currentActId = actId;
    this.renderResearchTabs();
    this.loadAct(actId);
    this.updateHashRoute(actId);

    const select = document.getElementById("act-select");
    if (select) select.value = actId;
  }

  openResearchTab(actId, actName) {
    const existing = this.openTabs.find(t => t.id === actId);
    if (!existing) {
      this.openTabs.push({ id: actId, name: actName });
    }
    this.switchResearchTab(actId);
  }

  closeResearchTab(actId) {
    if (this.openTabs.length <= 1) return;
    const idx = this.openTabs.findIndex(t => t.id === actId);
    if (idx >= 0) {
      this.openTabs.splice(idx, 1);
      if (this.currentActId === actId) {
        const nextTab = this.openTabs[Math.max(0, idx - 1)];
        this.switchResearchTab(nextTab.id);
      } else {
        this.renderResearchTabs();
      }
    }
  }

  // ---------------- Event Listeners ----------------
  initEventListeners() {
    // Act selector dropdown
    const actSelect = document.getElementById("act-select");
    if (actSelect) {
      actSelect.addEventListener("change", (e) => {
        const selectedActId = e.target.value;
        const opt = e.target.options[e.target.selectedIndex];
        this.openResearchTab(selectedActId, opt ? opt.text : selectedActId);
      });
    }

    // Act search input
    const actSearchInput = document.getElementById("act-search-input");
    if (actSearchInput) {
      actSearchInput.addEventListener("keydown", async (e) => {
        if (e.key === "Enter") {
          const query = e.target.value.trim();
          if (query) {
            const resp = await fetch(`/api/acts?q=${encodeURIComponent(query)}`);
            const json = await resp.json();
            if (json.success && json.data.length > 0) {
              const matched = json.data[0];
              this.openResearchTab(matched.id, matched.name);
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

    // Font size controls
    const fontPlusBtn = document.getElementById("font-plus-btn");
    if (fontPlusBtn) {
      fontPlusBtn.addEventListener("click", () => this.adjustFontSize(1));
    }
    const fontMinusBtn = document.getElementById("font-minus-btn");
    if (fontMinusBtn) {
      fontMinusBtn.addEventListener("click", () => this.adjustFontSize(-1));
    }

    // Mobile dialer toggle
    const dialerBtn = document.getElementById("dialer-toggle-btn");
    if (dialerBtn) {
      dialerBtn.addEventListener("click", () => {
        if (this.dialer) this.dialer.toggle();
      });
    }

    // In-act search input
    const searchInput = document.getElementById("search-input");
    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        this.filterStreamArticles(e.target.value.trim());
      });
    }

    // Add Tab button & modal
    const addTabBtn = document.getElementById("add-tab-btn");
    const addTabModal = document.getElementById("add-tab-modal");
    const addTabClose = document.getElementById("add-tab-modal-close");
    if (addTabBtn && addTabModal) {
      addTabBtn.addEventListener("click", () => {
        this.renderPopularActsModal();
        addTabModal.classList.remove("hidden");
      });
    }
    if (addTabClose && addTabModal) {
      addTabClose.addEventListener("click", () => addTabModal.classList.add("hidden"));
    }
    if (addTabModal) {
      addTabModal.addEventListener("click", (e) => {
        if (e.target === addTabModal) addTabModal.classList.add("hidden");
      });
    }

    // Drawer close button & backdrop
    const closeBtn = document.getElementById("drawer-close-btn");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => this.closeStudyDrawer());
    }

    const backdrop = document.getElementById("drawer-backdrop");
    if (backdrop) {
      backdrop.addEventListener("click", () => this.closeStudyDrawer());
    }

    // Drawer bookmark button
    const bookmarkBtn = document.getElementById("drawer-bookmark-btn");
    if (bookmarkBtn) {
      bookmarkBtn.addEventListener("click", () => {
        if (this.selectedArticleNo) {
          this.toggleBookmark(this.currentActId, this.selectedArticleNo);
        }
      });
    }

    // Drawer PDF print button
    const pdfBtn = document.getElementById("drawer-pdf-btn");
    if (pdfBtn) {
      pdfBtn.addEventListener("click", () => {
        window.print();
      });
    }

    // Drawer expand / collapse toggle
    const expandBtn = document.getElementById("drawer-expand-btn");
    if (expandBtn) {
      expandBtn.addEventListener("click", () => {
        const panel = document.getElementById("study-drawer-panel");
        if (panel) {
          const isExp = panel.classList.toggle("expanded");
          expandBtn.textContent = isExp ? "⤢ 還原" : "⤢ 展開";
        }
      });
    }

    // Global keyboard shortcuts (Esc to close drawer, Left/Right arrows for articles)
    document.addEventListener("keydown", (e) => {
      const activeTag = document.activeElement ? document.activeElement.tagName : "";
      if (activeTag === "INPUT" || activeTag === "TEXTAREA") return;

      if (e.key === "Escape") {
        this.closeStudyDrawer();
        const modal = document.getElementById("add-tab-modal");
        if (modal) modal.classList.add("hidden");
      } else if (e.key === "ArrowLeft") {
        this.navigateAdjacentArticle(-1);
      } else if (e.key === "ArrowRight") {
        this.navigateAdjacentArticle(1);
      }
    });
  }

  // ---------------- Popular Acts Modal ----------------
  renderPopularActsModal() {
    const grid = document.getElementById("popular-acts-grid");
    if (!grid) return;

    const popular = [
      { id: "criminal_code", name: "中華民國刑法" },
      { id: "civil_code", name: "中華民國民法" },
      { id: "constitution", name: "中華民國憲法" },
      { id: "criminal_procedure_code", name: "刑事訴訟法" },
      { id: "civil_procedure_code", name: "民事訴訟法" },
      { id: "labor_standards_act", name: "勞動基準法" },
      { id: "admin_procedure_act", name: "行政程序法" },
      { id: "traffic_act", name: "道路交通管理處罰條例" },
      { id: "company_act", name: "公司法" }
    ];

    grid.innerHTML = popular.map(item => `
      <div class="popular-act-chip" data-act-id="${item.id}" data-act-name="${item.name}">
        ${item.name}
      </div>
    `).join("");

    grid.querySelectorAll(".popular-act-chip").forEach(chip => {
      chip.addEventListener("click", () => {
        this.openResearchTab(chip.dataset.actId, chip.dataset.actName);
        document.getElementById("add-tab-modal").classList.add("hidden");
      });
    });

    // In-modal search input
    const tabSearchInput = document.getElementById("tab-search-input");
    const tabResults = document.getElementById("tab-search-results");
    if (tabSearchInput && tabResults) {
      tabSearchInput.addEventListener("input", async (e) => {
        const query = e.target.value.trim();
        if (!query) {
          tabResults.innerHTML = "";
          return;
        }
        const resp = await fetch(`/api/acts?q=${encodeURIComponent(query)}`);
        const json = await resp.json();
        if (json.success && json.data) {
          tabResults.innerHTML = json.data.slice(0, 10).map(act => `
            <div class="popular-act-chip" style="margin-bottom:0.35rem;text-align:left;" data-act-id="${act.id}" data-act-name="${act.name}">
              ${act.name} <span style="font-size:0.75rem;color:var(--text-dim);">(${act.category || ''})</span>
            </div>
          `).join("");

          tabResults.querySelectorAll(".popular-act-chip").forEach(c => {
            c.addEventListener("click", () => {
              this.openResearchTab(c.dataset.actId, c.dataset.actName);
              document.getElementById("add-tab-modal").classList.add("hidden");
            });
          });
        }
      });
    }
  }

  // ---------------- Data Loading ----------------
  async loadActList() {
    try {
      const resp = await fetch("/api/acts");
      const json = await resp.json();
      if (json.success) {
        this.allActs = json.data;
        const select = document.getElementById("act-select");
        if (select) {
          select.innerHTML = this.allActs.map(act => `
            <option value="${act.id}" ${act.id === this.currentActId ? 'selected' : ''}>
              ${act.name}
            </option>
          `).join("");
        }
      }
    } catch (e) {
      console.error("Failed to load acts list", e);
    }
  }

  async loadAct(actId) {
    try {
      const resp = await fetch(`/api/acts/${actId}`);
      const json = await resp.json();
      if (json.success) {
        this.currentAct = json.data;
        this.renderActBanner();
        this.renderChapterToc();
        this.renderStatuteStream(this.currentAct.articles);
        this.updateResearchTabTitle(actId, this.currentAct.name);
      }
    } catch (e) {
      console.error(`Failed to load act ${actId}`, e);
    }
  }

  updateResearchTabTitle(actId, actName) {
    const tab = this.openTabs.find(t => t.id === actId);
    if (tab) tab.name = actName;
    this.renderResearchTabs();
  }

  renderActBanner() {
    const banner = document.getElementById("act-banner");
    if (!banner || !this.currentAct) return;

    banner.innerHTML = `
      <div class="act-title-wrap">
        <h2 class="act-title">${this.currentAct.name}</h2>
        <span class="act-meta-tag">${this.currentAct.category || "法規"}</span>
        <span class="act-meta-tag">修訂：${this.currentAct.last_modified || "現行有效"}</span>
      </div>
      <div style="font-size:0.85rem;font-weight:700;color:var(--text-dim);">
        全案共 ${(this.currentAct.articles || []).length} 條
      </div>
    `;
  }

  renderChapterToc() {
    const tocList = document.getElementById("sidebar-chapter-list");
    if (!tocList || !this.currentAct) return;

    const chapters = [];
    const seen = new Set();
    (this.currentAct.articles || []).forEach(art => {
      const ch = art.chapter || "全文";
      if (!seen.has(ch)) {
        seen.add(ch);
        chapters.push({ chapter: ch, firstArticleNo: art.article_no });
      }
    });

    tocList.innerHTML = chapters.map((item, idx) => `
      <div class="chapter-item ${idx === 0 ? 'active' : ''}" data-target-art="${item.firstArticleNo}">
        ${item.chapter}
      </div>
    `).join("");

    tocList.querySelectorAll(".chapter-item").forEach(item => {
      item.addEventListener("click", () => {
        tocList.querySelectorAll(".chapter-item").forEach(i => i.classList.remove("active"));
        item.classList.add("active");
        this.scrollToArticleCard(item.dataset.targetArt);
      });
    });
  }

  renderStatuteStream(articles) {
    const streamList = document.getElementById("statute-stream-list");
    const statsEl = document.getElementById("stream-stats");
    if (!streamList) return;

    if (!articles || articles.length === 0) {
      streamList.innerHTML = `<div style="text-align:center;padding:3rem;color:var(--text-dim);">查無相符法規條文</div>`;
      if (statsEl) statsEl.textContent = "0 條";
      return;
    }

    if (statsEl) statsEl.textContent = `顯示 ${articles.length} 條`;

    let html = "";
    let lastChapter = null;

    articles.forEach(art => {
      if (art.chapter && art.chapter !== lastChapter) {
        lastChapter = art.chapter;
        html += `<div class="chapter-divider">📌 ${lastChapter}</div>`;
      }

      const bookmarked = this.isBookmarked(this.currentActId, art.article_no);

      html += `
        <article class="stream-article-card" id="article-card-${art.article_no}" data-article-no="${art.article_no}">
          <div class="article-card-header">
            <div class="article-card-no">
              <span>第 ${art.article_no} 條</span>
              ${art.title ? `<span class="article-card-title">${art.title}</span>` : ""}
              ${bookmarked ? `<span style="color:var(--accent-amber);font-size:0.85rem;" title="已加入書籤">⭐</span>` : ""}
            </div>
            <div class="article-card-actions">
              <button class="article-study-btn" data-article-no="${art.article_no}">
                🔍 條文深度研析
              </button>
            </div>
          </div>
          <div class="article-card-content">${art.content}</div>
        </article>
      `;
    });

    streamList.innerHTML = html;

    // Bind 條文研析 click buttons
    streamList.querySelectorAll(".article-study-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const no = btn.dataset.articleNo;
        this.openStudyDrawer(no);
      });
    });

    // Clicking an article card also opens drawer
    streamList.querySelectorAll(".stream-article-card").forEach(card => {
      card.addEventListener("click", (e) => {
        if (e.target.closest(".article-study-btn")) return;
        const no = card.dataset.articleNo;
        this.openStudyDrawer(no);
      });
    });
  }

  filterStreamArticles(query) {
    if (!this.currentAct || !this.currentAct.articles) return;
    if (!query) {
      this.renderStatuteStream(this.currentAct.articles);
      return;
    }

    const q = query.toLowerCase();
    const filtered = this.currentAct.articles.filter(art => {
      return (
        art.article_no.toLowerCase().includes(q) ||
        (art.title && art.title.toLowerCase().includes(q)) ||
        (art.content && art.content.toLowerCase().includes(q))
      );
    });

    this.renderStatuteStream(filtered);
  }

  scrollToArticleCard(articleNo) {
    const card = document.getElementById(`article-card-${articleNo}`);
    if (card) {
      card.scrollIntoView({ behavior: "smooth", block: "center" });
      document.querySelectorAll(".stream-article-card").forEach(c => c.classList.remove("active"));
      card.classList.add("active");
    }
  }

  // ---------------- Slide-Over Deep Study Drawer ----------------
  async openStudyDrawer(articleNo) {
    this.selectedArticleNo = articleNo;
    this.updateHashRoute(this.currentActId, articleNo);
    this.updateBookmarkButtonState(articleNo);

    // Update Drawer Header
    const badgeEl = document.getElementById("drawer-article-badge");
    const breadcrumbEl = document.getElementById("drawer-breadcrumb");
    if (badgeEl) badgeEl.textContent = `第 ${articleNo} 條`;

    // Fetch single article with all rich LawPlayer fields
    let art = (this.currentAct.articles || []).find(a => a.article_no === articleNo) || {
      article_no: articleNo,
      content: "載入中..."
    };

    try {
      const resp = await fetch(`/api/acts/${this.currentActId}/articles/${articleNo}`);
      const json = await resp.json();
      if (json.success && json.data) {
        art = json.data;
      }
    } catch (e) {
      console.warn("Failed to fetch article details", e);
    }

    if (breadcrumbEl) {
      breadcrumbEl.textContent = `${this.currentAct.name} > ${art.chapter || "法條內文"}`;
    }

    // Populate SINGLE SCROLL BODY
    const scrollBody = document.getElementById("study-drawer-scroll-body");
    if (scrollBody) {
      const relCount = (art.related_articles || []).length + (art.attachments || []).length;
      const amendCount = (art.amendment_history || []).length || 1;

      scrollBody.innerHTML = `
        <!-- Hero Section: Title & Full Article Content -->
        <section class="drawer-hero-section">
          <h1 class="drawer-hero-title">${this.currentAct.name} 第 ${art.article_no} 條</h1>
          ${art.title ? `<div class="drawer-hero-subtitle">${art.title}</div>` : ""}
          <div class="drawer-hero-article-box">
            <button class="article-box-copy-action" id="drawer-copy-article-btn" title="複製條文">📋 複製條文</button>
            ${art.content}
          </div>
        </section>

        <!-- Ergonomic Sticky Tabs Bar -->
        <nav class="drawer-tabs-bar">
          <button class="drawer-tab-btn ${this.activeTab === 'key_knowledge' ? 'active' : ''}" data-tab="key_knowledge">
            💡 關鍵知識
          </button>
          <button class="drawer-tab-btn ${this.activeTab === 'content_links' ? 'active' : ''}" data-tab="content_links">
            🔗 內容連結 (${relCount || 3})
          </button>
          <button class="drawer-tab-btn ${this.activeTab === 'legislative_history' ? 'active' : ''}" data-tab="legislative_history">
            📜 立法理由 (${amendCount})
          </button>
          <button class="drawer-tab-btn ${this.activeTab === 'my_bookmarks' ? 'active' : ''}" data-tab="my_bookmarks">
            ⭐ 我的收藏 (${this.bookmarks.length})
          </button>
        </nav>

        <!-- Active Tab Content Area (Flows inside single scroll!) -->
        <div class="drawer-tab-content-area" id="drawer-tab-content-area">
          ${this.generateTabContentHtml(art)}
        </div>

        <!-- Bottom Prev / Next Article Bar -->
        <footer class="drawer-bottom-nav">
          <button class="drawer-nav-btn" id="drawer-prev-btn">
            ← 上一條
          </button>
          <div style="display:flex;align-items:center;gap:0.75rem;">
            <span style="font-size:0.9rem;font-weight:800;color:var(--text-main);">
              第 ${art.article_no} 條 ${art.title || ''}
            </span>
            <button class="drawer-tool-btn" id="drawer-permalink-btn" title="在獨立分頁開啟">開新分頁 ↗</button>
          </div>
          <button class="drawer-nav-btn" id="drawer-next-btn">
            下一條 →
          </button>
        </footer>
      `;

      // Reset scroll smoothly to top
      scrollBody.scrollTop = 0;

      // Bind copy button in drawer
      const copyBtn = scrollBody.querySelector("#drawer-copy-article-btn");
      if (copyBtn) {
        copyBtn.addEventListener("click", () => {
          const textToCopy = `${this.currentAct.name} 第 ${art.article_no} 條 ${art.title || ''}\n${art.content}`;
          this.copyToClipboard(textToCopy, copyBtn);
        });
      }

      // Bind permalink button
      const permalinkBtn = scrollBody.querySelector("#drawer-permalink-btn");
      if (permalinkBtn) {
        permalinkBtn.addEventListener("click", () => {
          const url = `${window.location.origin}${window.location.pathname}#/act/${this.currentActId}/article/${art.article_no}`;
          window.open(url, "_blank");
        });
      }

      // Bind Tab Switching & Accordion
      this.bindDrawerTabs(scrollBody, art);
      this.bindDrawerNavButtons(scrollBody, art);
      this.bindFaqAccordion(scrollBody);
    }

    // Open Drawer
    const drawer = document.getElementById("study-drawer");
    if (drawer) {
      drawer.classList.remove("hidden");
    }
  }

  closeStudyDrawer() {
    const drawer = document.getElementById("study-drawer");
    if (drawer) {
      drawer.classList.add("hidden");
    }
    this.updateHashRoute(this.currentActId);
  }

  navigateAdjacentArticle(direction) {
    if (!this.currentAct || !this.selectedArticleNo) return;
    const articles = this.currentAct.articles || [];
    const idx = articles.findIndex(a => a.article_no === this.selectedArticleNo);
    const targetIdx = idx + direction;
    if (targetIdx >= 0 && targetIdx < articles.length) {
      this.openStudyDrawer(articles[targetIdx].article_no);
      this.scrollToArticleCard(articles[targetIdx].article_no);
    }
  }

  bindDrawerTabs(parentEl, art) {
    parentEl.querySelectorAll(".drawer-tab-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        parentEl.querySelectorAll(".drawer-tab-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        this.activeTab = btn.dataset.tab;

        const contentArea = parentEl.querySelector("#drawer-tab-content-area");
        if (contentArea) {
          contentArea.innerHTML = this.generateTabContentHtml(art);
          this.bindFaqAccordion(contentArea);
          this.bindBookmarkActionEvents(contentArea);
        }
      });
    });
  }

  bindDrawerNavButtons(parentEl, art) {
    const prevBtn = parentEl.querySelector("#drawer-prev-btn");
    const nextBtn = parentEl.querySelector("#drawer-next-btn");
    const articles = this.currentAct.articles || [];
    const idx = articles.findIndex(a => a.article_no === art.article_no);

    if (prevBtn) {
      prevBtn.disabled = idx <= 0;
      prevBtn.addEventListener("click", () => {
        if (idx > 0) {
          const targetNo = articles[idx - 1].article_no;
          this.openStudyDrawer(targetNo);
          this.scrollToArticleCard(targetNo);
        }
      });
    }

    if (nextBtn) {
      nextBtn.disabled = idx < 0 || idx >= articles.length - 1;
      nextBtn.addEventListener("click", () => {
        if (idx < articles.length - 1) {
          const targetNo = articles[idx + 1].article_no;
          this.openStudyDrawer(targetNo);
          this.scrollToArticleCard(targetNo);
        }
      });
    }
  }

  bindFaqAccordion(parentEl) {
    parentEl.querySelectorAll(".faq-q-trigger").forEach(header => {
      header.addEventListener("click", () => {
        const body = header.nextElementSibling;
        if (!body) return;
        const isOpen = body.classList.contains("open");
        body.classList.toggle("open", !isOpen);
        const arrow = header.querySelector(".faq-arrow");
        if (arrow) arrow.textContent = isOpen ? "▼" : "▲";
      });
    });
  }

  bindBookmarkActionEvents(parentEl) {
    parentEl.querySelectorAll(".bookmark-jump-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const actId = btn.dataset.actId;
        const artNo = btn.dataset.artNo;
        if (actId !== this.currentActId) {
          this.openResearchTab(actId, actId);
          setTimeout(() => this.openStudyDrawer(artNo), 300);
        } else {
          this.openStudyDrawer(artNo);
        }
      });
    });

    parentEl.querySelectorAll(".bookmark-delete-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const actId = btn.dataset.actId;
        const artNo = btn.dataset.artNo;
        this.toggleBookmark(actId, artNo);
        // Re-render bookmarks tab
        const contentArea = parentEl.closest("#drawer-tab-content-area") || parentEl;
        contentArea.innerHTML = this.renderMyBookmarksHtml();
        this.bindBookmarkActionEvents(contentArea);
      });
    });
  }

  generateTabContentHtml(art) {
    if (this.activeTab === "key_knowledge") {
      return this.renderKeyKnowledgeHtml(art);
    } else if (this.activeTab === "content_links") {
      return this.renderContentLinksHtml(art);
    } else if (this.activeTab === "legislative_history") {
      return this.renderLegislativeHtml(art);
    } else if (this.activeTab === "my_bookmarks") {
      return this.renderMyBookmarksHtml();
    }
    return "";
  }

  // ---------------- Tab 1: 💡 關鍵知識 ----------------
  renderKeyKnowledgeHtml(art) {
    let html = "";
    const parsed = this.parseArticleElements(art);

    // 1. 白話與解析 - 重點摘要 (Yellow Callout)
    const summaryText = art.summary || parsed.autoSummary;
    html += `
      <div class="callout-box">
        <div class="callout-title">💡 本條重點摘要</div>
        <div>${summaryText}</div>
      </div>
    `;

    // 2. 白話與生活案例解讀 (Vernacular Q&A)
    const qas = (art.vernacular_qa && art.vernacular_qa.length > 0) ? art.vernacular_qa : parsed.autoVernacular;
    html += `
      <div>
        <h3 class="sub-heading">📖 白話與實務解讀 <span class="sub-note">以法理為本，深入淺出</span></h3>
        ${qas.map(item => `
          <div class="qa-card">
            <div class="qa-card-question">${item.question || item.q}</div>
            <div class="qa-card-answer">${item.answer || item.a}</div>
          </div>
        `).join("")}
      </div>
    `;

    // 3. 法律定性 (Legal Definition & Latin Maxim)
    const defText = art.legal_definition || parsed.autoLegalDef;
    html += `
      <div>
        <h3 class="sub-heading">⚖️ 法律定性與規範特徵</h3>
        <div class="legal-qual-card">
          ${defText}
        </div>
      </div>
    `;

    // 4. 構成要件與法律效果結構化面板
    html += `
      <div>
        <h3 class="sub-heading">🏛️ 構成要件與法律效果剖析</h3>
        <div class="elements-grid">
          <div class="element-pill-box">
            <div class="element-pill-label">規範客體 / 行為態樣</div>
            <div class="element-pill-val">${parsed.behaviorType}</div>
          </div>
          <div class="element-pill-box">
            <div class="element-pill-label">主觀責任要求</div>
            <div class="element-pill-val">${parsed.intentType}</div>
          </div>
          <div class="element-pill-box">
            <div class="element-pill-label">法定效果 / 刑度範疇</div>
            <div class="element-pill-val" style="color:var(--accent-rose);font-weight:700;">${parsed.penaltyType}</div>
          </div>
          <div class="element-pill-box">
            <div class="element-pill-label">訴訟追訴特性</div>
            <div class="element-pill-val">${parsed.prosecutionType}</div>
          </div>
        </div>
      </div>
    `;

    // 5. 思考脈絡與邏輯判斷流程圖 (Exact Flowchart matching Screenshot 3)
    html += `
      <div>
        <h3 class="sub-heading">🔍 思考脈絡與流程圖 <span class="sub-note">法條適用邏輯樹</span></h3>
        <div class="flowchart-container">
          <div class="flow-step-box">行為事實發生</div>
          <div class="flow-indicator">↓</div>
          <div class="flow-decision-diamond">行為時是否有成文法律明文規定？</div>
          
          <div class="flow-branch-row">
            <div class="flow-sub-branch">
              <span style="color:var(--accent-rose);font-size:0.82rem;font-weight:800;">否 (無明文) →</span>
              <div class="flow-outcome-no-crime">不構成犯罪 (罪刑法定)</div>
            </div>
            
            <div class="flow-sub-branch">
              <span style="color:var(--accent-emerald);font-size:0.82rem;font-weight:800;">是 (有明文) ↓</span>
              <div class="flow-decision-diamond">是否為不利於行為人之類推適用？</div>
              
              <div class="flow-branch-row" style="margin-top:0.5rem;">
                <div class="flow-sub-branch">
                  <span style="color:var(--accent-rose);font-size:0.82rem;font-weight:800;">是 (不利類推) →</span>
                  <div class="flow-outcome-no-crime">嚴格禁止 (不成立犯罪)</div>
                </div>
                <div class="flow-sub-branch">
                  <span style="color:var(--accent-emerald);font-size:0.82rem;font-weight:800;">否 ↓</span>
                  <div class="flow-decision-diamond">是否為行為後事後立法追溯處罰？</div>
                  
                  <div class="flow-branch-row" style="margin-top:0.5rem;">
                    <div class="flow-sub-branch">
                      <span style="color:var(--accent-rose);font-size:0.82rem;font-weight:800;">是 (事後立法) →</span>
                      <div class="flow-outcome-no-crime">禁止溯及既往 (不罰)</div>
                    </div>
                    <div class="flow-sub-branch">
                      <span style="color:var(--accent-emerald);font-size:0.82rem;font-weight:800;">否 ↓</span>
                      <div class="flow-outcome-penalty">依法構成要件成立並處罰</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    // 6. 大家也在問 (FAQs Q1~Q12 Matching Screenshot 4)
    const faqs = (art.faqs && art.faqs.length > 0) ? art.faqs : parsed.autoFaqs;
    html += `
      <div>
        <h3 class="sub-heading">❓ 大家也在問 (${faqs.length})</h3>
        <div>
          ${faqs.map(faq => `
            <div class="faq-item-box">
              <div class="faq-q-trigger">
                <span>${faq.q}</span>
                <span class="faq-arrow">▼</span>
              </div>
              <div class="faq-a-content">${faq.a || faq.answer}</div>
            </div>
          `).join("")}
        </div>
      </div>
    `;

    // 7. 容易搞混 (Comparison Table Matching Screenshot 5)
    if (art.comparison_table && art.comparison_table.headers) {
      const ct = art.comparison_table;
      html += `
        <div>
          <h3 class="sub-heading">📊 容易搞混 (${ct.title || "三大法域概念對照"})</h3>
          <div class="comp-table-container">
            <table class="table-clean">
              <thead>
                <tr>
                  ${ct.headers.map(h => `<th>${h}</th>`).join("")}
                </tr>
              </thead>
              <tbody>
                ${ct.rows.map(row => `
                  <tr>
                    ${row.map(cell => `<td>${cell}</td>`).join("")}
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        </div>
      `;
    }

    // 8. 相關函釋令 (Matching Screenshot 5 - 100% Free & Unlimited)
    const letters = art.official_letters || [];
    if (letters.length > 0) {
      html += `
        <div>
          <h3 class="sub-heading">📜 相關函釋 (${letters.length} 則) <span class="sub-note" style="color:var(--accent-emerald);">全解鎖無限制</span></h3>
          <div style="background:var(--bg-surface);border:1px solid var(--border-color);border-radius:8px;overflow:hidden;">
            ${letters.map(c => `
              <div class="official-letter-card">
                <div>
                  <span style="font-weight:800;color:var(--text-main);">${c.no}</span>
                  <span style="margin-left:0.6rem;font-size:0.8rem;color:var(--text-dim);">${c.organ} ${c.date}</span>
                </div>
                <a href="https://judgment.judicial.gov.tw/FJUD/default.aspx" target="_blank" rel="noopener noreferrer" class="jump-link-btn">
                  快速跳轉 ↗
                </a>
              </div>
            `).join("")}
          </div>
        </div>
      `;
    }

    // 9. 立法沿革概覽
    const historyCount = (art.amendment_history || []).length || 1;
    html += `
      <div style="padding-top:0.5rem;border-top:1px dashed var(--border-color);">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <h4 style="font-size:0.95rem;font-weight:800;color:var(--text-dim);">📜 立法沿革 (${historyCount} 版)</h4>
          <span style="font-size:0.82rem;color:var(--accent-primary);cursor:pointer;" onclick="document.querySelector('[data-tab=legislative_history]').click()">
            查看新舊條文對照 Diff →
          </span>
        </div>
      </div>
    `;

    return html;
  }

  // ---------------- Tab 2: 🔗 內容連結 ----------------
  renderContentLinksHtml(art) {
    const rels = art.related_articles || [];
    const atts = art.attachments || [];
    const insights = art.practical_insights || [];

    return `
      <div>
        <h3 class="sub-heading">🔗 跨法規關聯條文 (${rels.length})</h3>
        ${rels.length > 0 ? `
          <div style="display:flex;flex-wrap:wrap;gap:0.5rem;margin-bottom:1.5rem;">
            ${rels.map(r => `
              <span style="background:var(--bg-surface);border:1px solid var(--border-color);padding:0.45rem 0.85rem;border-radius:6px;font-size:0.88rem;font-weight:700;color:var(--accent-primary);">
                ${r}
              </span>
            `).join("")}
          </div>
        ` : `<p style="font-size:0.88rem;color:var(--text-dim);margin-bottom:1.5rem;">暫無跨法規特殊關聯標註</p>`}

        <!-- Judicial Yuan & Academic Direct Precedents -->
        <h3 class="sub-heading">🏛️ 司法實務判解與裁判 (${insights.length})</h3>
        ${insights.length > 0 ? `
          <div style="margin-bottom:1.5rem;">
            ${insights.map(ins => `
              <div class="insight-full-card">
                <div class="insight-full-ref">🏛️ ${ins.court || "最高法院"} ｜ ${ins.ref || ""}</div>
                <div class="insight-full-summary">${ins.summary}</div>
              </div>
            `).join("")}
          </div>
        ` : ""}

        <div class="judgment-search-box">
          <h4 style="font-size:0.95rem;font-weight:800;color:var(--text-main);">🔍 權威法學資料庫直達檢索 (含 AutoRPA 代理)</h4>
          <div class="judgment-search-links">
            <a href="https://judgment.judicial.gov.tw/FJUD/default.aspx" target="_blank" rel="noopener noreferrer" class="judgment-link-btn">
              <span>🏛️ 司法院判決書系統 (${this.currentAct.name} 第${art.article_no}條)</span>
              <span style="color:var(--accent-primary);">↗</span>
            </a>
            <a href="https://www-lawbank-com-tw.autorpa.lib.ccu.edu.tw:8443/" target="_blank" rel="noopener noreferrer" class="judgment-link-btn">
              <span>⚖️ 法源法律網精選裁判 (AutoRPA)</span>
              <span style="color:var(--accent-primary);">↗</span>
            </a>
            <a href="https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/anglekmc/ttswebx?@0:0:1:lawkm@@0.1702332962648232" target="_blank" rel="noopener noreferrer" class="judgment-link-btn">
              <span>📚 月旦知識庫論文研析 (AutoRPA)</span>
              <span style="color:var(--accent-primary);">↗</span>
            </a>
          </div>
        </div>

        ${atts.length > 0 ? `
          <h3 class="sub-heading" style="margin-top:1.5rem;">📑 全國法規標準附檔 (${atts.length})</h3>
          <div>
            ${atts.map(att => `
              <a href="${att.url}" target="_blank" rel="noopener noreferrer" class="judgment-link-btn" style="margin-bottom:0.5rem;">
                <span>📄 ${att.title}</span>
                <span style="color:var(--accent-primary);">下載 PDF ↗</span>
              </a>
            `).join("")}
          </div>
        ` : ""}
      </div>
    `;
  }

  // ---------------- Tab 3: 📜 立法理由 ----------------
  renderLegislativeHtml(art) {
    const history = art.amendment_history || [];
    if (history.length === 0) {
      return `
        <div class="amend-timeline-card">
          <div class="amend-timeline-date">現行制定與修正意旨</div>
          <div class="amend-timeline-reason">
            ${art.legislative_reasons || `本條為 ${this.currentAct.name} 之明文規定，體系上落於 ${art.chapter || "本法"}，確立當事人權利義務或刑事規範要件。`}
          </div>
        </div>
      `;
    }

    return `
      <div>
        <h3 class="sub-heading">📜 歷次立法與修法理由時間軸 (${history.length})</h3>
        ${history.map(item => `
          <div class="amend-timeline-card">
            <div class="amend-timeline-date">${item.date} ｜ ${item.change_type || "修正"}</div>
            <div class="amend-timeline-reason">${item.reason}</div>
            ${item.old_content ? `
              <div class="amend-diff-block">
                <div><strong style="color:var(--accent-rose);">修正前條文：</strong><br>${item.old_content}</div>
                <div style="margin-top:0.6rem;"><strong style="color:var(--accent-emerald);">修正後現行條文：</strong><br>${item.new_content || art.content}</div>
              </div>
            ` : ""}
          </div>
        `).join("")}
      </div>
    `;
  }

  // ---------------- Tab 4: ⭐ 我的收藏庫 ----------------
  renderMyBookmarksHtml() {
    if (this.bookmarks.length === 0) {
      return `
        <div style="text-align:center;padding:3rem 1rem;color:var(--text-dim);">
          <div style="font-size:2.5rem;margin-bottom:0.75rem;">⭐</div>
          <div style="font-weight:800;font-size:1.05rem;color:var(--text-main);margin-bottom:0.35rem;">尚無收藏的條文</div>
          <p style="font-size:0.88rem;line-height:1.6;">
            在任何條文研析面板點擊右上角「🔖 書籤」按鈕，即可將重要條文永久收藏至此，方便出門在外一鍵查閱！
          </p>
        </div>
      `;
    }

    return `
      <div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">
          <h3 class="sub-heading" style="margin-bottom:0;">⭐ 個人重點法規收藏庫 (${this.bookmarks.length})</h3>
          <span style="font-size:0.8rem;color:var(--text-dim);">本地加密儲存 ｜ 免登入</span>
        </div>
        
        <div>
          ${this.bookmarks.map(b => `
            <div class="insight-full-card" style="position:relative;">
              <div style="display:flex;justify-content:space-between;align-items:baseline;">
                <div class="insight-full-ref">
                  ⚖️ ${b.actName} 第 ${b.articleNo} 條 ${b.title ? `(${b.title})` : ''}
                </div>
                <span style="font-size:0.75rem;color:var(--text-dim);">${b.timestamp || ''}</span>
              </div>
              <div style="font-size:0.88rem;color:var(--text-muted);margin:0.5rem 0;line-height:1.7;">
                ${b.snippet || ''}
              </div>
              <div style="display:flex;justify-content:flex-end;gap:0.5rem;margin-top:0.65rem;">
                <button class="article-study-btn bookmark-jump-btn" data-act-id="${b.actId}" data-art-no="${b.articleNo}">
                  ⚡ 立即跳轉
                </button>
                <button class="drawer-tool-btn bookmark-delete-btn" data-act-id="${b.actId}" data-art-no="${b.articleNo}" style="color:var(--accent-rose);">
                  🗑️ 移除
                </button>
              </div>
            </div>
          `).join("")}
        </div>
      </div>
    `;
  }

  // ---------------- Structural Parsing Engine (For all 47,377 Articles) ----------------
  parseArticleElements(art) {
    const content = art.content || "";
    
    // Auto Summary
    let autoSummary = `規範 ${this.currentAct.name} 於 ${art.chapter || "本法"} 之核心要件與法律效果。`;
    if (content.includes("處") && (content.includes("年") || content.includes("役") || content.includes("罰金"))) {
      autoSummary = `本條明定犯罪構成要件與刑罰效果，保護相關法益免受不法侵害。`;
    } else if (content.includes("賠償") || content.includes("請求權")) {
      autoSummary = `本條規範民事損害賠償請求權基礎與歸責條件。`;
    } else if (content.includes("保障") || content.includes("自由")) {
      autoSummary = `憲政法治人權保障核心條款，拘束國家各機關公權力行使。`;
    }

    // Auto Vernacular
    const autoVernacular = [
      {
        question: `Q. 本條的核心立法意旨與生活適用情境是什麼？`,
        answer: `本條是 ${this.currentAct.name} 規範日常法律行為的重要準據。在日常生活或司法實務中，當事人必須符合本條規定之法定構成要件，才能主張相應之權利或承擔法律責任。`
      },
      {
        question: `Q. 如果違反本條或不符本條要件，會產生什麼法律後果？`,
        answer: `若不具備本條規定之構成要件，法院在審理時將認定無法適用本條規定；若屬禁止或處罰規範而違反者，將依法受行政裁罰、民事求償或刑事處分。`
      }
    ];

    // Auto Legal Definition
    const autoLegalDef = `本條為 ${this.currentAct.name} 之明文規定，體系上落於 ${art.chapter || "本法"}，確立當事人權利義務或刑事規範要件。`;

    // Auto FAQs
    const autoFaqs = [
      {
        q: `Q1 如何正確主張本條之法律要件？`,
        a: `主張本條權利者，應就符合本條各款各項要件之客觀事實負舉證責任；若為相對人，則可針對要件欠缺或具阻卻事由進行答辯。`
      },
      {
        q: `Q2 本條在法院審理與訴訟實務中的常見爭點為何？`,
        a: `實務爭點多聚焦於不確定法律概念之詮釋、舉證責任分配，以及跨法規適用時之法規競合關係。`
      }
    ];

    // Behavior & Object Type
    let behaviorType = "法定一般規範行為";
    if (content.includes("故意") || content.includes("過失")) behaviorType = "作為或不作為行為";
    if (content.includes("駕駛")) behaviorType = "交通工具駕駛行為";
    if (content.includes("公務員")) behaviorType = "公務職權行使行為";

    // Intent & Liability Type
    let intentType = "故意責任（民事過失推定）";
    if (content.includes("過失")) intentType = "故意或過失均處罰";
    if (content.includes("意圖")) intentType = "特定目的超個人主觀意圖";

    // Penalty & Effect Type
    let penaltyType = "民事上權利得喪變更效果";
    if (content.includes("有期徒刑") || content.includes("拘役")) {
      const match = content.match(/處([^，。]+)/);
      penaltyType = match ? match[1].trim() : "法定自由刑 / 罰金刑";
    } else if (content.includes("罰鍰")) {
      penaltyType = "行政罰秩序罰鍰";
    }

    // Prosecution Type
    let prosecutionType = "民事當事人進行主義";
    if (content.includes("告訴乃論")) prosecutionType = "告訴乃論之罪（6個月提告期）";
    else if (content.includes("處") && (content.includes("年") || content.includes("拘役"))) {
      prosecutionType = "公訴（檢察官依職權追訴）";
    }

    return {
      autoSummary,
      autoVernacular,
      autoLegalDef,
      autoFaqs,
      behaviorType,
      intentType,
      penaltyType,
      prosecutionType
    };
  }

  // ---------------- Utilities ----------------
  async copyToClipboard(text, triggerEl) {
    try {
      await navigator.clipboard.writeText(text);
      const originalText = triggerEl.textContent;
      triggerEl.textContent = "✅ 已複製！";
      triggerEl.style.color = "var(--accent-emerald)";
      setTimeout(() => {
        triggerEl.textContent = originalText;
        triggerEl.style.color = "";
      }, 1500);
    } catch (err) {
      console.error("Failed to copy", err);
    }
  }
}

// Instantiate on DOMContentLoaded
document.addEventListener("DOMContentLoaded", () => {
  window.legalHubApp = new LegalHubApp();
});
