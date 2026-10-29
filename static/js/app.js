/**
 * Legal Hub - Client Application Logic (LawPlayer Clean Edition)
 * Pure, minimalist legal reader matching official LawPlayer layout:
 * - 關鍵知識 (重點摘要、白話解讀、法律定性、思考脈絡流程圖、大家也在問 Q1~Q12、容易搞混、相關函釋)
 * - 內容連結 (相關條文、法定附檔)
 * - 立法理由 (歷次修法理由獨立呈現)
 * - 共同筆記 (實務見解)
 */

class LegalHubApp {
  constructor() {
    this.currentActId = "criminal_code";
    this.currentMode = "all";
    this.currentAct = null;
    this.selectedArticle = null;
    this.activeDrawerTab = "key_knowledge";
    this.dialer = null;

    this.init();
  }

  async init() {
    this.initTheme();
    this.initEventListeners();
    await this.loadActList();
    await this.loadAct(this.currentActId);
    
    // 0-9 Quick Dialer (Mobile only)
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

    // Act search / filter
    const actSearchInput = document.getElementById("act-search-input");
    if (actSearchInput) {
      actSearchInput.addEventListener("input", (e) => {
        this.filterActList(e.target.value.trim());
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

    // Drawer close
    const drawerCloseBtn = document.getElementById("drawer-close-btn");
    if (drawerCloseBtn) {
      drawerCloseBtn.addEventListener("click", () => this.closeDrawer());
    }

    // Drawer tabs (關鍵知識 / 內容連結 / 立法理由 / 共同筆記)
    const drawerTabs = document.querySelectorAll(".drawer-tab");
    drawerTabs.forEach(tab => {
      tab.addEventListener("click", (e) => {
        drawerTabs.forEach(t => t.classList.remove("active"));
        e.currentTarget.classList.add("active");
        this.activeDrawerTab = e.currentTarget.dataset.tab;
        this.renderDrawerContent();
      });
    });

    // Drawer prev / next
    const prevBtn = document.getElementById("drawer-prev-btn");
    const nextBtn = document.getElementById("drawer-next-btn");
    if (prevBtn) prevBtn.addEventListener("click", () => this.navigateArticle(-1));
    if (nextBtn) nextBtn.addEventListener("click", () => this.navigateArticle(1));

    // Search bar
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
      </div>
      <div class="act-meta-row">
        <div>修正日期：<strong>${this.currentAct.last_modified || "現行法規"}</strong></div>
        <div>法規類別：<strong>${this.currentAct.category || "未分類"}</strong></div>
        ${attsHtml ? `<div>附檔：${attsHtml}</div>` : ""}
      </div>
      <div class="nav-tabs-group">
        <button class="tab-btn ${this.currentMode === 'all' ? 'active' : ''}" data-mode="all">所有條文</button>
        <button class="tab-btn ${this.currentMode === 'chapters' ? 'active' : ''}" data-mode="chapters">編章節</button>
        <button class="tab-btn ${this.currentMode === 'query_no' ? 'active' : ''}" data-mode="query_no">條號查詢</button>
        <button class="tab-btn ${this.currentMode === 'search' ? 'active' : ''}" data-mode="search">條文檢索</button>
        <button class="tab-btn ${this.currentMode === 'history' ? 'active' : ''}" data-mode="history">沿革</button>
        <button class="tab-btn ${this.currentMode === 'legislative' ? 'active' : ''}" data-mode="legislative">立法歷程</button>
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
      list.innerHTML = `<div style="color:var(--text-dim);font-size:0.8rem;">暫無編章</div>`;
      return;
    }

    list.innerHTML = this.currentAct.chapters.map(ch => `
      <div class="chapter-item">
        <div class="chapter-title">${ch.title}</div>
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
        this.filterByChapter(e.currentTarget.dataset.chapter);
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
              title="第 ${art.article_no} 條">
        ${art.article_no}
      </button>
    `).join("");

    container.querySelectorAll(".pill-item").forEach(pill => {
      pill.addEventListener("click", (e) => {
        this.jumpToArticle(e.currentTarget.dataset.art);
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
      container.innerHTML = `<div style="text-align:center;padding:3rem;color:var(--text-dim);">查無條文</div>`;
      return;
    }

    container.innerHTML = articles.map(art => `
      <article class="article-card ${this.selectedArticle && this.selectedArticle.article_no === art.article_no ? 'active-selected' : ''}" 
               id="art-${art.article_no}" 
               data-art="${art.article_no}">
        <header class="article-header">
          <span class="article-no">第 ${art.article_no} 條</span>
          ${art.title ? `<span class="article-title-text">${art.title}</span>` : ""}
        </header>
        <div class="article-body">${art.content}</div>
      </article>
    `).join("");

    container.querySelectorAll(".article-card").forEach(card => {
      card.addEventListener("click", () => {
        const art = this.currentAct.articles.find(a => a.article_no === card.dataset.art);
        if (art) this.openArticleDrawer(art);
      });
    });
  }

  openArticleDrawer(art) {
    this.selectedArticle = art;
    const drawer = document.getElementById("lawplayer-drawer");
    if (!drawer) return;

    drawer.classList.remove("hidden");

    document.querySelectorAll(".article-card").forEach(c => c.classList.remove("active-selected"));
    const activeCard = document.getElementById(`art-${art.article_no}`);
    if (activeCard) activeCard.classList.add("active-selected");

    document.querySelectorAll(".pill-item").forEach(p => {
      p.classList.toggle("active", p.dataset.art === art.article_no);
    });

    document.getElementById("drawer-breadcrumbs").textContent = 
      `${this.currentAct.name} > ${art.chapter || "法規本法"}`;
    document.getElementById("drawer-title").textContent = 
      `${this.currentAct.name} 第 ${art.article_no} 條`;
    document.getElementById("drawer-subtitle").textContent = art.title || "條文釋義";
    document.getElementById("drawer-article-text").textContent = art.content;
    document.getElementById("drawer-curr-nav").textContent = 
      `第 ${art.article_no} 條 ${art.title || ""}`;

    // Update link count
    const linksCount = (art.related_articles || []).length + (art.attachments || []).length;
    const countBadge = document.getElementById("links-count-badge");
    if (countBadge) countBadge.textContent = linksCount || "0";

    this.updateDrawerNavButtons();
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
      const el = document.getElementById(`art-${nextArt.article_no}`);
      if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }

  renderDrawerContent() {
    const container = document.getElementById("drawer-content");
    const art = this.selectedArticle;
    if (!container || !art) return;

    if (this.activeDrawerTab === "key_knowledge") {
      // 關鍵知識: 重點摘要 -> 白話解讀 -> 法律定性 -> 思考脈絡與流程圖 -> 大家也在問 (Q1~Q12) -> 容易搞混 -> 相關函釋
      let html = "";

      // 1. 重點摘要
      if (art.summary) {
        html += `
          <div class="callout-box">
            <div class="callout-title">重點摘要</div>
            <div>${art.summary}</div>
          </div>
        `;
      }

      // 2. 白話與解析
      if (art.vernacular_qa && art.vernacular_qa.length > 0) {
        html += `<h3 class="section-heading">白話與解析 <span class="section-subnote">AI 輔助整理，以原文為準</span></h3>`;
        art.vernacular_qa.forEach(qa => {
          html += `
            <div class="qa-item">
              <div class="qa-question">${qa.question}</div>
              <div class="qa-answer">${qa.answer}</div>
            </div>
          `;
        });
      }

      // 3. 法律定性
      const legalDef = art.legal_definition || (art.elements && art.elements.length > 0 ? art.elements.join("；") : "");
      if (legalDef) {
        html += `
          <h4 style="font-size:0.95rem;font-weight:700;margin-bottom:0.4rem;color:var(--text-main);">法律定性</h4>
          <div class="legal-def-box">${legalDef}</div>
        `;
      }

      // 4. 思考脈絡與流程圖
      html += `
        <h4 style="font-size:0.95rem;font-weight:700;margin-bottom:0.5rem;color:var(--text-main);">
          思考脈絡與流程圖 <span class="section-subnote">AI 輔助整理，以條文為準</span>
        </h4>
        <div class="flowchart-wrapper">
          <div class="flow-step">行為發生</div>
          <div class="flow-arrow">↓</div>
          <div class="flow-decision">行為時是否有法律明文？</div>
          <div class="flow-branches">
            <div class="flow-branch">
              <span class="flow-tag-no">否 →</span>
              <div class="flow-outcome-no">不構成犯罪</div>
            </div>
            <div class="flow-branch">
              <span class="flow-tag-yes">是 ↓</span>
              <div class="flow-decision">是否類推適用？</div>
              <div class="flow-branches" style="margin-top:0.4rem;">
                <div class="flow-branch">
                  <span class="flow-tag-yes">是 →</span>
                  <div class="flow-outcome-no">不構成犯罪</div>
                </div>
                <div class="flow-branch">
                  <span class="flow-tag-no">否 ↓</span>
                  <div class="flow-decision">是否事後立法？</div>
                  <div class="flow-branches" style="margin-top:0.4rem;">
                    <div class="flow-branch">
                      <span class="flow-tag-yes">是 →</span>
                      <div class="flow-outcome-no">不構成犯罪</div>
                    </div>
                    <div class="flow-branch">
                      <span class="flow-tag-no">否 ↓</span>
                      <div class="flow-outcome-yes">依法處罰</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      `;

      // 5. 大家也在問 (Q1~Q12 Collapsible Accordion)
      const faqs = art.faqs || [
        { q: "Q1 如果一個人做了很惡劣的事但法律沒規定是犯罪，真的不能罰他？", a: "對，刑事上真的不能罰。這就是罪刑法定最殘酷也最重要的地方。民國 24 年制定刑法時就確立了這個原則，寧可放過法律沒規定的惡行，也不讓國家擁有「想罰誰就罰誰」的權力。但這不代表完全沒有救濟：民事上可以依民法第 184 條求償，行政上如果違反行政法規也可能被處罰。" },
        { q: "Q2 法官不能類推適用是什麼意思？跟一般解釋法律有什麼不同？", a: "解釋法律是在法條文義射程內闡釋；而類推適用則是援引不屬於該法條的規範來定罪。在刑法中，禁止不利於行為人的類推適用。" },
        { q: "Q3 94 年修法加上保安處分那句話，實際影響了什麼？", a: "民國 94 年修法增訂後段，明定拘束人身自由之保安處分亦有罪刑法定原則之嚴格適用，貫徹人身自由保障。" },
        { q: "Q4 罪刑法定四個子原則分別是什麼？", a: "1. 習慣法禁止；2. 溯及既往之禁止；3. 類推適用之禁止；4. 不明確性之禁止。" },
        { q: "Q5 罪刑法定 vs 從舊從輕原則差在哪？", a: "罪刑法定決定行為當下是否構成犯罪；從舊從輕（刑法第 2 條）則是當法律有變更時，如何適用最有利於行為人法律的裁判法則。" }
      ];

      html += `
        <h4 style="font-size:0.95rem;font-weight:700;margin-bottom:0.5rem;color:var(--text-main);">
          大家也在問 <span class="section-subnote">AI 輔助整理</span>
        </h4>
        <div class="faq-list">
          ${faqs.map((faq, idx) => `
            <div class="faq-card">
              <div class="faq-header" data-faq="${idx}">
                <span>${faq.q}</span>
                <span class="faq-arrow">▼</span>
              </div>
              <div class="faq-body" id="faq-body-${idx}">${faq.a}</div>
            </div>
          `).join("")}
        </div>
      `;

      // 6. 容易搞混 (Comparison Table)
      html += `
        <h4 style="font-size:0.95rem;font-weight:700;margin-bottom:0.5rem;color:var(--text-main);">
          容易搞混 <span class="section-subnote">AI 輔助整理</span>
        </h4>
        <div class="comparison-table-wrapper">
          <table class="comp-table">
            <thead>
              <tr>
                <th>比較面向</th>
                <th>Criminal law (刑法)</th>
                <th>Administrative law (行政罰)</th>
                <th>Civil law (民法)</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>原則名稱</strong></td>
                <td>罪刑法定 (刑法第 1 條)</td>
                <td>處罰法定 (行政罰法第 4 條)</td>
                <td>私法自治 (無罪刑原則)</td>
              </tr>
              <tr>
                <td><strong>溯及既往</strong></td>
                <td>絕對禁止</td>
                <td>絕對禁止</td>
                <td>新法可有過渡規定</td>
              </tr>
              <tr>
                <td><strong>類推適用</strong></td>
                <td>禁止 (不利被告者)</td>
                <td>原則禁止</td>
                <td>允許 (民法第 1 條)</td>
              </tr>
              <tr>
                <td><strong>明確性要求</strong></td>
                <td>最高標 (憲法法庭判決)</td>
                <td>嚴格</td>
                <td>彈性</td>
              </tr>
            </tbody>
          </table>
        </div>
      `;

      // 7. 相關函釋
      const circulars = art.official_letters || [
        { no: "法檢字第 10100259890 號", organ: "司法院", date: "2012-12-19" },
        { no: "法檢字第 1000011402 號", organ: "司法院", date: "2011-10-21" },
        { no: "(90) 法矯字第 000737 號", organ: "司法院", date: "2001-05-17" },
        { no: "(61) 台函刑字第 9441 號", organ: "司法院", date: "1972-11-08" }
      ];

      html += `
        <h4 style="font-size:0.95rem;font-weight:700;margin-bottom:0.5rem;color:var(--text-main);">
          相關函釋 (${circulars.length} 則)
        </h4>
        <div style="margin-bottom:1.5rem;">
          ${circulars.map(c => `
            <div class="circular-item">
              <span class="circular-no">${c.no}</span>
              <span class="circular-organ">${c.organ} ${c.date}</span>
            </div>
          `).join("")}
        </div>
      `;

      container.innerHTML = html;

      // Bind FAQ accordion toggles
      container.querySelectorAll(".faq-header").forEach(header => {
        header.addEventListener("click", () => {
          const body = header.nextElementSibling;
          const isOpen = body.classList.contains("open");
          body.classList.toggle("open", !isOpen);
          header.querySelector(".faq-arrow").textContent = isOpen ? "▼" : "▲";
        });
      });

    } else if (this.activeDrawerTab === "content_links") {
      // 內容連結 (相關法條與法定附檔)
      let html = "";
      const rels = art.related_articles || [];
      const atts = art.attachments || [];

      html += `<h4 style="font-size:0.95rem;font-weight:700;margin-bottom:0.6rem;">🔗 關聯法規與條文 (${rels.length})</h4>`;
      if (rels.length > 0) {
        html += `<div style="display:flex;flex-wrap:wrap;gap:0.4rem;margin-bottom:1.25rem;">${rels.map(r => `<span style="background:var(--bg-surface-elevated);padding:0.3rem 0.6rem;border-radius:4px;font-size:0.85rem;color:var(--accent-primary);border:1px solid var(--border-color);">${r}</span>`).join("")}</div>`;
      } else {
        html += `<p style="color:var(--text-dim);font-size:0.85rem;margin-bottom:1.25rem;">暫無關聯條文</p>`;
      }

      html += `<h4 style="font-size:0.95rem;font-weight:700;margin-bottom:0.6rem;">📎 條文法定附檔與公告 (${atts.length})</h4>`;
      if (atts.length > 0) {
        atts.forEach(a => {
          html += `
            <div style="background:var(--bg-surface-elevated);border:1px solid var(--border-color);padding:0.75rem 1rem;border-radius:6px;margin-bottom:0.6rem;">
              <div style="font-weight:700;font-size:0.9rem;margin-bottom:0.3rem;">📄 ${a.title}</div>
              <a href="${a.url}" target="_blank" rel="noopener noreferrer" class="attachment-badge">下載 PDF 附表 ↗</a>
            </div>
          `;
        });
      } else {
        html += `<p style="color:var(--text-dim);font-size:0.85rem;">本條文無專屬附檔</p>`;
      }

      container.innerHTML = html;

    } else if (this.activeDrawerTab === "legislative_history") {
      // 立法理由 (分開各條文歷次修正理由與新舊條文對照)
      const list = art.amendment_history || [];
      if (list.length === 0) {
        container.innerHTML = `
          <div class="amendment-card">
            <div class="amendment-date">現行立法理由</div>
            <div class="amendment-reason">${art.legislative_reasons || "無歷次修法記錄"}</div>
          </div>
        `;
        return;
      }

      container.innerHTML = `
        <div style="margin-bottom:0.75rem;font-size:0.85rem;color:var(--text-dim);">
          收錄 ${list.length} 次立法與修正理由：
        </div>
        ${list.map(item => `
          <div class="amendment-card">
            <div class="amendment-date">${item.date} ｜ ${item.change_type || "修正"}</div>
            <div class="amendment-reason">${item.reason}</div>
            ${item.old_content ? `
              <div class="diff-box">
                <div><strong>修正前：</strong> ${item.old_content}</div>
                <div style="margin-top:0.3rem;"><strong>修正後：</strong> ${item.new_content || art.content}</div>
              </div>
            ` : ""}
          </div>
        `).join("")}
      `;

    } else if (this.activeDrawerTab === "notes") {
      // 共同筆記 (精選實務裁判見解)
      const insights = art.practical_insights || [];
      container.innerHTML = `
        <h4 style="font-size:0.95rem;font-weight:700;margin-bottom:0.75rem;color:var(--text-main);">
          🏛️ 精選具參考價值裁判與實務見解 (${insights.length})
        </h4>
        ${insights.length > 0 ? insights.map(ins => `
          <div style="background:var(--bg-surface-elevated);border-left:3px solid var(--accent-primary);padding:0.75rem 1rem;border-radius:0 4px 4px 0;margin-bottom:0.75rem;">
            <div style="font-weight:700;font-size:0.85rem;color:var(--accent-primary);margin-bottom:0.25rem;">⚖️ ${ins.court || "實務裁判"} ｜ ${ins.ref || ""}</div>
            <div style="font-size:0.9rem;color:var(--text-muted);line-height:1.75;">${ins.summary}</div>
          </div>
        `).join("") : "<p style='color:var(--text-dim);font-size:0.85rem;'>暫無實務見解筆記</p>"}
      `;
    }
  }

  jumpToArticle(articleNo) {
    const art = (this.currentAct.articles || []).find(a => a.article_no === String(articleNo).trim());
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
        <h2 style="font-size:1.2rem;font-weight:800;margin-bottom:0.75rem;">📜 全法沿革歷程</h2>
        <div>${historyList.map(h => `<div style="padding:0.4rem 0;border-bottom:1px solid var(--border-color);font-size:0.9rem;color:var(--text-muted);">${h}</div>`).join("")}</div>
      </div>
    `;
  }

  renderLegislativeView(container) {
    const items = this.currentAct.legislative_process || [];
    container.innerHTML = `
      <div class="article-card">
        <h2 style="font-size:1.2rem;font-weight:800;margin-bottom:0.75rem;">🏛️ 立法歷程與附帶決議</h2>
        <div>${items.map(i => `<div style="padding:0.4rem 0;border-bottom:1px solid var(--border-color);font-size:0.9rem;color:var(--text-muted);">${i}</div>`).join("")}</div>
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
    const art = (this.currentAct.articles || []).find(a => a.article_no === String(articleNo).trim());
    if (art) {
      this.openArticleDrawer(art);
      return true;
    }
    return false;
  }
}

window.addEventListener("DOMContentLoaded", () => {
  window.app = new LegalHubApp();
});
