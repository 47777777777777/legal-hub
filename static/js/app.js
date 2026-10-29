/**
 * Legal Hub - Ergonomic Legal Explorer & Slide-over Deep Study Drawer
 * 
 * Features:
 * 1. Single natural vertical scroll (NO nested scrollbars, NO cut-offs)
 * 2. Continuous statute stream reading with instant "條文研析" drawer
 * 3. 4 Essential tabs: 關鍵知識 | 實務判解 | 內容連結 | 立法理由
 * 4. Rich, authentic data for key articles + tailored analysis for all articles
 * 5. Full keyboard support (Esc to close, Prev/Next) & Mobile numeric dialer
 */

class LegalHubApp {
  constructor() {
    this.currentActId = "criminal_code";
    this.currentAct = null;
    this.selectedArticleNo = null;
    this.activeTab = "key_knowledge";
    this.dialer = null;

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

    // Global keyboard shortcuts (Esc to close drawer)
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        this.closeStudyDrawer();
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
        
        // Find matching first article and scroll smoothly
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
      statsEl.textContent = `共 ${articles.length} 條條文`;
    }

    if (articles.length === 0) {
      container.innerHTML = `<div style="text-align:center;padding:4rem;color:var(--text-dim);">查無符合之條文</div>`;
      return;
    }

    container.innerHTML = articles.map(art => {
      const insightCount = (art.practical_insights || []).length;
      const amendCount = (art.amendment_history || []).length;
      const attCount = (art.attachments || []).length;

      return `
        <article class="stream-article-card ${art.article_no === this.selectedArticleNo ? 'active' : ''}" id="article-card-${art.article_no}" data-art="${art.article_no}">
          <div class="stream-card-header">
            <div class="stream-card-title-group">
              <span class="stream-card-no">第 ${art.article_no} 條</span>
              ${art.title ? `<span class="stream-card-title">${art.title}</span>` : ""}
            </div>
            <button class="stream-study-btn" data-art="${art.article_no}" title="開啟條文深度研析">
              💡 條文研析
            </button>
          </div>
          <div class="stream-card-body">${art.content}</div>
          <div class="stream-card-tags">
            ${art.chapter ? `<span class="stream-tag">📂 ${art.chapter}</span>` : ""}
            ${insightCount > 0 ? `<span class="stream-tag" style="color:var(--accent-primary);">🏛️ 實務判解 ${insightCount} 則</span>` : ""}
            ${amendCount > 0 ? `<span class="stream-tag" style="color:var(--accent-emerald);">📜 歷次修法 ${amendCount} 次</span>` : ""}
            ${attCount > 0 ? `<span class="stream-tag" style="color:var(--accent-amber);">📎 法定附檔 ${attCount} 件</span>` : ""}
          </div>
        </article>
      `;
    }).join("");

    // Bind card click & button click
    container.querySelectorAll(".stream-study-btn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        this.openStudyDrawer(btn.dataset.art);
      });
    });

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

    // Highlight card in stream
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
          <div class="drawer-hero-article-box">${art.content}</div>
        </section>

        <!-- Ergonomic Sticky Tabs Bar -->
        <nav class="drawer-tabs-bar">
          <button class="drawer-tab-btn ${this.activeTab === 'key_knowledge' ? 'active' : ''}" data-tab="key_knowledge">
            💡 關鍵知識
          </button>
          <button class="drawer-tab-btn ${this.activeTab === 'insights' ? 'active' : ''}" data-tab="insights">
            🏛️ 實務判解 (${(art.practical_insights || []).length})
          </button>
          <button class="drawer-tab-btn ${this.activeTab === 'content_links' ? 'active' : ''}" data-tab="content_links">
            🔗 內容連結 (${(art.related_articles || []).length + (art.attachments || []).length})
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
          <span style="font-size:0.85rem;font-weight:700;color:var(--text-dim);">
            第 ${art.article_no} 條 ${art.title || ''}
          </span>
          <button class="drawer-nav-btn" id="drawer-next-btn">
            下一條 →
          </button>
        </footer>
      `;

      // Reset scroll smoothly to top
      scrollBody.scrollTop = 0;

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
        if (idx > 0) this.openStudyDrawer(articles[idx - 1].article_no);
      });
    }

    if (nextBtn) {
      nextBtn.disabled = idx < 0 || idx >= articles.length - 1;
      nextBtn.addEventListener("click", () => {
        if (idx < articles.length - 1) this.openStudyDrawer(articles[idx + 1].article_no);
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

  renderKeyKnowledgeHtml(art) {
    let html = "";

    // 1. 重點摘要 (Distinct per article)
    const summaryText = art.summary || `本條為 ${this.currentAct.name} 之明文規定，規範核心法律構成要件與法律效果。`;
    html += `
      <div class="callout-box">
        <div class="callout-title">💡 重點摘要</div>
        <div>${summaryText}</div>
      </div>
    `;

    // 2. 白話與解析 (Vernacular Q&A)
    const qas = art.vernacular_qa || [];
    if (qas.length > 0) {
      html += `
        <div>
          <h3 class="sub-heading">📖 白話與解析 <span class="sub-note">以法理為本，深入淺出</span></h3>
          ${qas.map(item => `
            <div class="qa-card">
              <div class="qa-card-question">${item.question}</div>
              <div class="qa-card-answer">${item.answer}</div>
            </div>
          `).join("")}
        </div>
      `;
    }

    // 3. 法律定性
    const legalDef = art.legal_definition || `本條為 ${this.currentAct.name} 於 ${art.chapter || "本法"} 所定之規範，具拘束力與法定救濟效力。`;
    html += `
      <div>
        <h3 class="sub-heading">⚖️ 法律定性</h3>
        <div class="legal-qual-card">${legalDef}</div>
      </div>
    `;

    // 4. 思考脈絡與流程圖
    html += `
      <div>
        <h3 class="sub-heading">🔍 思考脈絡與邏輯判斷流程</h3>
        <div class="flowchart-container">
          <div class="flow-step-box">生活事實行為發生</div>
          <div class="flow-indicator">↓</div>
          <div class="flow-decision-box">行為時是否符合本條構成要件？</div>
          <div class="flow-branch-row">
            <div class="flow-sub-branch">
              <span style="color:var(--accent-rose);font-size:0.8rem;font-weight:700;">否 →</span>
              <div class="flow-outcome-no-crime">不成立本條效果</div>
            </div>
            <div class="flow-sub-branch">
              <span style="color:var(--accent-emerald);font-size:0.8rem;font-weight:700;">是 ↓</span>
              <div class="flow-decision-box">是否有阻卻違法或免責事由？</div>
              <div class="flow-branch-row" style="margin-top:0.4rem;">
                <div class="flow-sub-branch">
                  <span style="color:var(--accent-rose);font-size:0.8rem;font-weight:700;">有 →</span>
                  <div class="flow-outcome-no-crime">免除處罰或責任</div>
                </div>
                <div class="flow-sub-branch">
                  <span style="color:var(--accent-emerald);font-size:0.8rem;font-weight:700;">無 ↓</span>
                  <div class="flow-outcome-penalty">依法承擔法律效果</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    // 5. 大家也在問 (FAQs Q1~Q8)
    const faqs = (art.faqs && art.faqs.length > 0) ? art.faqs : [
      {
        q: `Q1 如何判斷是否該當 ${this.currentAct.name} 第 ${art.article_no} 條？`,
        a: `須嚴格檢驗客觀構成要件（主體、客體、行為態樣與結果發生）與主觀構成要件（故意或過失責任），缺一不可。`
      },
      {
        q: `Q2 違反本條文之救濟途徑為何？`,
        a: `當事人如受不利裁判或處分，得依訴訟法規提起救濟，主張阻卻違法、情狀顯可憫恕或依法請求損害賠償。`
      }
    ];

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
          <div style="background:var(--bg-surface);border:1px solid var(--border-color);border-radius:6px;padding:0.5rem 1rem;">
            ${letters.map(c => `
              <div style="display:flex;justify-content:space-between;padding:0.4rem 0;border-bottom:1px solid var(--border-color);font-size:0.85rem;">
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
    if (insights.length === 0) {
      return `
        <div style="text-align:center;padding:3rem 1rem;color:var(--text-dim);background:var(--bg-surface);border:1px solid var(--border-color);border-radius:8px;">
          <div style="font-size:1.5rem;margin-bottom:0.5rem;">⚖️</div>
          <div style="font-weight:700;margin-bottom:0.4rem;">本條文刻正彙整精選實務判解</div>
          <div style="font-size:0.85rem;color:var(--text-dim);">可至法源法律網或司法院法學檢索系統查詢最新裁判要旨。</div>
        </div>
      `;
    }

    return `
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

  renderContentLinksHtml(art) {
    const rels = art.related_articles || [];
    const atts = art.attachments || [];

    return `
      <div>
        <h3 class="sub-heading">🔗 跨法規關聯條文 (${rels.length})</h3>
        ${rels.length > 0 ? `
          <div style="display:flex;flex-wrap:wrap;gap:0.5rem;margin-bottom:2rem;">
            ${rels.map(r => `
              <span style="background:var(--bg-surface);border:1px solid var(--border-color);padding:0.4rem 0.8rem;border-radius:6px;font-size:0.88rem;font-weight:600;color:var(--accent-primary);">
                ${r}
              </span>
            `).join("")}
          </div>
        ` : `<p style="color:var(--text-dim);font-size:0.88rem;margin-bottom:2rem;">本條文無登記之跨法規關聯條文</p>`}

        <h3 class="sub-heading">📎 條文法定附檔與公告標準 (${atts.length})</h3>
        ${atts.length > 0 ? `
          <div style="margin-bottom:2rem;">
            ${atts.map(att => `
              <div style="background:var(--bg-surface);border:1px solid var(--border-color);border-radius:8px;padding:1rem 1.25rem;margin-bottom:0.75rem;">
                <div style="font-weight:800;font-size:0.95rem;margin-bottom:0.35rem;">📄 ${att.title}</div>
                <div style="font-size:0.85rem;color:var(--text-muted);margin-bottom:0.75rem;">${att.description || "法規命令法定附件標準"}</div>
                <a href="${att.url}" target="_blank" rel="noopener noreferrer" class="attachment-badge">
                  線上檢視 / 下載 PDF ↗
                </a>
              </div>
            `).join("")}
          </div>
        ` : `<p style="color:var(--text-dim);font-size:0.88rem;margin-bottom:2rem;">本條文無專屬法定附檔</p>`}

        <h3 class="sub-heading">🌐 權威專業資料庫快捷直達</h3>
        <div style="display:grid;grid-template-columns:repeat(auto-fill, minmax(240px, 1fr));gap:0.75rem;">
          <a href="https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/anglekmc/ttswebx?@0:0:1:lawkm@@0.1702332962648232" target="_blank" rel="noopener noreferrer" style="background:var(--bg-surface);border:1px solid var(--border-color);padding:0.75rem 1rem;border-radius:6px;text-decoration:none;color:var(--text-main);font-size:0.88rem;display:flex;align-items:center;justify-content:space-between;">
            <span>📚 月旦知識庫 (CCU AutoRPA)</span>
            <span style="color:var(--accent-primary);">↗</span>
          </a>
          <a href="https://www-lawbank-com-tw.autorpa.lib.ccu.edu.tw:8443/" target="_blank" rel="noopener noreferrer" style="background:var(--bg-surface);border:1px solid var(--border-color);padding:0.75rem 1rem;border-radius:6px;text-decoration:none;color:var(--text-main);font-size:0.88rem;display:flex;align-items:center;justify-content:space-between;">
            <span>⚖️ 法源法律網 (CCU AutoRPA)</span>
            <span style="color:var(--accent-primary);">↗</span>
          </a>
          <a href="https://law.moj.gov.tw" target="_blank" rel="noopener noreferrer" style="background:var(--bg-surface);border:1px solid var(--border-color);padding:0.75rem 1rem;border-radius:6px;text-decoration:none;color:var(--text-main);font-size:0.88rem;display:flex;align-items:center;justify-content:space-between;">
            <span>🏛️ 全國法規資料庫</span>
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
          <div class="amend-timeline-date">現行制定理由</div>
          <div class="amend-timeline-reason">${art.legislative_reasons || "現行生效法規條文。"}</div>
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
