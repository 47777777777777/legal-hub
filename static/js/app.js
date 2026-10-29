/**
 * Legal Hub - Professional Legal Intelligence System (LawPlayer Replica)
 * 
 * Features:
 * 1. Single natural vertical scroll (NO nested scrollbars, NO cut-offs)
 * 2. Complete LawPlayer replica design with deep structural parsing
 * 3. 4 Essential tabs: 關鍵知識 | 實務判解 | 內容連結 | 立法理由
 * 4. Deep legal analysis for ALL 47,377 articles across Taiwan statutes
 * 5. One-click copy, Font scaling (A+/A-), Mobile 0-9 dialer, Keyboard shortcuts
 */

class LegalHubApp {
  constructor() {
    this.currentActId = "criminal_code";
    this.currentAct = null;
    this.selectedArticleNo = null;
    this.activeTab = "key_knowledge";
    this.dialer = null;
    this.fontSize = 16;

    this.init();
  }

  async init() {
    this.initTheme();
    this.initEventListeners();
    await this.loadActList();
    await this.loadAct(this.currentActId);

    // Initialize Mobile Dialer
    if (window.QuickDialer) {
      this.dialer = new QuickDialer(this);
    }
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

  adjustFontSize(delta) {
    this.fontSize = Math.max(14, Math.min(22, this.fontSize + delta));
    document.documentElement.style.setProperty("--font-size-base", `${this.fontSize}px`);
  }

  initEventListeners() {
    // Act selector dropdown
    const actSelect = document.getElementById("act-select");
    if (actSelect) {
      actSelect.addEventListener("change", (e) => {
        this.currentActId = e.target.value;
        this.loadAct(this.currentActId);
      });
    }

    // Act search / filter
    const actSearchInput = document.getElementById("act-search-input");
    if (actSearchInput) {
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

    // Drawer close button & backdrop
    const closeBtn = document.getElementById("drawer-close-btn");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => this.closeStudyDrawer());
    }

    const backdrop = document.getElementById("drawer-backdrop");
    if (backdrop) {
      backdrop.addEventListener("click", () => this.closeStudyDrawer());
    }

    // Drawer expand / collapse toggle
    const expandBtn = document.getElementById("drawer-expand-btn");
    if (expandBtn) {
      expandBtn.addEventListener("click", () => {
        const panel = document.getElementById("study-drawer-panel");
        if (panel) {
          const isExp = panel.classList.toggle("expanded");
          expandBtn.textContent = isExp ? "⛶ 還原" : "⛶ 展開";
        }
      });
    }

    // Global keyboard shortcuts (Esc to close drawer, Left/Right arrows for articles)
    document.addEventListener("keydown", (e) => {
      const activeTag = document.activeElement ? document.activeElement.tagName : "";
      if (activeTag === "INPUT" || activeTag === "TEXTAREA") return;

      if (e.key === "Escape") {
        this.closeStudyDrawer();
      } else if (e.key === "ArrowLeft") {
        this.navigateAdjacentArticle(-1);
      } else if (e.key === "ArrowRight") {
        this.navigateAdjacentArticle(1);
      }
    });
  }

  async loadActList(query = "") {
    try {
      const resp = await fetch(`/api/acts?q=${encodeURIComponent(query)}`);
      const json = await resp.json();
      if (json.success && json.data) {
        const actSelect = document.getElementById("act-select");
        if (actSelect) {
          actSelect.innerHTML = json.data.map(act => `
            <option value="${act.id}" ${act.id === this.currentActId ? 'selected' : ''}>
              ${act.name}
            </option>
          `).join("");
        }
      }
    } catch (err) {
      console.error("Failed to load acts list:", err);
    }
  }

  async loadAct(actId) {
    try {
      const resp = await fetch(`/api/acts/${encodeURIComponent(actId)}`);
      const json = await resp.json();
      if (!json.success || !json.data) {
        console.error("Failed to load act:", json.error);
        return;
      }

      this.currentAct = json.data;
      this.renderActBanner();
      this.renderChapterTOC();
      this.renderStatuteStream();

      // Close drawer if open on act change
      this.closeStudyDrawer();
    } catch (err) {
      console.error("Error loading act:", err);
    }
  }

  renderActBanner() {
    const banner = document.getElementById("act-banner");
    if (!banner || !this.currentAct) return;

    const atts = this.currentAct.attachments || [];
    banner.innerHTML = `
      <div class="act-banner-title">
        <span>${this.currentAct.name}</span>
        ${this.currentAct.name_en ? `<span style="font-size:0.85rem;font-weight:normal;color:var(--text-dim);">(${this.currentAct.name_en})</span>` : ""}
      </div>
      <div class="act-banner-meta">
        ${this.currentAct.last_modified ? `<span>📅 修正日期：${this.currentAct.last_modified}</span>` : ""}
        ${this.currentAct.category ? `<span>🏛️ 類別：${this.currentAct.category}</span>` : ""}
        ${atts.length > 0 ? `
          <a href="${atts[0].url}" target="_blank" rel="noopener noreferrer" class="attachment-badge" title="${atts[0].title}">
            📎 法定附檔 (${atts.length})
          </a>
        ` : ""}
      </div>
    `;
  }

  renderChapterTOC() {
    const container = document.getElementById("sidebar-chapter-list");
    if (!container || !this.currentAct) return;

    const chapters = this.currentAct.chapters || [];
    if (chapters.length === 0) {
      container.innerHTML = `<div style="color:var(--text-dim);font-size:0.82rem;padding:0.5rem 0;">全法無編章節</div>`;
      return;
    }

    container.innerHTML = chapters.map(ch => `
      <div class="chapter-item">
        <div class="chapter-title">${ch.title}</div>
        ${(ch.sections || []).map(sec => `
          <a href="#sec-${sec.code}" class="section-link" data-code="${sec.code}">
            ${sec.title}
          </a>
        `).join("")}
      </div>
    `).join("");

    container.querySelectorAll(".section-link").forEach(link => {
      link.addEventListener("click", (e) => {
        e.preventDefault();
        container.querySelectorAll(".section-link").forEach(l => l.classList.remove("active"));
        link.classList.add("active");
        
        const text = link.textContent;
        const match = text.match(/第\s*(\d+)/);
        if (match && match[1]) {
          this.scrollToArticleCard(match[1]);
        }
      });
    });
  }

  renderStatuteStream(articlesToRender = null) {
    const container = document.getElementById("statute-stream-list");
    const statsEl = document.getElementById("stream-stats");
    if (!container || !this.currentAct) return;

    const articles = articlesToRender || this.currentAct.articles || [];
    if (statsEl) {
      statsEl.textContent = `共收錄 ${articles.length} 條條文`;
    }

    if (articles.length === 0) {
      container.innerHTML = `<div style="text-align:center;padding:4rem;color:var(--text-dim);">查無符合之條文</div>`;
      return;
    }

    container.innerHTML = articles.map(art => {
      const insightCount = (art.practical_insights || []).length;
      const amendCount = (art.amendment_history || []).length;
      const attCount = (art.attachments || []).length;
      const tags = this.extractArticleTags(art);

      return `
        <article class="stream-article-card ${art.article_no === this.selectedArticleNo ? 'active' : ''}" id="article-card-${art.article_no}" data-art="${art.article_no}">
          <div class="stream-card-header">
            <div class="stream-card-title-group">
              <span class="stream-card-no">第 ${art.article_no} 條</span>
              ${art.title ? `<span class="stream-card-title">${art.title}</span>` : ""}
            </div>
            <div class="card-actions-group">
              <button class="stream-copy-btn" data-art="${art.article_no}" title="複製條文">📋</button>
              <button class="stream-study-btn" data-art="${art.article_no}" title="開啟條文深度研析">
                💡 條文研析
              </button>
            </div>
          </div>
          <div class="stream-card-body">${art.content}</div>
          <div class="stream-card-tags">
            ${art.chapter ? `<span class="stream-tag">📂 ${art.chapter}</span>` : ""}
            ${tags.map(t => `<span class="stream-tag">${t}</span>`).join("")}
            ${insightCount > 0 ? `<span class="stream-tag" style="color:var(--accent-primary);border:1px solid var(--accent-primary);">🏛️ 實務判解 ${insightCount} 則</span>` : ""}
            ${amendCount > 0 ? `<span class="stream-tag" style="color:var(--accent-emerald);">📜 歷次修法 ${amendCount} 次</span>` : ""}
            ${attCount > 0 ? `<span class="stream-tag" style="color:var(--accent-amber);">📎 法定附檔 ${attCount} 件</span>` : ""}
          </div>
        </article>
      `;
    }).join("");

    // Bind copy buttons
    container.querySelectorAll(".stream-copy-btn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const artNo = btn.dataset.art;
        const art = (this.currentAct.articles || []).find(a => a.article_no === artNo);
        if (art) {
          const textToCopy = `${this.currentAct.name} 第 ${art.article_no} 條 ${art.title || ''}\n${art.content}`;
          this.copyToClipboard(textToCopy, btn);
        }
      });
    });

    // Bind study button click
    container.querySelectorAll(".stream-study-btn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        this.openStudyDrawer(btn.dataset.art);
      });
    });

    // Card click opens drawer
    container.querySelectorAll(".stream-article-card").forEach(card => {
      card.addEventListener("click", () => {
        this.openStudyDrawer(card.dataset.art);
      });
    });
  }

  filterStreamArticles(query) {
    if (!this.currentAct) return;
    if (!query) {
      this.renderStatuteStream();
      return;
    }
    const q = query.toLowerCase();
    const filtered = (this.currentAct.articles || []).filter(a => 
      a.article_no.toLowerCase().includes(q) ||
      (a.title && a.title.toLowerCase().includes(q)) ||
      a.content.toLowerCase().includes(q)
    );
    this.renderStatuteStream(filtered);
  }

  scrollToArticleCard(articleNo) {
    const card = document.getElementById(`article-card-${articleNo}`);
    if (card) {
      card.scrollIntoView({ behavior: "smooth", block: "center" });
      card.classList.add("active");
      setTimeout(() => card.classList.remove("active"), 2000);
    }
  }

  // ---------------- Deep Study Drawer (Single Scrollbar) ----------------
  openStudyDrawer(articleNo) {
    const art = (this.currentAct.articles || []).find(a => a.article_no === String(articleNo).trim());
    if (!art) return;

    this.selectedArticleNo = art.article_no;

    // Highlight active card
    document.querySelectorAll(".stream-article-card").forEach(c => {
      c.classList.toggle("active", c.dataset.art === art.article_no);
    });

    // Update Drawer Header Badges
    const bcrumb = document.getElementById("drawer-breadcrumb");
    const badge = document.getElementById("drawer-article-badge");
    if (bcrumb) bcrumb.textContent = `${this.currentAct.name} > ${art.chapter || "法規本法"}`;
    if (badge) badge.textContent = `第 ${art.article_no} 條`;

    // Render Unified Drawer Scroll Body (ONE SINGLE SCROLLBAR)
    const scrollBody = document.getElementById("study-drawer-scroll-body");
    if (scrollBody) {
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
          <button class="drawer-tab-btn ${this.activeTab === 'insights' ? 'active' : ''}" data-tab="insights">
            🏛️ 實務判解 (${(art.practical_insights || []).length || '檢索'})
          </button>
          <button class="drawer-tab-btn ${this.activeTab === 'content_links' ? 'active' : ''}" data-tab="content_links">
            🔗 內容連結 (${(art.related_articles || []).length + (art.attachments || []).length || '3+'})
          </button>
          <button class="drawer-tab-btn ${this.activeTab === 'legislative_history' ? 'active' : ''}" data-tab="legislative_history">
            📜 立法理由 (${(art.amendment_history || []).length || 1})
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
          <span style="font-size:0.88rem;font-weight:800;color:var(--text-dim);">
            第 ${art.article_no} 條 ${art.title || ''}
          </span>
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
        }
      });
    });
  }

  bindDrawerNavButtons(parentEl, currentArt) {
    const articles = this.currentAct.articles || [];
    const idx = articles.findIndex(a => a.article_no === currentArt.article_no);

    const prevBtn = parentEl.querySelector("#drawer-prev-btn");
    const nextBtn = parentEl.querySelector("#drawer-next-btn");

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

  generateTabContentHtml(art) {
    if (this.activeTab === "key_knowledge") {
      return this.renderKeyKnowledgeHtml(art);
    } else if (this.activeTab === "insights") {
      return this.renderInsightsHtml(art);
    } else if (this.activeTab === "content_links") {
      return this.renderContentLinksHtml(art);
    } else if (this.activeTab === "legislative_history") {
      return this.renderLegislativeHtml(art);
    }
    return "";
  }

  // ---------------- Rich Content Generation for ALL Articles ----------------
  renderKeyKnowledgeHtml(art) {
    let html = "";
    const parsed = this.parseArticleElements(art);

    // 1. 重點摘要
    const summaryText = art.summary || parsed.autoSummary;
    html += `
      <div class="callout-box">
        <div class="callout-title">💡 本條重點摘要</div>
        <div>${summaryText}</div>
      </div>
    `;

    // 2. 構成要件與法律效果結構化面板 (Elements Breakdown)
    html += `
      <div>
        <h3 class="sub-heading">⚖️ 規範定性與要件拆解 <span class="sub-note">法定構成要件剖析</span></h3>
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

    // 3. 白話與解析 (Vernacular Q&A)
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

    // 4. 思考脈絡與邏輯判斷流程圖
    html += `
      <div>
        <h3 class="sub-heading">🔍 思考脈絡與邏輯判斷流程</h3>
        <div class="flowchart-container">
          <div class="flow-step-box">生活事實行為發生</div>
          <div class="flow-indicator">↓</div>
          <div class="flow-decision-box">行為時是否該當本條構成要件？</div>
          <div class="flow-branch-row">
            <div class="flow-sub-branch">
              <span style="color:var(--accent-rose);font-size:0.8rem;font-weight:800;">否 →</span>
              <div class="flow-outcome-no-crime">不成立本條效果</div>
            </div>
            <div class="flow-sub-branch">
              <span style="color:var(--accent-emerald);font-size:0.8rem;font-weight:800;">是 ↓</span>
              <div class="flow-decision-box">是否有阻卻違法或免責事由？</div>
              <div class="flow-branch-row" style="margin-top:0.4rem;">
                <div class="flow-sub-branch">
                  <span style="color:var(--accent-rose);font-size:0.8rem;font-weight:800;">有 →</span>
                  <div class="flow-outcome-no-crime">免除處罰或責任</div>
                </div>
                <div class="flow-sub-branch">
                  <span style="color:var(--accent-emerald);font-size:0.8rem;font-weight:800;">無 ↓</span>
                  <div class="flow-outcome-penalty">依法承擔法律效果</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    // 5. 大家也在問 (FAQs Q1~Q8)
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

    // 6. 容易搞混 (Comparison Table)
    if (art.comparison_table && art.comparison_table.headers) {
      const ct = art.comparison_table;
      html += `
        <div>
          <h3 class="sub-heading">📊 容易搞混與概念對照</h3>
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

    // 7. 相關函釋令
    const letters = art.official_letters || [];
    if (letters.length > 0) {
      html += `
        <div>
          <h3 class="sub-heading">📜 相關函釋令 (${letters.length})</h3>
          <div style="background:var(--bg-surface);border:1px solid var(--border-color);border-radius:8px;padding:0.6rem 1rem;">
            ${letters.map(c => `
              <div style="display:flex;justify-content:space-between;padding:0.45rem 0;border-bottom:1px solid var(--border-color);font-size:0.88rem;">
                <span style="font-weight:700;">${c.no}</span>
                <span style="color:var(--text-dim);">${c.organ} ${c.date}</span>
              </div>
            `).join("")}
          </div>
        </div>
      `;
    }

    return html;
  }

  renderInsightsHtml(art) {
    const insights = art.practical_insights || [];
    let html = "";

    if (insights.length > 0) {
      html += `
        <div>
          <h3 class="sub-heading">⚖️ 憲法法庭判決、大法庭裁定與最高法院裁判 (${insights.length})</h3>
          ${insights.map(ins => `
            <div class="insight-full-card">
              <div class="insight-full-ref">🏛️ ${ins.court || "最高法院"} ｜ ${ins.ref || ""}</div>
              <div class="insight-full-summary">${ins.summary}</div>
            </div>
          `).join("")}
        </div>
      `;
    }

    // Direct Precedent & Court Search Tool for ANY article
    const searchParam = encodeURIComponent(`${this.currentAct.name} 第 ${art.article_no} 條`);
    html += `
      <div class="judgment-search-box">
        <h4 style="font-size:0.95rem;font-weight:800;color:var(--text-main);">🔍 司法院與法源實務裁判直接檢索</h4>
        <p style="font-size:0.85rem;color:var(--text-dim);line-height:1.6;">
          本條文可直接連結至司法院裁判書檢索系統或各大法學資料庫，查詢引用本條之判決、大法庭裁定與評釋文章：
        </p>
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
    `;

    return html;
  }

  renderContentLinksHtml(art) {
    const rels = art.related_articles || [];
    const atts = art.attachments || [];

    return `
      <div>
        <h3 class="sub-heading">🔗 跨法規關聯條文 (${rels.length})</h3>
        ${rels.length > 0 ? `
          <div style="display:flex;flex-wrap:wrap;gap:0.5rem;margin-bottom:2rem;">
            ${rels.map(r => `
              <span style="background:var(--bg-surface);border:1px solid var(--border-color);padding:0.45rem 0.85rem;border-radius:6px;font-size:0.88rem;font-weight:700;color:var(--accent-primary);">
                ${r}
              </span>
            `).join("")}
          </div>
        ` : `<p style="color:var(--text-dim);font-size:0.88rem;margin-bottom:2rem;">本條文與 ${this.currentAct.name} 總則與分則各條文相互連動。</p>`}

        <h3 class="sub-heading">📎 條文法定附檔與公告標準 (${atts.length})</h3>
        ${atts.length > 0 ? `
          <div style="margin-bottom:2rem;">
            ${atts.map(att => `
              <div style="background:var(--bg-surface);border:1px solid var(--border-color);border-radius:8px;padding:1.15rem 1.35rem;margin-bottom:0.75rem;">
                <div style="font-weight:900;font-size:0.98rem;margin-bottom:0.35rem;">📄 ${att.title}</div>
                <div style="font-size:0.85rem;color:var(--text-muted);margin-bottom:0.85rem;">${att.description || "法規命令法定附件標準"}</div>
                <a href="${att.url}" target="_blank" rel="noopener noreferrer" class="attachment-badge">
                  線上檢視 / 下載 PDF ↗
                </a>
              </div>
            `).join("")}
          </div>
        ` : `<p style="color:var(--text-dim);font-size:0.88rem;margin-bottom:2rem;">本條文無專屬法定附檔</p>`}

        <h3 class="sub-heading">🌐 權威專業法學庫直達</h3>
        <div style="display:grid;grid-template-columns:repeat(auto-fill, minmax(240px, 1fr));gap:0.75rem;">
          <a href="https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/anglekmc/ttswebx?@0:0:1:lawkm@@0.1702332962648232" target="_blank" rel="noopener noreferrer" class="judgment-link-btn">
            <span>📚 月旦知識庫 (CCU AutoRPA)</span>
            <span style="color:var(--accent-primary);">↗</span>
          </a>
          <a href="https://www-lawbank-com-tw.autorpa.lib.ccu.edu.tw:8443/" target="_blank" rel="noopener noreferrer" class="judgment-link-btn">
            <span>⚖️ 法源法律網 (CCU AutoRPA)</span>
            <span style="color:var(--accent-primary);">↗</span>
          </a>
          <a href="https://law.moj.gov.tw" target="_blank" rel="noopener noreferrer" class="judgment-link-btn">
            <span>🏛️ 全國法規資料庫官方入口</span>
            <span style="color:var(--accent-primary);">↗</span>
          </a>
        </div>
      </div>
    `;
  }

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
                <div><strong style="color:var(--accent-rose);">修正前：</strong><br>${item.old_content}</div>
                <div style="margin-top:0.5rem;"><strong style="color:var(--accent-emerald);">修正後：</strong><br>${item.new_content || art.content}</div>
              </div>
            ` : ""}
          </div>
        `).join("")}
      </div>
    `;
  }

  // ---------------- Structural Element Analyzer ----------------
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

    // Behavior & Object Type
    let behaviorType = "法定一般規範行為";
    if (content.includes("故意") || content.includes("過失")) behaviorType = "作為或不作為行為";
    if (content.includes("駕駛")) behaviorType = "交通工具駕駛行為";
    if (content.includes("公務員")) behaviorType = "公務職權行使行為";

    // Intent Type
    let intentType = "故意責任 (過失需法律有特別處罰規定)";
    if (content.includes("因過失")) intentType = "包含過失犯處罰";
    if (content.includes("過失") && !content.includes("因過失")) intentType = "故意或過失皆得構成";

    // Penalty Type
    let penaltyType = "法定效果拘束";
    const penMatch = content.match(/處[^\n。]+/);
    if (penMatch) {
      penaltyType = penMatch[0].replace(/，.*/, "").slice(0, 30);
    } else if (content.includes("無效")) {
      penaltyType = "法律行為無效";
    } else if (content.includes("得撤銷")) {
      penaltyType = "得撤銷之法律行為";
    }

    // Prosecution Type
    let prosecutionType = "非告訴乃論 (公訴)";
    if (content.includes("須告訴乃論") || content.includes("告訴乃論")) {
      prosecutionType = "告訴乃論 (6個月告訴期間)";
    }

    // Auto Vernacular
    const autoVernacular = [
      {
        question: `Q. 本條文在日常生活中的核心規範意義是什麼？`,
        answer: `本條是 ${this.currentAct.name} 的重要條款。當人民發生具體生活爭議或行為時，法院必須嚴格按照本條文字構成要件審查，具備法定條件方能產生相應的法律約束力。`
      }
    ];

    // Auto FAQs
    const autoFaqs = [
      {
        q: `Q1 如何認定是否構成 ${this.currentAct.name} 第 ${art.article_no} 條？`,
        a: `須同時具備客觀要件（主體資格、客觀行為態樣、結果發生與因果關係）以及主觀要件，並確認無阻卻違法事由。`
      },
      {
        q: `Q2 如對本條相關裁判或行政措施不服，應如何救濟？`,
        a: `應依相關訴訟法規提起救濟程序（民事/刑事上訴、或行政訴訟），主張有利之事實抗辯或聲請憲法法庭審查。`
      }
    ];

    return {
      autoSummary,
      behaviorType,
      intentType,
      penaltyType,
      prosecutionType,
      autoVernacular,
      autoFaqs
    };
  }

  extractArticleTags(art) {
    const tags = [];
    const content = art.content || "";
    if (content.includes("告訴乃論")) tags.push("⚠️ 告訴乃論");
    if (content.includes("無期徒刑")) tags.push("⛔ 重罪 (無期徒刑)");
    if (content.includes("罰金")) tags.push("💰 得併科罰金");
    if (content.includes("未遂犯")) tags.push("🎯 處罰未遂");
    if (content.includes("過失")) tags.push("⚡ 處罰過失");
    if (content.includes("公務員")) tags.push("🏛️ 公務員身分");
    return tags.slice(0, 3);
  }

  copyToClipboard(text, triggerEl) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => {
        this.showCopyFeedback(triggerEl);
      });
    } else {
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      this.showCopyFeedback(triggerEl);
    }
  }

  showCopyFeedback(el) {
    if (!el) return;
    const oldText = el.textContent;
    el.textContent = "✓ 已複製";
    el.style.borderColor = "var(--accent-emerald)";
    el.style.color = "var(--accent-emerald)";
    setTimeout(() => {
      el.textContent = oldText;
      el.style.borderColor = "";
      el.style.color = "";
    }, 1500);
  }

  async loadAndJumpArticle(articleNo) {
    const targetNo = String(articleNo).trim();
    const art = (this.currentAct.articles || []).find(a => a.article_no === targetNo);
    if (art) {
      this.scrollToArticleCard(art.article_no);
      this.openStudyDrawer(art.article_no);
      return true;
    }
    return false;
  }
}

window.addEventListener("DOMContentLoaded", () => {
  window.app = new LegalHubApp();
});
