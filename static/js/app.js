/**
 * Legal Hub - Professional Legal Intelligence System
 * High-Density, Split-View, Hover Citations, Scrubber, Gestures & Keyboard Navigation
 */

const ESC_MAP = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ESC_MAP[c]);
}

function toRoman(n) {
  const map = [[1000, "M"], [900, "CM"], [500, "D"], [400, "CD"], [100, "C"], [90, "XC"], [50, "L"], [40, "XL"], [10, "X"], [9, "IX"], [5, "V"], [4, "IV"], [1, "I"]];
  let out = "";
  for (const [v, s] of map) {
    while (n >= v) { out += s; n -= v; }
  }
  return out;
}

const CHN_NUM_MAP = { "零": 0, "〇": 0, "一": 1, "二": 2, "兩": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9 };
function parseChnNumber(str) {
  if (!str) return 0;
  str = str.replace(/[條項款目之\s]/g, "");
  let val = 0, temp = 0;
  for (let i = 0; i < str.length; i++) {
    const ch = str[i];
    if (CHN_NUM_MAP[ch] !== undefined) {
      temp = CHN_NUM_MAP[ch];
    } else if (ch === '十') {
      val += (temp === 0 ? 1 : temp) * 10;
      temp = 0;
    } else if (ch === '百') {
      val += (temp === 0 ? 1 : temp) * 100;
      temp = 0;
    } else if (ch === '千') {
      val += (temp === 0 ? 1 : temp) * 1000;
      temp = 0;
    } else if (ch >= '0' && ch <= '9') {
      val = parseInt(str, 10);
      break;
    }
  }
  return val + temp;
}

const RE_KUAN = /^([一二三四五六七八九十百]+、)\s*/;
const RE_MU = /^([（(][一二三四五六七八九十百]+[）)])\s*/;
const RE_SUBMU = /^([0-9０-９]+[.．、])\s*/;

function parseArticleStructure(content) {
  const lines = String(content == null ? "" : content)
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0);
  const paras = [];
  lines.forEach((line) => {
    let m, level = 0;
    if ((m = line.match(RE_KUAN))) level = 1;
    else if ((m = line.match(RE_MU))) level = 2;
    else if ((m = line.match(RE_SUBMU))) level = 3;

    if (level === 0) {
      paras.push({ text: line, subs: [] });
    } else {
      if (!paras.length) paras.push({ text: "", subs: [] });
      paras[paras.length - 1].subs.push({ level, marker: m[1], text: line.slice(m[0].length) });
    }
  });
  return { paras };
}

// Convert citations like "第二百二十一條" or "第 185-3 條" into interactive hover/tap links
function linkifyArticleRefs(text, q) {
  let safe = hl(text, q);
  const refRegex = /(第\s*([0-9０-９]+(?:\s*之\s*[0-9０-９]+|-?[0-9]+)?|[一二三四五六七八九十百千]+(?:\s*之\s*[一二三四五六七八九十百]+)?)\s*條)/g;
  return safe.replace(refRegex, (match, full, rawNo) => {
    const cleanNo = cleanRawNo(rawNo);
    return `<span class="article-ref-link" data-ref-no="${cleanNo}">${full}</span>`;
  });
}

function cleanRawNo(raw) {
  if (/[一二三四五六七八九十百千]/.test(raw)) {
    const parts = raw.split(/之/);
    const main = parseChnNumber(parts[0]);
    if (parts.length > 1) {
      return `${main}-${parseChnNumber(parts[1])}`;
    }
    return String(main);
  }
  return raw.replace(/\s+/g, "").replace(/之/, "-");
}

function hl(text, q) {
  text = String(text == null ? "" : text);
  if (!q) return esc(text);
  const re = new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi");
  let out = "", last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m[0].length === 0) { re.lastIndex++; continue; }
    out += esc(text.slice(last, m.index)) + "<mark>" + esc(m[0]) + "</mark>";
    last = m.index + m[0].length;
  }
  return out + esc(text.slice(last));
}

function renderArticleBody(content, q) {
  const { paras } = parseArticleStructure(content);
  if (!paras.length) return `<div class="article-body"></div>`;
  const multi = paras.filter((p) => p.text).length > 1;
  let n = 0;
  const blocks = paras
    .map((p) => {
      const no = p.text ? ++n : 0;
      const subs = p.subs
        .map(
          (s) =>
            `<div class="sub sub-${s.level}"><span class="sub-marker">${esc(s.marker)}</span><span class="sub-text">${linkifyArticleRefs(s.text, q)}</span></div>`
        )
        .join("");
      return `<div class="para-block ${multi ? "" : "single"}">
        ${multi ? `<span class="para-no" title="${no ? `第 ${no} 項` : ""}">${no ? toRoman(no) : ""}</span>` : ""}
        <div class="para-body">${p.text ? `<div class="para-text">${linkifyArticleRefs(p.text, q)}</div>` : ""}${subs}</div>
      </div>`;
    })
    .join("");
  return `<div class="article-body">${blocks}</div>`;
}

function articleCopyText(content) {
  const { paras } = parseArticleStructure(content);
  const multi = paras.filter((p) => p.text).length > 1;
  let n = 0;
  return paras
    .map((p) => {
      const head = (multi && p.text ? `第 ${++n} 項　` : "") + p.text;
      const subs = p.subs.map((s) => `${"　".repeat(s.level)}${s.marker}${s.text}`);
      return [head.trimEnd(), ...subs].filter((l) => l).join("\n");
    })
    .join("\n");
}

function hydrateIcons(root) {
  (root || document).querySelectorAll("[data-icon]").forEach((el) => {
    if (el.dataset.hydrated) return;
    el.innerHTML = icon(el.dataset.icon, parseInt(el.dataset.size || "16", 10));
    el.dataset.hydrated = "1";
  });
}

function sectionHeading(iconName, title, note) {
  return `<h3 class="sub-heading">${icon(iconName, 16)}<span>${title}</span>${note ? `<span class="sub-note">${note}</span>` : ""}</h3>`;
}

// Global CCU helpers for guaranteed click handling
window.switchCCUTab = function(tabName) {
  const appBtn = document.getElementById("ccu-tab-app-btn");
  const netBtn = document.getElementById("ccu-tab-net-btn");
  const appPanel = document.getElementById("ccu-tab-app-panel");
  const netPanel = document.getElementById("ccu-tab-net-panel");
  if (tabName === "net") {
    if (appBtn) { appBtn.style.background = "transparent"; appBtn.style.color = "#a1a1aa"; }
    if (netBtn) { netBtn.style.background = "#27272a"; netBtn.style.color = "#fafafa"; }
    if (appPanel) appPanel.style.display = "none";
    if (netPanel) netPanel.style.display = "block";
  } else {
    if (appBtn) { appBtn.style.background = "#27272a"; appBtn.style.color = "#fafafa"; }
    if (netBtn) { netBtn.style.background = "transparent"; netBtn.style.color = "#a1a1aa"; }
    if (appPanel) appPanel.style.display = "block";
    if (netPanel) netPanel.style.display = "none";
  }
};

window.currentCCUSource = "all";
window.switchCCUSource = function(source) {
  window.currentCCUSource = source;
  document.querySelectorAll(".ccu-source-btn").forEach(btn => {
    if (btn.dataset.source === source) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });
};

class LegalHubApp {
  constructor() {
    this.currentActId = "criminal_code";
    this.currentAct = null;
    this.selectedArticleNo = null;
    this.activeTab = "key_knowledge";
    this.activeFilter = "all";
    this.dialer = null;
    this.fontSize = 15;
    this.searchQuery = "";
    this.isSplitMode = true; // True desktop split-view
    this.isTocCollapsed = false;
    this.activeChapterIdx = 0;
    this.openTabs = [{ id: "criminal_code", name: "中華民國刑法" }];
    this.bookmarks = this.loadBookmarks();

    this.init();
  }

  async init() {
    hydrateIcons();
    this.initTheme();
    this.initDensity();
    this.initEventListeners();
    this.bindCCUEvents();
    this.refreshCCUStatus();
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

    this.initScrollspy();
    this.initDraggableSplit();
    this.initMobileGestures();
  }

  // ---------------- Theme & Density ----------------
  initTheme() {
    const saved = localStorage.getItem("legal_hub_theme") || "dark";
    document.documentElement.setAttribute("data-theme", saved);
    this.updateThemeButton(saved);
  }

  updateThemeButton(theme) {
    const btn = document.getElementById("theme-toggle-btn");
    if (btn) btn.innerHTML = icon(theme === "dark" ? "sun" : "moon", 16);
  }

  toggleTheme() {
    const cur = document.documentElement.getAttribute("data-theme") || "dark";
    const next = cur === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("legal_hub_theme", next);
    this.updateThemeButton(next);
  }

  initDensity() {
    const saved = localStorage.getItem("legal_hub_density") || "compact";
    document.documentElement.setAttribute("data-density", saved);
  }

  toggleDensity() {
    const cur = document.documentElement.getAttribute("data-density") || "compact";
    const next = cur === "compact" ? "standard" : "compact";
    document.documentElement.setAttribute("data-density", next);
    localStorage.setItem("legal_hub_density", next);
  }

  adjustFontSize(delta) {
    this.fontSize = Math.max(13, Math.min(22, this.fontSize + delta));
    document.documentElement.style.setProperty("--font-size-base", `${this.fontSize}px`);
  }

  // ---------------- Bookmarks ----------------
  loadBookmarks() {
    try { return JSON.parse(localStorage.getItem("legal_hub_bookmarks") || "[]"); } catch (e) { return []; }
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
      let title = "", snippet = "";
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
        timestamp: new Date().toLocaleDateString()
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
    btn.innerHTML = icon(on ? "bookmark-filled" : "bookmark", 16);
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

  // ---------------- Chrome-like Research Tabs ----------------
  renderResearchTabs() {
    const container = document.getElementById("research-tabs-list");
    if (!container) return;

    container.innerHTML = this.openTabs
      .map(
        (tab) => `
      <div class="research-tab-item ${tab.id === this.currentActId ? "active" : ""}" data-act-id="${esc(tab.id)}">
        <span>${esc(tab.name)}</span>
        ${this.openTabs.length > 1 ? `<button class="tab-close-btn" data-close="${esc(tab.id)}" title="關閉分頁">${icon("x", 12)}</button>` : ""}
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

  // ---------------- Event Listeners & Global Shortcuts ----------------
  initEventListeners() {
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
        } catch (err) { console.error(err); }
      });
    }

    const searchInput = document.getElementById("search-input");
    this.bindClearable(searchInput, document.getElementById("search-clear"), (q) => this.filterStreamArticles(q));

    // Density and Theme Toggles
    document.getElementById("density-toggle-btn").addEventListener("click", () => this.toggleDensity());
    document.getElementById("theme-toggle-btn").addEventListener("click", () => this.toggleTheme());
    document.getElementById("font-plus-btn").addEventListener("click", () => this.adjustFontSize(1));
    document.getElementById("font-minus-btn").addEventListener("click", () => this.adjustFontSize(-1));

    // TOC Toggle
    document.getElementById("toc-toggle-btn").addEventListener("click", () => this.toggleToc());

    // Quick Filter Chips
    document.querySelectorAll(".quick-filter-chips .filter-chip").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".quick-filter-chips .filter-chip").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        this.activeFilter = btn.dataset.filter;
        this.filterStreamArticles(this.searchQuery);
      });
    });

    // Mobile Thumb Capsule
    const capSearch = document.getElementById("capsule-search-btn");
    if (capSearch) {
      capSearch.addEventListener("click", () => {
        const inp = document.getElementById("search-input");
        if (inp) { inp.focus(); inp.scrollIntoView({ behavior: "smooth" }); }
      });
    }
    const capDial = document.getElementById("capsule-dial-btn");
    if (capDial) {
      capDial.addEventListener("click", () => {
        if (this.dialer) this.dialer.toggle();
      });
    }

    // Modal
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

    // Flowchart Modal Close
    document.getElementById("flowchart-modal-close").addEventListener("click", () => {
      document.getElementById("flowchart-modal").classList.add("hidden");
    });

    // CCU AutoRPA Modal Controls
    const ccuBtn = document.getElementById("ccu-proxy-btn");
    const ccuModal = document.getElementById("ccu-modal");
    const ccuClose = document.getElementById("ccu-modal-close");
    if (ccuBtn && ccuModal) {
      ccuBtn.addEventListener("click", () => this.openCCUModal());
    }
    const closeCCU = () => {
      ccuModal.classList.add("hidden");
      if (this.harvestInterval) {
        clearInterval(this.harvestInterval);
        this.harvestInterval = null;
      }
    };
    if (ccuClose && ccuModal) {
      ccuClose.addEventListener("click", closeCCU);
      ccuModal.addEventListener("click", (e) => {
        if (e.target === ccuModal) closeCCU();
      });
    }

    // Popover Close
    document.getElementById("popover-close-btn").addEventListener("click", () => {
      document.getElementById("article-hover-popover").classList.add("hidden");
    });

    // Drawer Controls
    document.getElementById("drawer-close-btn").addEventListener("click", () => this.closeStudyDrawer());
    document.getElementById("drawer-backdrop").addEventListener("click", () => this.closeStudyDrawer());
    document.getElementById("drawer-bookmark-btn").addEventListener("click", () => {
      if (this.selectedArticleNo) this.toggleBookmark(this.currentActId, this.selectedArticleNo);
    });
    document.getElementById("drawer-pdf-btn").addEventListener("click", () => window.print());
    document.getElementById("drawer-split-btn").addEventListener("click", () => this.toggleSplitWidth());

    // Global Keybindings (Law-student Power User)
    document.addEventListener("keydown", (e) => {
      const tag = document.activeElement ? document.activeElement.tagName : "";
      if (e.key === "Escape") {
        this.closeStudyDrawer();
        modal.classList.add("hidden");
        document.getElementById("flowchart-modal").classList.add("hidden");
        document.getElementById("article-hover-popover").classList.add("hidden");
        const cm = document.getElementById("ccu-modal");
        if (cm) cm.classList.add("hidden");
        return;
      }
      
      // Ctrl+K or Cmd+K: Focus law search
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        const s = document.getElementById("search-input");
        if (s) { s.focus(); s.select(); }
        return;
      }

      // Ctrl+B: Toggle TOC
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "b") {
        e.preventDefault();
        this.toggleToc();
        return;
      }

      if (tag === "INPUT" || tag === "TEXTAREA") return;
      
      if (e.key === "/" || e.key === "f") {
        e.preventDefault();
        const s = document.getElementById("search-input");
        if (s) { s.focus(); s.select(); }
      } else if (e.key === "ArrowLeft" || e.key === "[") {
        this.navigateAdjacentArticle(-1);
      } else if (e.key === "ArrowRight" || e.key === "]") {
        this.navigateAdjacentArticle(1);
      }
    });
  }

  toggleToc() {
    this.isTocCollapsed = !this.isTocCollapsed;
    const toc = document.getElementById("sidebar-toc");
    if (toc) toc.classList.toggle("collapsed", this.isTocCollapsed);
  }

  toggleSplitWidth() {
    const drawer = document.getElementById("study-drawer");
    if (!drawer) return;
    if (window.innerWidth <= 768) {
      const panel = document.getElementById("study-drawer-panel");
      panel.classList.toggle("expanded");
    } else {
      const cur = document.documentElement.style.getPropertyValue("--drawer-width") || "50%";
      const next = cur === "50%" ? "65%" : cur === "65%" ? "38%" : "50%";
      document.documentElement.style.setProperty("--drawer-width", next);
    }
  }

  // ---------------- CCU AutoRPA & Document Downloader ----------------
  async openCCUModal() {
    const modal = document.getElementById("ccu-modal");
    if (!modal) return;
    modal.classList.remove("hidden");
    await this.refreshCCUStatus();
    await this.loadLiteratureMetrics();
    await this.pollHarvestStatus();
    if (this.harvestInterval) clearInterval(this.harvestInterval);
    this.harvestInterval = setInterval(() => this.pollHarvestStatus(), 2500);

    const searchInput = document.getElementById("ccu-search-input");
    const resultsContainer = document.getElementById("ccu-search-results");
    if (resultsContainer && (!searchInput || !searchInput.value.trim())) {
      this.renderLiteratureEmptyState();
    }
  }

  async pollHarvestStatus() {
    try {
      const res = await fetch("/api/ccu/harvest/status");
      const json = await res.json();
      const st = json.data || {};
      const statusText = document.getElementById("harvest-status-text");
      const percentText = document.getElementById("harvest-percent-text");
      const progressBar = document.getElementById("harvest-progress-bar");
      const actionText = document.getElementById("harvest-current-action");
      const terminalBox = document.getElementById("harvest-terminal-logs");
      const activeDot = document.getElementById("harvest-active-dot");
      const startBtn = document.getElementById("ccu-start-harvest-btn");
      const stopBtn = document.getElementById("ccu-stop-harvest-btn");
      const calcText = document.getElementById("harvest-calc-text");
      const dupStat = document.getElementById("harvest-dup-stat");

      if (progressBar) progressBar.style.width = `${st.percent || 0}%`;
      if (percentText) percentText.textContent = `${st.percent || 0}%`;
      if (actionText) actionText.textContent = st.current_action || (st.is_running ? "採集中" : "待機");

      if (dupStat) {
        dupStat.textContent = `⚡ 輕量比對已略過重複: ${st.total_skipped_duplicates || 0} 篇`;
      }

      if (calcText && st.estimation) {
        const est = st.estimation;
        calcText.innerHTML = `📊 容量精算：均篇約 <b>${est.average_file_size_mb || 1.2} MB</b> ｜ 推估 10 年歷史總量約 <b>${est.estimated_10y_articles || 1400} 篇 (~${est.estimated_10y_gb || 1.65} GB)</b>`;
      }

      if (terminalBox && Array.isArray(st.logs) && st.logs.length > 0) {
        terminalBox.textContent = st.logs.join("\n");
        terminalBox.scrollTop = terminalBox.scrollHeight;
      }

      if (st.is_running) {
        if (activeDot) {
          activeDot.style.background = "#10b981";
          activeDot.style.boxShadow = "0 0 8px #10b981";
        }
        if (startBtn) startBtn.style.display = "none";
        if (stopBtn) stopBtn.style.display = "inline-block";
        if (statusText) {
          statusText.innerHTML = `<span style="color:#6ee7b7; font-weight:700;">● 採集中 (${st.current_year || 2026} 年回溯)</span> ｜ 已收錄 <b>${st.total_harvested || 0}</b> 篇 ｜ 略過重複 <b>${st.total_skipped_duplicates || 0}</b> 篇${st.last_saved_title ? ` ｜ 最新：《${esc(st.last_saved_title)}》` : ''}`;
        }
      } else {
        if (activeDot) {
          activeDot.style.background = "#71717a";
          activeDot.style.boxShadow = "none";
        }
        if (startBtn) {
          startBtn.style.display = "inline-block";
          startBtn.textContent = st.current_year && st.current_year < 2026 ? `▶️ 續採 (${st.current_year} 年)` : `▶️ 啟動自動採集`;
        }
        if (stopBtn) stopBtn.style.display = "none";
        if (statusText) {
          if (st.status === "completed") {
            statusText.innerHTML = `<span style="color:#34d399; font-weight:700;">🎉 歷史專論採集完畢</span> ｜ 共收錄 ${st.total_in_db || 0} 篇文獻 (${st.downloaded_size_mb || 0} MB)`;
          } else if (st.status === "stopped") {
            statusText.innerHTML = `<span style="color:#f59e0b; font-weight:700;">⏹️ 已於 ${st.current_year || 2026} 年安全暫停</span> ｜ 現有快取 ${st.total_in_db || 0} 篇文獻 (可隨時點擊續採)`;
          } else if (st.status === "error") {
            statusText.innerHTML = `<span style="color:#ef4444; font-weight:700;">⚠️ 採集中斷</span> ｜ ${esc(st.errors ? st.errors.join("; ") : "連線異常")}`;
          }
        }
      }

      const statSummary = document.getElementById("lit-stat-summary");
      if (statSummary && (st.total_in_db !== undefined)) {
        statSummary.textContent = `${st.total_in_db} 篇文獻 (${st.downloaded_size_mb || 0} MB)`;
      }
    } catch (e) {
      console.warn("Poll harvest status error:", e);
    }
  }

  renderLiteratureEmptyState() {
    const resultsContainer = document.getElementById("ccu-search-results");
    if (!resultsContainer) return;

    let quickTags = [];
    const act = this.currentAct;
    const artNo = this.selectedArticleNo;
    const actName = act ? act.name : "刑法";

    if (artNo) {
      if (this.currentActId === "criminal_code" && artNo === "10") {
        quickTags = ["公務員定義最新文獻", "重傷判準實務評析", "性交定義之演進", "刑法第10條"];
      } else if (this.currentActId === "criminal_code" && artNo === "185-3") {
        quickTags = ["酒駕不能安全駕駛評釋", "吐氣酒精濃度認定", "刑法第185條之3", "罪刑相當原則"];
      } else {
        quickTags = [
          `${actName}第${artNo}條`,
          `${actName} 第${artNo}條 專論評釋`,
          `第${artNo}條 構成要件爭議`,
          `${actName} 最新期刊`
        ];
      }
    } else {
      quickTags = ["刑法修正爭點評析", "公務員定義實務論述", "酒後駕車罪刑爭端", "沒收新制實務分析", "正當防衛裁判評釋"];
    }

    resultsContainer.innerHTML = `
      <div style="padding: 1.25rem 0.5rem; text-align: center; color: #a1a1aa;">
        <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">📖</div>
        <div style="font-weight: 600; font-size: 0.92rem; color: #d4d4d8; margin-bottom: 0.35rem;">尚無檢索結果</div>
        <div style="font-size: 0.8rem; color: #71717a; margin-bottom: 1.25rem;">
          輸入關鍵字，或直接點選下方與目前研析條文最關聯的推薦標籤：
        </div>
        <div style="text-align: left; background: #0f0f13; border: 1px solid #202025; border-radius: 8px; padding: 0.85rem;">
          <div style="font-size: 0.78rem; font-weight: 700; color: #60a5fa; margin-bottom: 0.6rem; display: flex; align-items: center; gap: 0.3rem;">
            <span>⚡</span>
            <span>${artNo ? `針對目前條文 (${actName} 第${esc(artNo)}條) 的推薦標籤：` : '推薦熱門法學檢索標籤：'}</span>
          </div>
          <div style="display: flex; flex-wrap: wrap; gap: 0.45rem;">
            ${quickTags.map(tag => `
              <button type="button" class="quick-tag-chip" data-query="${esc(tag)}" style="background: #18181b; border: 1px solid #2e2e36; color: #e4e4e7; border-radius: 6px; padding: 0.35rem 0.7rem; font-size: 0.8rem; cursor: pointer; transition: all 0.15s ease;">
                🔍 ${esc(tag)}
              </button>
            `).join('')}
          </div>
        </div>
      </div>
    `;

    resultsContainer.querySelectorAll(".quick-tag-chip").forEach(btn => {
      btn.addEventListener("click", () => {
        const q = btn.dataset.query;
        const searchInput = document.getElementById("ccu-search-input");
        if (searchInput) {
          searchInput.value = q;
        }
        const searchBtn = document.getElementById("ccu-do-search-btn");
        if (searchBtn) searchBtn.click();
      });
    });
  }

  async loadLiteratureMetrics() {
    const statSummary = document.getElementById("lit-stat-summary");
    try {
      const res = await fetch("/api/literature/stats");
      const json = await res.json();
      const s = json.data || {};
      const total = s.total_articles || 0;
      const downloaded = s.downloaded_articles || 0;
      const sizeMb = s.downloaded_size_mb || 0;
      if (statSummary) {
        statSummary.textContent = `${total} 篇文獻 (${sizeMb} MB，已下載 ${downloaded} 篇 PDF)`;
      }
    } catch (e) {
      console.warn("Load literature stats failed:", e);
      if (statSummary) {
        statSummary.textContent = "0 篇文獻 (0 MB)";
      }
    }
  }

  async refreshCCUStatus() {
    const badge = document.getElementById("ccu-auth-badge");
    const indicator = document.getElementById("ccu-header-indicator");
    const hintBox = document.getElementById("ccu-hint-box");
    const connectedBar = document.getElementById("ccu-auth-connected-bar");
    const configBox = document.getElementById("ccu-auth-config-box");
    const collapseConfigBtn = document.getElementById("ccu-collapse-config-btn");
    const lawbankPill = document.getElementById("ccu-lawbank-pill");
    const lawdataPill = document.getElementById("ccu-lawdata-pill");

    try {
      const res = await fetch("/api/ccu/status");
      const json = await res.json();
      const data = json.data || {};
      if (data.authenticated) {
        if (badge) {
          badge.textContent = "● 連線正常 (有效)";
          badge.style.background = "#052e16";
          badge.style.color = "#86efac";
        }
        if (indicator) {
          indicator.style.background = "#10b981";
          indicator.title = "AutoRPA 連線正常 (法源/月旦)";
        }
        if (connectedBar) connectedBar.style.display = "flex";
        if (configBox) configBox.style.display = "none";
        if (collapseConfigBtn) collapseConfigBtn.style.display = "inline-block";
        if (hintBox) hintBox.style.display = "none";
        if (lawbankPill) lawbankPill.style.display = data.lawbank_active ? "inline-block" : "none";
        if (lawdataPill) lawdataPill.style.display = data.lawdata_active ? "inline-block" : "none";
      } else {
        if (badge) {
          badge.textContent = "● 未認證 (需填 sessionid)";
          badge.style.background = "#2a2a32";
          badge.style.color = "#a1a1aa";
        }
        if (indicator) {
          indicator.style.background = "#71717a";
          indicator.title = "AutoRPA 未認證 (點擊設定)";
        }
        if (connectedBar) connectedBar.style.display = "none";
        if (configBox) configBox.style.display = "block";
        if (collapseConfigBtn) collapseConfigBtn.style.display = "none";
        if (hintBox && data.hint) {
          hintBox.textContent = data.hint;
          hintBox.style.display = "block";
          hintBox.style.color = "#f87171";
        }
      }
    } catch (e) {
      if (badge) badge.textContent = "連線失敗";
      if (indicator) indicator.style.background = "#ef4444";
    }
  }

  bindCCUEvents() {
    const saveBtn = document.getElementById("ccu-save-session-btn");
    const refreshBtn = document.getElementById("ccu-refresh-status-btn");
    const cookieInput = document.getElementById("ccu-cookie-input");
    const pasteBtn = document.getElementById("ccu-paste-btn");
    const hintBox = document.getElementById("ccu-hint-box");
    const searchBtn = document.getElementById("ccu-do-search-btn");
    const searchInput = document.getElementById("ccu-search-input");
    const resultsContainer = document.getElementById("ccu-search-results");
    const toggleConfigBtn = document.getElementById("ccu-toggle-config-btn");
    const collapseConfigBtn = document.getElementById("ccu-collapse-config-btn");
    const configBox = document.getElementById("ccu-auth-config-box");
    const clearCacheBtn = document.getElementById("ccu-clear-cache-btn");
    const tabAppBtn = document.getElementById("ccu-tab-app-btn");
    const tabNetBtn = document.getElementById("ccu-tab-net-btn");

    // Segmented Tabs
    if (tabAppBtn) {
      tabAppBtn.addEventListener("click", () => window.switchCCUTab("app"));
    }
    if (tabNetBtn) {
      tabNetBtn.addEventListener("click", () => window.switchCCUTab("net"));
    }

    // Toggle Re-configure Box
    if (toggleConfigBtn && configBox) {
      toggleConfigBtn.addEventListener("click", () => {
        configBox.style.display = configBox.style.display === "none" ? "block" : "none";
      });
    }
    if (collapseConfigBtn && configBox) {
      collapseConfigBtn.addEventListener("click", () => {
        configBox.style.display = "none";
      });
    }

    // Source Selector
    document.querySelectorAll(".ccu-source-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        if (window.switchCCUSource) {
          window.switchCCUSource(btn.dataset.source);
        }
      });
    });

    // Paste from Clipboard
    if (pasteBtn && cookieInput) {
      pasteBtn.addEventListener("click", async () => {
        try {
          const clipText = await navigator.clipboard.readText();
          if (clipText && clipText.trim()) {
            cookieInput.value = clipText.trim();
            pasteBtn.textContent = "✅";
            setTimeout(() => { pasteBtn.textContent = "📋"; }, 1500);
          } else {
            alert("剪貼簿目前沒有內容，請先複製 sessionid 或 Cookie");
          }
        } catch (e) {
          cookieInput.focus();
          alert("瀏覽器剪貼簿存取受限，請直接在輸入框內按「Ctrl + V」貼上！");
        }
      });
    }

    // Save and Verify Session
    if (saveBtn) {
      saveBtn.addEventListener("click", async () => {
        const val = cookieInput ? cookieInput.value.trim() : "";
        saveBtn.disabled = true;
        saveBtn.textContent = "驗證中...";
        try {
          const res = await fetch("/api/ccu/session", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ cookies: val })
          });
          const json = await res.json();
          const d = json.data || {};
          if (hintBox) {
            if (d.hint) {
              hintBox.textContent = d.hint;
              hintBox.style.display = "block";
              hintBox.style.color = d.authenticated ? "#34d399" : "#f87171";
            } else {
              hintBox.style.display = "none";
            }
          }
          await this.refreshCCUStatus();
          if (d.authenticated) {
            alert("✅ AutoRPA 認證成功！已成功連通法源法律網與月旦知識庫。");
          } else {
            alert("⚠️ " + (d.hint || "尚未通過 AutoRPA 驗證，請確認 sessionid 是否正確。"));
          }
        } catch (e) {
          alert("儲存失敗：" + e.message);
        } finally {
          saveBtn.disabled = false;
          saveBtn.textContent = "儲存並連線驗證";
        }
      });
    }

    if (refreshBtn) {
      refreshBtn.addEventListener("click", () => this.refreshCCUStatus());
    }

    const refreshStatsBtn = document.getElementById("ccu-refresh-stats-btn");
    if (refreshStatsBtn) {
      refreshStatsBtn.addEventListener("click", () => this.loadLiteratureMetrics());
    }

    // Auto-Harvest Controls
    const startHarvestBtn = document.getElementById("ccu-start-harvest-btn");
    const resetHarvestBtn = document.getElementById("ccu-reset-harvest-btn");
    const stopHarvestBtn = document.getElementById("ccu-stop-harvest-btn");

    if (startHarvestBtn) {
      startHarvestBtn.addEventListener("click", () => window.handleStartHarvest && window.handleStartHarvest(false));
    }
    if (resetHarvestBtn) {
      resetHarvestBtn.addEventListener("click", () => window.handleStartHarvest && window.handleStartHarvest(true));
    }
    if (stopHarvestBtn) {
      stopHarvestBtn.addEventListener("click", () => window.handleStopHarvest && window.handleStopHarvest());
    }

    if (clearCacheBtn) {
      clearCacheBtn.addEventListener("click", async () => {
        if (!confirm("確定要清理本地快取嗎？")) return;
        try {
          const res = await fetch("/api/cache/clear", { method: "POST" });
          const json = await res.json();
          alert(json.message || "快取已清理完畢。");
          await this.loadLiteratureMetrics();
        } catch (e) {
          alert("清理快取失敗：" + e.message);
        }
      });
    }

    // Literature Search (LawBank & LawData)
    if (searchBtn && searchInput) {
      const doSearch = async () => {
        const q = searchInput.value.trim();
        if (!q) {
          this.renderLiteratureEmptyState();
          return;
        }
        searchBtn.disabled = true;
        searchBtn.textContent = "檢索中...";
        if (resultsContainer) resultsContainer.innerHTML = '<div style="color:#71717a; text-align:center; padding:2rem;">正在向法源與月旦檢索期刊專論...</div>';
        try {
          const src = window.currentCCUSource || "all";
          const res = await fetch(`/api/ccu/search?q=${encodeURIComponent(q)}&source=${src}`);
          const json = await res.json();
          const items = json.data || [];
          if (!items.length) {
            resultsContainer.innerHTML = `
              <div style="color:#71717a; text-align:center; padding:2rem;">
                <div>查無相關法源或月旦文獻，或尚未通過 AutoRPA 認證。</div>
                <div style="margin-top:0.75rem;"><button id="ccu-back-empty-btn" class="filter-chip" style="cursor:pointer; font-size:0.8rem; padding:0.3rem 0.8rem;">返回推薦標籤</button></div>
              </div>
            `;
            const backBtn = document.getElementById("ccu-back-empty-btn");
            if (backBtn) backBtn.addEventListener("click", () => this.renderLiteratureEmptyState());
          } else {
            resultsContainer.innerHTML = `
              <div style="font-size:0.8rem; color:#a1a1aa; margin-bottom:0.6rem; display:flex; justify-content:space-between; align-items:center;">
                <span>檢索到 <b>${items.length}</b> 篇專論文獻（法源 / 月旦）：</span>
                <button id="ccu-back-empty-btn" style="background:none; border:none; color:#60a5fa; cursor:pointer; font-size:0.75rem; text-decoration:underline;">清除搜尋</button>
              </div>
              <div style="display:flex; flex-direction:column; gap:0.5rem;">
                ${items.map(item => {
                  const isLawData = item.source_db === "lawdata" || (item.source && item.source.includes("月旦"));
                  const badgeColor = isLawData ? "#fb923c" : "#60a5fa";
                  const badgeBg = isLawData ? "rgba(234,88,12,0.15)" : "rgba(59,130,246,0.15)";
                  const badgeBorder = isLawData ? "rgba(234,88,12,0.3)" : "rgba(59,130,246,0.3)";
                  const badgeLabel = isLawData ? "📚 月旦知識庫" : "⚖️ 法源法律網";
                  return `
                  <div class="card" style="padding:0.75rem; background:#111115; border:1px solid #232329; border-radius:6px;">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:0.5rem;">
                      <div style="font-weight:700; font-size:0.9rem;"><a href="${item.url}" target="_blank" rel="noopener noreferrer" style="color:#60a5fa; text-decoration:none;">${esc(item.title)} ↗</a></div>
                      <span class="badge" style="background:${badgeBg}; color:${badgeColor}; border:1px solid ${badgeBorder}; font-size:0.75rem; padding:1px 6px; border-radius:4px; flex-shrink:0;">${badgeLabel}</span>
                    </div>
                    <div style="font-size:0.75rem; color:#8e8e93; margin-top:0.35rem; display:flex; justify-content:space-between; align-items:center;">
                      <span>來源：${esc(item.source)}</span>
                      <a href="${item.url}" target="_blank" rel="noopener noreferrer" class="filter-chip" style="padding:0.2rem 0.55rem; font-size:0.75rem; text-decoration:none;">全文閱覽 ↗</a>
                    </div>
                  </div>
                `}).join('')}
              </div>
            `;
            const backBtn = document.getElementById("ccu-back-empty-btn");
            if (backBtn) backBtn.addEventListener("click", () => {
              if (searchInput) searchInput.value = "";
              this.renderLiteratureEmptyState();
            });
          }
        } catch (e) {
          if (resultsContainer) resultsContainer.innerHTML = `<div style="color:#ef4444; padding:1rem;">檢索出錯：${e.message}</div>`;
        } finally {
          searchBtn.disabled = false;
          searchBtn.textContent = "🔍 檢索論文";
        }
      };
      searchBtn.addEventListener("click", doSearch);
      searchInput.addEventListener("keydown", (e) => { if (e.key === "Enter") doSearch(); });
    }
  }

  // ---------------- Modal ----------------
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
    if (!query) { box.innerHTML = ""; return; }
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
    } catch (e) { box.innerHTML = `<div class="empty-note">搜尋失敗</div>`; }
  }

  // ---------------- Data Loading & Hierarchy ----------------
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
      this.renderToolbarMeta();
      this.renderChapterTocTree();
      this.renderStatuteStream(this.currentAct.articles || []);
      this.buildFastScrubber(this.currentAct.articles || []);
    } catch (e) { console.error(`Failed to load act ${actId}`, e); }
  }

  renderToolbarMeta() {
    const n = (this.currentAct.articles || []).length;
    const badge = document.getElementById("search-count-badge");
    if (badge) badge.textContent = `${n} 條`;

    const meta = document.getElementById("act-meta-inline");
    if (meta && this.currentAct) {
      meta.textContent = `(${this.currentAct.category || "法規"} · ${this.currentAct.last_modified || "現行"})`;
    }
  }

  // Tree Accordion for 編 (Part) > 章 (Chapter)
  renderChapterTocTree() {
    const list = document.getElementById("sidebar-chapter-list");
    if (!list || !this.currentAct) return;

    const parts = {};
    const defaultPart = "本法大綱";

    (this.currentAct.articles || []).forEach((art) => {
      const chStr = art.chapter || "全文";
      const segs = chStr.split(" / ").map((s) => s.trim());
      let partName = defaultPart;
      let chapterName = chStr;
      if (segs.length >= 2) {
        partName = segs[0];
        chapterName = segs.slice(1).join(" / ");
      }

      if (!parts[partName]) parts[partName] = [];
      if (!parts[partName].some((c) => c.title === chapterName)) {
        parts[partName].push({
          title: chapterName,
          firstArticleNo: art.article_no,
          fullChapter: chStr
        });
      }
    });

    let html = "";
    Object.keys(parts).forEach((partKey, pIdx) => {
      const chapters = parts[partKey];
      html += `
        <div class="toc-part-group">
          ${partKey !== defaultPart ? `
            <div class="toc-part-header" data-part="${esc(partKey)}">
              <span>${esc(partKey)}</span>
              <span class="part-arrow">▼</span>
            </div>` : ""}
          <div class="toc-part-body">
            ${chapters.map((ch) => `
              <div class="chapter-item" data-target-art="${esc(ch.firstArticleNo)}" data-full-chapter="${esc(ch.fullChapter)}">
                ${esc(ch.title)}
              </div>
            `).join("")}
          </div>
        </div>`;
    });

    list.innerHTML = html;

    // Part header accordion click
    list.querySelectorAll(".toc-part-header").forEach((header) => {
      header.addEventListener("click", () => {
        const body = header.nextElementSibling;
        if (body) {
          const isCollapsed = body.classList.toggle("collapsed");
          const arrow = header.querySelector(".part-arrow");
          if (arrow) arrow.textContent = isCollapsed ? "▶" : "▼";
        }
      });
    });

    // Chapter item click
    list.querySelectorAll(".chapter-item").forEach((item) => {
      item.addEventListener("click", () => {
        if (this.searchQuery) this.clearSearch();
        list.querySelectorAll(".chapter-item").forEach((i) => i.classList.remove("active"));
        item.classList.add("active");
        this.scrollToArticleCard(item.dataset.targetArt, "start");
      });
    });
  }

  // ---------------- Stream Rendering & Citations ----------------
  renderStatuteStream(articles) {
    const list = document.getElementById("statute-stream-list");
    const countBadge = document.getElementById("search-count-badge");
    const q = this.searchQuery;
    if (!list) return;

    if (!articles || articles.length === 0) {
      list.innerHTML = `<div class="empty-note big">查無符合條件的條文</div>`;
      if (countBadge) countBadge.textContent = "0 條";
      return;
    }
    if (countBadge) countBadge.textContent = `${articles.length} 條`;

    let html = "";
    articles.forEach((art) => {
      const marked = this.isBookmarked(this.currentActId, art.article_no);
      html += `
        <article class="stream-article-card ${this.selectedArticleNo === art.article_no ? 'active' : ''}" id="article-card-${esc(art.article_no)}" data-article-no="${esc(art.article_no)}" data-chapter="${esc(art.chapter || '')}">
          <div class="article-card-header">
            <div class="article-card-no">
              <span>第 ${hl(art.article_no, q)} 條</span>
              ${art.title ? `<span class="article-card-title">${hl(art.title, q)}</span>` : ""}
              <span class="card-bookmark-mark ${marked ? "" : "hidden"}" title="已收藏">${icon("bookmark-filled", 13)}</span>
            </div>
            <div class="article-card-actions">
              <button class="article-study-btn" data-article-no="${esc(art.article_no)}">研析</button>
            </div>
          </div>
          <div class="article-card-content">${renderArticleBody(art.content, q)}</div>
        </article>`;
    });

    list.innerHTML = html;

    // Click anywhere on card (or study button) to inspect in Split-view
    list.querySelectorAll(".stream-article-card").forEach((card) => {
      card.addEventListener("click", (e) => {
        if (e.target.closest(".article-ref-link")) return; // Don't trigger drawer if clicking citation popover link
        this.openStudyDrawer(card.dataset.articleNo);
      });
    });

    // Citations Hover Popover
    this.bindCitationEvents(list);
  }

  // Citation Hover / Tap Popover (Lawsnote style)
  bindCitationEvents(root) {
    const popover = document.getElementById("article-hover-popover");
    const popTitle = document.getElementById("popover-title");
    const popBody = document.getElementById("popover-body");
    const popJump = document.getElementById("popover-jump-btn");

    root.querySelectorAll(".article-ref-link").forEach((link) => {
      const targetNo = link.dataset.refNo;

      const showPopover = (e) => {
        e.stopPropagation();
        const art = (this.currentAct.articles || []).find((a) => a.article_no === targetNo);
        if (art) {
          popTitle.textContent = `${this.currentAct.name} 第 ${targetNo} 條 ${art.title || ""}`;
          popBody.textContent = art.content;
          popJump.onclick = () => {
            popover.classList.add("hidden");
            this.loadAndJumpArticle(targetNo);
          };
        } else {
          popTitle.textContent = `第 ${targetNo} 條 (跨法規參照)`;
          popBody.textContent = `此為跨法規條文，點選下方前往全國法規檢索。`;
          popJump.onclick = () => {
            window.open(`https://law.moj.gov.tw/LawClass/LawSearchNo.aspx?PC=${this.currentAct.pcode}&AN=${targetNo}`, "_blank");
          };
        }

        const rect = link.getBoundingClientRect();
        let top = rect.bottom + 8;
        let left = Math.max(10, Math.min(window.innerWidth - 330, rect.left));
        if (top + 200 > window.innerHeight) top = rect.top - 200;

        popover.style.top = `${top}px`;
        popover.style.left = `${left}px`;
        popover.classList.remove("hidden");
      };

      link.addEventListener("mouseenter", showPopover);
      link.addEventListener("click", showPopover);
    });
  }

  filterStreamArticles(query) {
    if (!this.currentAct || !this.currentAct.articles) return;
    this.searchQuery = query;
    let list = this.currentAct.articles;

    // Filter Chips
    if (this.activeFilter === "penalty") {
      list = list.filter((a) => (a.content || "").includes("處") && ((a.content || "").includes("年") || (a.content || "").includes("罰金") || (a.content || "").includes("拘役")));
    } else if (this.activeFilter === "important") {
      list = list.filter((a) => (a.amendment_history && a.amendment_history.length > 0) || (a.title && a.title.length > 0));
    }

    if (query) {
      const q = query.toLowerCase();
      list = list.filter(
        (art) =>
          String(art.article_no).toLowerCase().includes(q) ||
          (art.title && art.title.toLowerCase().includes(q)) ||
          (art.content && art.content.toLowerCase().includes(q))
      );
    }

    this.renderStatuteStream(list);
  }

  clearSearch() {
    const input = document.getElementById("search-input");
    if (input) input.value = "";
    document.getElementById("search-clear").classList.add("hidden");
    this.searchQuery = "";
    this.filterStreamArticles("");
  }

  // ---------------- Drawer / Split View ----------------
  async openStudyDrawer(articleNo) {
    this.selectedArticleNo = articleNo;
    this.updateHashRoute(this.currentActId, articleNo);
    this.updateBookmarkButtonState(articleNo);

    // Active Card Highlight
    document.querySelectorAll(".stream-article-card").forEach((c) => {
      c.classList.toggle("active", c.dataset.articleNo === articleNo);
    });

    document.getElementById("drawer-article-badge").textContent = `第 ${articleNo} 條`;

    let art = (this.currentAct.articles || []).find((a) => a.article_no === articleNo) || {
      article_no: articleNo,
      content: ""
    };
    try {
      const resp = await fetch(`/api/acts/${this.currentActId}/articles/${articleNo}`);
      const json = await resp.json();
      if (json.success && json.data) art = json.data;
    } catch (e) { console.warn(e); }

    const crumb = [this.currentAct.name, art.chapter].filter(Boolean).join("  ›  ");
    const crumbEl = document.getElementById("drawer-breadcrumb");
    crumbEl.textContent = crumb;
    crumbEl.title = crumb;

    const scrollBody = document.getElementById("study-drawer-scroll-body");
    const nLinks = (art.related_articles || []).length + (art.attachments || []).length;
    const nInsights = (art.practical_insights || []).length;
    const nAmend = (art.amendment_history || []).length;

    const tabBtn = (id, iconName, label, count) =>
      `<button class="drawer-tab-btn ${this.activeTab === id ? "active" : ""}" data-tab="${id}">${icon(iconName, 15)}<span>${label}</span>${count ? `<span class="tab-count">${count}</span>` : ""}</button>`;

    // Consistent Drawer Structure: Fixed Top Article Quote Box, followed by Sticky Tabs & Analysis
    scrollBody.innerHTML = `
      <section class="drawer-hero-section">
        <h1 class="drawer-hero-title">${esc(this.currentAct.name)} 第 ${esc(art.article_no)} 條</h1>
        ${art.title ? `<div class="drawer-hero-subtitle">${esc(art.title)}</div>` : ""}
        <div class="drawer-hero-article-box">
          <button class="article-box-copy-action" id="drawer-copy-article-btn" title="複製條文">${icon("copy", 13)}<span>複製</span></button>
          ${renderArticleBody(art.content, "")}
        </div>
      </section>

      <nav class="drawer-tabs-bar">
        ${tabBtn("key_knowledge", "lightbulb", "關鍵知識", 0)}
        ${tabBtn("insights", "gavel", "實務見解", nInsights)}
        ${tabBtn("content_links", "link", "內容連結", nLinks)}
        ${tabBtn("legislative_history", "file", "立法理由與沿革", nAmend)}
        ${tabBtn("my_bookmarks", "star", "我的收藏", this.bookmarks.length)}
      </nav>

      <div class="drawer-tab-content-area" id="drawer-tab-content-area">
        ${this.generateTabContentHtml(art)}
      </div>

      <footer class="drawer-bottom-nav">
        <button class="drawer-nav-btn" id="drawer-prev-btn">${icon("arrowLeft", 14)}<span>上一條</span></button>
        <button class="drawer-nav-btn ghost" id="drawer-permalink-btn" title="在新分頁開啟此條">
          <span>第 ${esc(art.article_no)} 條</span>${icon("external", 13)}
        </button>
        <button class="drawer-nav-btn" id="drawer-next-btn"><span>下一條</span>${icon("arrowRight", 14)}</button>
      </footer>`;

    scrollBody.scrollTop = 0;

    scrollBody.querySelector("#drawer-copy-article-btn").addEventListener("click", (e) => {
      const text = `${this.currentAct.name} 第 ${art.article_no} 條 ${art.title || ""}\n${articleCopyText(art.content)}`;
      this.copyToClipboard(text, e.currentTarget);
    });
    scrollBody.querySelector("#drawer-permalink-btn").addEventListener("click", () => {
      window.open(`${window.location.origin}${window.location.pathname}#/act/${this.currentActId}/article/${art.article_no}`, "_blank");
    });

    this.bindDrawerTabs(scrollBody, art);
    this.bindDrawerNavButtons(scrollBody, art);
    this.bindDynamicContent(scrollBody);

    const drawer = document.getElementById("study-drawer");
    drawer.classList.remove("hidden");
    const drag = document.getElementById("split-drag-handle");
    if (drag) drag.classList.remove("hidden");

    // Auto-scroll target article into upper 40% on mobile so view is never obscured
    if (window.innerWidth <= 768) {
      this.scrollToArticleCard(articleNo, "start");
    }
  }

  closeStudyDrawer() {
    document.getElementById("study-drawer").classList.add("hidden");
    const drag = document.getElementById("split-drag-handle");
    if (drag) drag.classList.add("hidden");
    document.querySelectorAll(".stream-article-card.active").forEach((c) => c.classList.remove("active"));
    if (this.currentActId) this.updateHashRoute(this.currentActId);
  }

  navigateAdjacentArticle(direction) {
    if (!this.currentAct || !this.selectedArticleNo) return;
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

  bindDynamicContent(root) {
    // Accordion
    root.querySelectorAll(".faq-q-trigger").forEach((header) => {
      header.addEventListener("click", () => {
        const body = header.nextElementSibling;
        if (!body) return;
        const open = body.classList.toggle("open");
        header.classList.toggle("open", open);
      });
    });

    // Flowchart Fullscreen Trigger
    root.querySelectorAll(".flowchart-fullscreen-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const modal = document.getElementById("flowchart-modal");
        const body = document.getElementById("flowchart-modal-body");
        const chartEl = root.querySelector(".flowchart-svg-diagram") || root.querySelector(".flowchart-svg-card");
        if (modal && body && chartEl) {
          body.innerHTML = chartEl.outerHTML;
          modal.classList.remove("hidden");
        }
      });
    });

    // Bookmarks Jump / Delete
    root.querySelectorAll(".bookmark-jump-btn").forEach((btn) => {
      btn.addEventListener("click", () => this.loadAndJumpArticle(btn.dataset.artNo));
    });
    root.querySelectorAll(".bookmark-delete-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        this.toggleBookmark(btn.dataset.actId, btn.dataset.artNo);
        const area = document.getElementById("drawer-tab-content-area");
        area.innerHTML = this.renderMyBookmarksHtml();
        this.bindDynamicContent(area);
      });
    });

    // Drawer CCU Open Config Modal Trigger
    root.querySelectorAll(".drawer-open-ccu-config-btn").forEach((btn) => {
      btn.addEventListener("click", () => this.openCCUModal());
    });

    // Drawer CCU Paper Search Trigger
    root.querySelectorAll(".drawer-ccu-fetch-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const query = btn.dataset.query;
        const card = btn.closest(".card");
        const box = card ? card.querySelector(".drawer-ccu-results-box") : null;
        if (!box) return;
        btn.disabled = true;
        btn.textContent = "檢索中...";
        box.innerHTML = '<div style="color:#a1a1aa; padding:0.4rem 0;">正在透過 AutoRPA 檢索法源期刊專論...</div>';
        try {
          const res = await fetch(`/api/ccu/search?q=${encodeURIComponent(query)}`);
          const json = await res.json();
          const items = json.data || [];
          if (!items.length) {
            box.innerHTML = '<div style="color:#71717a; padding:0.4rem 0;">查無相關文獻，或法源校園代理尚未認證（可點選導覽列 🏛️ 按鈕確認連線）。</div>';
          } else {
            box.innerHTML = items.map(item => `
              <div style="padding:0.5rem 0; border-bottom:1px solid #27272a;">
                <div style="font-weight:600;"><a href="${item.url}" target="_blank" rel="noopener noreferrer" style="color:#60a5fa; text-decoration:none;">${esc(item.title)} ↗</a></div>
                <div style="font-size:0.75rem; color:#8e8e93; margin-top:2px;">來源：${esc(item.source)}</div>
              </div>
            `).join('');
          }
        } catch (e) {
          box.innerHTML = `<div style="color:#ef4444; padding:0.4rem 0;">檢索失敗：${e.message}</div>`;
        } finally {
          btn.disabled = false;
          btn.textContent = "🔍 檢索法源論文";
        }
      });
    });

    // Dual-Binding Literature for this Article
    const litContainer = root.querySelector("#drawer-article-literature-list");
    if (litContainer && this.currentActId && this.selectedArticleNo) {
      fetch(`/api/acts/${this.currentActId}/articles/${this.selectedArticleNo}/literature`)
        .then(res => res.json())
        .then(json => {
          const items = json.data || [];
          if (!items.length) {
            litContainer.innerHTML = '<div class="card" style="padding:0.75rem; color:#71717a; font-size:0.85rem;">本條目前尚無預載文獻，您可透過下方即時檢索法源法律網最新期刊專論。</div>';
            return;
          }
          litContainer.innerHTML = items.map(lit => `
            <div class="card" style="margin-bottom:0.75rem; padding:0.85rem;">
              <div style="font-weight:700; font-size:0.95rem; color:#60a5fa; margin-bottom:0.25rem;">
                ${esc(lit.title)}${lit.subtitle ? ` <span style="font-weight:400; color:#d4d4d8; font-size:0.85rem;">—— ${esc(lit.subtitle)}</span>` : ''}
              </div>
              <div style="font-size:0.8rem; color:#a1a1aa; margin-bottom:0.5rem; display:flex; flex-wrap:wrap; gap:0.5rem;">
                <span>👤 <b>${esc(lit.author)}</b>${lit.author_affiliation ? ` (${esc(lit.author_affiliation)})` : ''}</span>
                <span>📚 <b>${esc(lit.journal_name)}</b></span>
                <span>📅 ${esc(lit.pub_date || String(lit.pub_year || ''))}</span>
                ${lit.volume || lit.issue ? `<span>${esc(lit.volume || '')} ${esc(lit.issue || '')}</span>` : ''}
                ${lit.pages ? `<span>p. ${esc(lit.pages)}</span>` : ''}
              </div>
              ${lit.abstract ? `<div style="font-size:0.85rem; line-height:1.6; color:#d4d4d8; margin-bottom:0.5rem; background:#141417; padding:0.5rem; border-radius:4px;">${esc(lit.abstract)}</div>` : ''}
              <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.75rem; color:#71717a;">
                <span>檔案大小：${lit.file_size_mb ? `${lit.file_size_mb} MB` : '未載入'}</span>
                ${lit.file_path ? `<a href="/${lit.file_path}" target="_blank" class="filter-chip active" style="padding:0.2rem 0.6rem; font-size:0.75rem; text-decoration:none;">📄 開啟全文 PDF</a>` : ''}
              </div>
            </div>
          `).join('');
        })
        .catch(() => {
          litContainer.innerHTML = '<div style="color:#71717a; font-size:0.85rem;">載入關聯文獻失敗。</div>';
        });
    }
  }

  generateTabContentHtml(art) {
    switch (this.activeTab) {
      case "insights":
        return this.renderInsightsHtml(art);
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

  // ---------------- Tab 1: 關鍵知識 ----------------
  renderKeyKnowledgeHtml(art) {
    const parsed = this.parseArticleElements(art);
    let html = "";

    if (art.summary) {
      html += `
        <div class="callout-box">
          <div class="callout-title">${icon("lightbulb", 15)}<span>重點摘要 (法律人核心提煉)</span></div>
          <div>${esc(art.summary)}</div>
        </div>`;
    }

    const qas = art.vernacular_qa && art.vernacular_qa.length ? art.vernacular_qa : [];
    if (qas.length) {
      html += `<section>${sectionHeading("book", "白話與實務解讀 (法律人真實問答)", `${qas.length}`)}
        ${qas.map((item) => `
          <div class="card">
            <div class="card-title">${esc(item.question || item.q || "")}</div>
            <div class="card-body" style="white-space: pre-wrap; line-height: 1.65;">${esc(item.answer || item.a || "")}</div>
          </div>
        `).join("")}
      </section>`;
    }

    if (art.legal_definition) {
      html += `<section>${sectionHeading("file", "法律人專業深度解讀")}
        <div class="card">
          <div class="card-body" style="white-space: pre-wrap; line-height: 1.7; font-size: 0.95rem; color: #d0d0d8;">${esc(art.legal_definition)}</div>
        </div>
      </section>`;
    }

    html += `<section>${sectionHeading("landmark", "構成要件與法律效果")}
      <div class="card kv-card">
        <div class="kv"><div class="kv-label">規範客體 / 行為態樣</div><div class="kv-val">${parsed.behaviorType}</div></div>
        <div class="kv"><div class="kv-label">主觀責任要求</div><div class="kv-val">${parsed.intentType}</div></div>
        <div class="kv"><div class="kv-label">法定效果 / 刑度範疇</div><div class="kv-val kv-accent">${parsed.penaltyType}</div></div>
        <div class="kv"><div class="kv-label">訴訟追訴特性</div><div class="kv-val">${parsed.prosecutionType}</div></div>
      </div>
    </section>`;

    // Flowchart Vector SVG Image with Fullscreen button
    html += `<section>${sectionHeading("branch", "思考脈絡審查路徑圖 (向量流程圖)")}
      <div class="flowchart-svg-card">
        <div class="flowchart-svg-toolbar">
          <button class="flowchart-btn flowchart-fullscreen-btn" title="全螢幕向量放大檢視">${icon("maximize", 12)} 放大檢視</button>
        </div>
        ${this.generateFlowchartSvg(art)}
      </div>
    </section>`;

    const faqs = art.faqs && art.faqs.length ? art.faqs : [];
    if (faqs.length) {
      html += `<section>${sectionHeading("help", "大家也在問", `${faqs.length}`)}
        ${faqs.map((faq) => `
          <div class="faq-item-box">
            <div class="faq-q-trigger"><span>${esc(faq.q)}</span><span class="faq-chevron">${icon("plus", 14)}</span></div>
            <div class="faq-a-content">${esc(faq.a || faq.answer || "")}</div>
          </div>
        `).join("")}
      </section>`;
    }

    return html;
  }

  // ---------------- Flowchart Vector SVG Generator (Pure Vector Diagram / Image) ----------------
  generateFlowchartSvg(art) {
    const actName = this.currentAct ? this.currentAct.name : "";
    const isCriminal = actName.includes("刑法") || actName.includes("懲治") || actName.includes("毒品");
    const artNo = String(art.article_no || "").trim();

    if (artNo === "1" && isCriminal) {
      // 刑法第 1 條 罪刑法定原則專屬審查向量流程圖 (長方形與橢圓節點，無菱形)
      return `
        <svg class="flowchart-svg-diagram" viewBox="0 0 520 440" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <marker id="flow-arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto">
              <path d="M 0 1 L 8 5 L 0 9 z" fill="#8e8e93" />
            </marker>
          </defs>

          <!-- Start Node -->
          <rect x="180" y="16" width="160" height="38" rx="6" fill="#181820" stroke="#3e3e4a" stroke-width="1.5" />
          <text x="260" y="40" fill="#fafafa" font-size="13" font-weight="700" text-anchor="middle">生活事實行為發生</text>

          <line x1="260" y1="54" x2="260" y2="86" stroke="#71717a" stroke-width="1.5" marker-end="url(#flow-arrow)" />

          <!-- Decision 1: Oval / Rounded Rect (長方形/橢圓) -->
          <rect x="135" y="88" width="250" height="44" rx="22" fill="#14141c" stroke="#d4d4d8" stroke-width="1.5" />
          <text x="260" y="115" fill="#ffffff" font-size="12" font-weight="700" text-anchor="middle">行為時是否有成文法律明文規定？</text>

          <!-- Branch 否 -> Curve to 不構成犯罪 -->
          <path d="M 135 110 L 80 110 L 80 340" fill="none" stroke="#71717a" stroke-width="1.5" marker-end="url(#flow-arrow)" />
          <rect x="92" y="98" width="24" height="18" rx="4" fill="#2d1217" stroke="#f43f5e" stroke-width="1"/>
          <text x="104" y="111" fill="#fb7185" font-size="11" font-weight="800" text-anchor="middle">否</text>

          <!-- Branch 是 -> Down -->
          <line x1="260" y1="132" x2="260" y2="174" stroke="#71717a" stroke-width="1.5" marker-end="url(#flow-arrow)" />
          <rect x="268" y="142" width="24" height="18" rx="4" fill="#12281e" stroke="#10b981" stroke-width="1"/>
          <text x="280" y="155" fill="#34d399" font-size="11" font-weight="800" text-anchor="middle">是</text>

          <!-- Decision 2: Oval / Rounded Rect (長方形/橢圓) -->
          <rect x="135" y="176" width="250" height="44" rx="22" fill="#14141c" stroke="#d4d4d8" stroke-width="1.5" />
          <text x="260" y="203" fill="#ffffff" font-size="12" font-weight="700" text-anchor="middle">是否為不利於行為人之類推適用？</text>

          <!-- Branch 是 -> Left to 違憲聲請 / 禁止 -->
          <path d="M 135 198 L 80 198" fill="none" stroke="#71717a" stroke-width="1.5" marker-end="url(#flow-arrow)" />
          <rect x="96" y="188" width="24" height="18" rx="4" fill="#2d1217" stroke="#f43f5e" stroke-width="1"/>
          <text x="108" y="201" fill="#fb7185" font-size="11" font-weight="800" text-anchor="middle">是</text>

          <rect x="15" y="215" width="130" height="38" rx="6" fill="#1e1318" stroke="#f43f5e" stroke-width="1.5" />
          <text x="80" y="239" fill="#fca5a5" font-size="12" font-weight="700" text-anchor="middle">聲請違憲審查 / 禁止</text>

          <!-- Branch 否 -> Down -->
          <line x1="260" y1="220" x2="260" y2="262" stroke="#71717a" stroke-width="1.5" marker-end="url(#flow-arrow)" />
          <rect x="268" y="230" width="24" height="18" rx="4" fill="#12281e" stroke="#10b981" stroke-width="1"/>
          <text x="280" y="243" fill="#34d399" font-size="11" font-weight="800" text-anchor="middle">否</text>

          <!-- Decision 3: Oval / Rounded Rect (長方形/橢圓) -->
          <rect x="135" y="264" width="250" height="44" rx="22" fill="#14141c" stroke="#d4d4d8" stroke-width="1.5" />
          <text x="260" y="291" fill="#ffffff" font-size="12" font-weight="700" text-anchor="middle">是否為事後立法 (溯及既往)？</text>

          <!-- Branch 是 -> Curve to 不構成犯罪 -->
          <path d="M 135 286 L 80 286" fill="none" stroke="#71717a" stroke-width="1.5" marker-end="url(#flow-arrow)" />
          <rect x="96" y="276" width="24" height="18" rx="4" fill="#2d1217" stroke="#f43f5e" stroke-width="1"/>
          <text x="108" y="289" fill="#fb7185" font-size="11" font-weight="800" text-anchor="middle">是</text>

          <!-- Branch 否 -> Down to 依法處罰 -->
          <line x1="260" y1="308" x2="260" y2="348" stroke="#71717a" stroke-width="1.5" marker-end="url(#flow-arrow)" />
          <rect x="268" y="318" width="24" height="18" rx="4" fill="#12281e" stroke="#10b981" stroke-width="1"/>
          <text x="280" y="331" fill="#34d399" font-size="11" font-weight="800" text-anchor="middle">否</text>

          <!-- Terminal 1: 不構成犯罪 -->
          <rect x="15" y="352" width="130" height="44" rx="6" fill="#241117" stroke="#f43f5e" stroke-width="1.5" />
          <text x="80" y="379" fill="#fda4af" font-size="13" font-weight="800" text-anchor="middle">不構成犯罪</text>

          <!-- Terminal 2: 依法處罰 -->
          <rect x="195" y="352" width="130" height="44" rx="6" fill="#11241a" stroke="#10b981" stroke-width="1.5" />
          <text x="260" y="379" fill="#86efac" font-size="13" font-weight="800" text-anchor="middle">依法處罰</text>
        </svg>
      `;
    }

    if (isCriminal) {
      // 刑事法律三階層通用向量審查流程圖 (長方形與橢圓節點，無菱形)
      return `
        <svg class="flowchart-svg-diagram" viewBox="0 0 520 440" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <marker id="flow-arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto">
              <path d="M 0 1 L 8 5 L 0 9 z" fill="#8e8e93" />
            </marker>
          </defs>

          <!-- Start Node -->
          <rect x="170" y="16" width="180" height="36" rx="6" fill="#181820" stroke="#3e3e4a" stroke-width="1.5" />
          <text x="260" y="39" fill="#fafafa" font-size="13" font-weight="700" text-anchor="middle">生活事實行為發生</text>

          <line x1="260" y1="52" x2="260" y2="82" stroke="#71717a" stroke-width="1.5" marker-end="url(#flow-arrow)" />

          <!-- Decision 1: 構成要件該當 (長方形與橢圓) -->
          <rect x="120" y="84" width="280" height="44" rx="22" fill="#14141c" stroke="#d4d4d8" stroke-width="1.5" />
          <text x="260" y="111" fill="#ffffff" font-size="12" font-weight="700" text-anchor="middle">一、行為是否該當本條第 ${artNo} 條法定要件？</text>

          <!-- Branch 否 -> Left to 不罰 -->
          <path d="M 120 106 L 70 106 L 70 340" fill="none" stroke="#71717a" stroke-width="1.5" marker-end="url(#flow-arrow)" />
          <rect x="80" y="95" width="24" height="18" rx="4" fill="#2d1217" stroke="#f43f5e" stroke-width="1"/>
          <text x="92" y="108" fill="#fb7185" font-size="11" font-weight="800" text-anchor="middle">否</text>

          <!-- Branch 是 -> Down -->
          <line x1="260" y1="128" x2="260" y2="168" stroke="#71717a" stroke-width="1.5" marker-end="url(#flow-arrow)" />
          <rect x="268" y="138" width="24" height="18" rx="4" fill="#12281e" stroke="#10b981" stroke-width="1"/>
          <text x="280" y="151" fill="#34d399" font-size="11" font-weight="800" text-anchor="middle">是</text>

          <!-- Decision 2: 違法性 (長方形與橢圓) -->
          <rect x="120" y="170" width="280" height="44" rx="22" fill="#14141c" stroke="#d4d4d8" stroke-width="1.5" />
          <text x="260" y="197" fill="#ffffff" font-size="12" font-weight="700" text-anchor="middle">二、是否存在阻卻違法事由 (§21~24)？</text>

          <!-- Branch 有 -> Left to 阻卻不罰 -->
          <path d="M 120 192 L 70 192" fill="none" stroke="#71717a" stroke-width="1.5" marker-end="url(#flow-arrow)" />
          <rect x="80" y="181" width="24" height="18" rx="4" fill="#2d1217" stroke="#f43f5e" stroke-width="1"/>
          <text x="92" y="194" fill="#fb7185" font-size="11" font-weight="800" text-anchor="middle">有</text>

          <!-- Branch 無 -> Down -->
          <line x1="260" y1="214" x2="260" y2="254" stroke="#71717a" stroke-width="1.5" marker-end="url(#flow-arrow)" />
          <rect x="268" y="224" width="24" height="18" rx="4" fill="#12281e" stroke="#10b981" stroke-width="1"/>
          <text x="280" y="237" fill="#34d399" font-size="11" font-weight="800" text-anchor="middle">無</text>

          <!-- Decision 3: 罪責 (長方形與橢圓) -->
          <rect x="120" y="256" width="280" height="44" rx="22" fill="#14141c" stroke="#d4d4d8" stroke-width="1.5" />
          <text x="260" y="283" fill="#ffffff" font-size="12" font-weight="700" text-anchor="middle">三、行為人是否具責任能力 (§18, 19)？</text>

          <!-- Branch 無 -> Left to 不罰/保安處分 -->
          <path d="M 120 278 L 70 278" fill="none" stroke="#71717a" stroke-width="1.5" marker-end="url(#flow-arrow)" />
          <rect x="80" y="267" width="24" height="18" rx="4" fill="#2d1217" stroke="#f43f5e" stroke-width="1"/>
          <text x="92" y="280" fill="#fb7185" font-size="11" font-weight="800" text-anchor="middle">無</text>

          <!-- Branch 具備 -> Down to 本罪成立處罰 -->
          <line x1="260" y1="300" x2="260" y2="346" stroke="#71717a" stroke-width="1.5" marker-end="url(#flow-arrow)" />
          <rect x="268" y="312" width="24" height="18" rx="4" fill="#12281e" stroke="#10b981" stroke-width="1"/>
          <text x="280" y="325" fill="#34d399" font-size="11" font-weight="800" text-anchor="middle">有</text>

          <!-- Terminal 1: 不罰 / 阻卻犯罪 -->
          <rect x="10" y="352" width="130" height="44" rx="6" fill="#241117" stroke="#f43f5e" stroke-width="1.5" />
          <text x="75" y="379" fill="#fda4af" font-size="12.5" font-weight="800" text-anchor="middle">不構成犯罪 (不罰)</text>

          <!-- Terminal 2: 依法科刑處罰 -->
          <rect x="195" y="352" width="130" height="44" rx="6" fill="#11241a" stroke="#10b981" stroke-width="1.5" />
          <text x="260" y="379" fill="#86efac" font-size="12.5" font-weight="800" text-anchor="middle">依法成罪並處罰</text>
        </svg>
      `;
    }

    // 一般法規與民事要件審查向量流程圖 (長方形與橢圓節點，無菱形)
    return `
      <svg class="flowchart-svg-diagram" viewBox="0 0 520 400" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <marker id="flow-arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M 0 1 L 8 5 L 0 9 z" fill="#8e8e93" />
          </marker>
        </defs>

        <!-- Start Node -->
        <rect x="170" y="16" width="180" height="36" rx="6" fill="#181820" stroke="#3e3e4a" stroke-width="1.5" />
        <text x="260" y="39" fill="#fafafa" font-size="13" font-weight="700" text-anchor="middle">法律事實關係發生</text>

        <line x1="260" y1="52" x2="260" y2="86" stroke="#71717a" stroke-width="1.5" marker-end="url(#flow-arrow)" />

        <!-- Decision 1: 要件成就 (長方形與橢圓) -->
        <rect x="120" y="88" width="280" height="44" rx="22" fill="#14141c" stroke="#d4d4d8" stroke-width="1.5" />
        <text x="260" y="115" fill="#ffffff" font-size="12" font-weight="700" text-anchor="middle">一、事實是否符合本條法定構成要件？</text>

        <!-- Branch 否 -> Left to 無效果 -->
        <path d="M 120 110 L 70 110 L 70 300" fill="none" stroke="#71717a" stroke-width="1.5" marker-end="url(#flow-arrow)" />
        <rect x="80" y="99" width="24" height="18" rx="4" fill="#2d1217" stroke="#f43f5e" stroke-width="1"/>
        <text x="92" y="112" fill="#fb7185" font-size="11" font-weight="800" text-anchor="middle">否</text>

        <!-- Branch 是 -> Down -->
        <line x1="260" y1="132" x2="260" y2="176" stroke="#71717a" stroke-width="1.5" marker-end="url(#flow-arrow)" />
        <rect x="268" y="144" width="24" height="18" rx="4" fill="#12281e" stroke="#10b981" stroke-width="1"/>
        <text x="280" y="157" fill="#34d399" font-size="11" font-weight="800" text-anchor="middle">是</text>

        <!-- Decision 2: 阻卻事由 (長方形與橢圓) -->
        <rect x="120" y="178" width="280" height="44" rx="22" fill="#14141c" stroke="#d4d4d8" stroke-width="1.5" />
        <text x="260" y="205" fill="#ffffff" font-size="12" font-weight="700" text-anchor="middle">二、是否存在時效抗辯或排除事由？</text>

        <!-- Branch 有 -> Left -->
        <path d="M 120 200 L 70 200" fill="none" stroke="#71717a" stroke-width="1.5" marker-end="url(#flow-arrow)" />
        <rect x="80" y="189" width="24" height="18" rx="4" fill="#2d1217" stroke="#f43f5e" stroke-width="1"/>
        <text x="92" y="202" fill="#fb7185" font-size="11" font-weight="800" text-anchor="middle">有</text>

        <!-- Branch 無 -> Down to 成立履行 -->
        <line x1="260" y1="222" x2="260" y2="306" stroke="#71717a" stroke-width="1.5" marker-end="url(#flow-arrow)" />
        <rect x="268" y="254" width="24" height="18" rx="4" fill="#12281e" stroke="#10b981" stroke-width="1"/>
        <text x="280" y="267" fill="#34d399" font-size="11" font-weight="800" text-anchor="middle">無</text>

        <!-- Terminal 1: 權利阻卻 / 無法律效果 -->
        <rect x="10" y="312" width="130" height="44" rx="6" fill="#241117" stroke="#f43f5e" stroke-width="1.5" />
        <text x="75" y="339" fill="#fda4af" font-size="12.5" font-weight="800" text-anchor="middle">權利阻卻 / 不生效力</text>

        <!-- Terminal 2: 法律效果成立並履行 -->
        <rect x="195" y="312" width="130" height="44" rx="6" fill="#11241a" stroke="#10b981" stroke-width="1.5" />
        <text x="260" y="339" fill="#86efac" font-size="12.5" font-weight="800" text-anchor="middle">權利健全依法履行</text>
      </svg>
    `;
  }

  // ---------------- Tab 2: 實務見解 (Dedicated Tab) ----------------
  renderInsightsHtml(art) {
    const insights = art.practical_insights || [];
    const letters = art.official_letters || [];
    const actName = esc(this.currentAct.name);

    let html = `
      <section>${sectionHeading("gavel", "大法庭裁定、憲法法庭判決與最高法院裁判 (法律人/司法院)", `${insights.length}`)}
        ${insights.length ? insights.map((ins) => `
          <div class="card">
            <div class="card-title accent">${esc(ins.court || "最高法院")} · ${esc(ins.ref || "重要裁判")}</div>
            <div class="card-body" style="line-height: 1.6;">${esc(ins.summary || "")}</div>
          </div>
        `).join("") : `
          <div class="card">
            <div class="card-body">本條尚未收錄重點精選摘要，您可透過下方資料庫即時查詢引用本條之所有裁判全文：</div>
          </div>
        `}
      </section>`;

    if (letters.length) {
      html += `
        <section>${sectionHeading("book", "法務部令函與行政函釋 (法律人)", `${letters.length}`)}
          ${letters.map((letItem) => `
            <div class="card">
              <div class="card-title accent">${esc(letItem.ref || "法務部令函")} · ${esc(letItem.date || "")}</div>
              <div class="card-body" style="line-height: 1.6; white-space: pre-wrap;">${esc(letItem.summary || letItem.content || "")}</div>
            </div>
          `).join("")}
        </section>`;
    }

    html += `
      <section>${sectionHeading("search", "權威判解檢索 (含 AutoRPA 代理)")}
        <div class="link-grid">
          <a href="https://judgment.judicial.gov.tw/FJUD/default.aspx" target="_blank" rel="noopener noreferrer" class="judgment-link-btn">
            <span>🏛️ 司法院裁判書系統 (${actName} 第${esc(art.article_no)}條)</span>${icon("external", 13)}
          </a>
          <a href="https://www-lawbank-com-tw.autorpa.lib.ccu.edu.tw:8443/" target="_blank" rel="noopener noreferrer" class="judgment-link-btn">
            <span>⚖️ 法源法律網精選裁判 (AutoRPA)</span>${icon("external", 13)}
          </a>
          <a href="https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/anglekmc/ttswebx?@0:0:1:lawkm@@0.1702332962648232" target="_blank" rel="noopener noreferrer" class="judgment-link-btn">
            <span>📚 月旦知識庫法學期刊 (AutoRPA)</span>${icon("external", 13)}
          </a>
        </div>
      </section>

      <section id="drawer-article-literature-section">${sectionHeading("book", "相關法學期刊與專論文獻 (二級法條關聯)")}
        <div id="drawer-article-literature-list" style="margin-top:0.5rem;">
          <div style="color:#71717a; font-size:0.85rem; padding:0.4rem 0;">載入關聯文獻中...</div>
        </div>
      </section>

      <section id="drawer-ccu-papers-section">${sectionHeading("book", "法源與月旦期刊專論文獻檢索")}
        <div class="card" style="padding: 0.85rem;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 0.6rem; flex-wrap:wrap; gap:0.5rem;">
            <span style="font-size:0.85rem; color:#d4d4d8;">查閱探討本條之法源與月旦期刊專論</span>
            <div style="display:flex; gap:0.4rem;">
              <button class="filter-chip drawer-open-ccu-config-btn" style="padding:0.3rem 0.75rem; font-size:0.8rem; cursor:pointer;" title="開啟 AutoRPA 連線設定視窗">
                ⚙️ 連線設定
              </button>
              <button class="filter-chip active drawer-ccu-fetch-btn" data-query="${actName} 第${esc(art.article_no)}條" style="padding:0.3rem 0.8rem; font-size:0.8rem; cursor:pointer;">
                🔍 檢索關聯論文
              </button>
            </div>
          </div>
          <div class="drawer-ccu-results-box" style="font-size:0.85rem; color:#71717a; min-height:36px;">
            點擊上方按鈕立即向法源法律網與月旦知識庫檢索關聯專論文章。
          </div>
        </div>
      </section>`;
    return html;
  }

  // ---------------- Tab 3: 內容連結 ----------------
  renderContentLinksHtml(art) {
    const rels = art.related_articles || [];
    const atts = art.attachments || [];
    return `
      <section>${sectionHeading("link", "跨法規關聯條文", `${rels.length}`)}
        ${rels.length ? `<div class="chip-row">${rels.map((r) => `<span class="ref-chip">${r}</span>`).join("")}</div>` : `<div class="empty-note">尚無關聯標註</div>`}
      </section>
      ${atts.length ? `<section>${sectionHeading("file", "相關標準與附檔", `${atts.length}`)}
        <div class="link-grid">${atts.map((a) => `<a href="${a.url}" target="_blank" rel="noopener noreferrer" class="judgment-link-btn"><span>${a.title}</span>${icon("external", 13)}</a>`).join("")}</div>
      </section>` : ""}`;
  }

  // ---------------- Tab 4: 立法理由與沿革 ----------------
  renderLegislativeHtml(art) {
    const history = art.amendment_history || [];
    if (!history.length) {
      return `
        <section>${sectionHeading("file", "制定與修正理由")}
          <div class="card">
            <div class="card-body">${art.legislative_reasons || `本條為 ${esc(this.currentAct.name)} 之現行明文規範，位於「${esc(art.chapter || "本法")}」。`}</div>
          </div>
        </section>`;
    }
    return `
      <section>${sectionHeading("file", "歷次修法理由與新舊法對照 Diff", `${history.length}`)}
        ${history.map((item) => `
          <div class="card">
            <div class="card-title accent">${item.date} · ${item.change_type || "修正"}</div>
            <div class="card-body">${item.reason}</div>
            ${item.old_content ? `
              <div class="diff-block">
                <div class="diff-row del"><span class="diff-tag">修正前</span>${item.old_content}</div>
                <div class="diff-row add"><span class="diff-tag">修正後</span>${item.new_content || art.content}</div>
              </div>` : ""}
          </div>
        `).join("")}
      </section>`;
  }

  // ---------------- Tab 5: 我的收藏 ----------------
  renderMyBookmarksHtml() {
    if (!this.bookmarks.length) {
      return `<div class="empty-state">
        <div class="empty-state-icon">${icon("bookmark", 26)}</div>
        <div class="empty-state-title">尚未收藏任何條文</div>
        <p>在條文右上角點選書籤圖示即可收藏，離線可用。</p>
      </div>`;
    }
    return `
      <section>${sectionHeading("star", "我的收藏法條庫", `${this.bookmarks.length}`)}
        ${this.bookmarks.map((b) => `
          <div class="card">
            <div class="card-title accent">${esc(b.actName)} 第 ${esc(b.articleNo)} 條 ${b.title ? `(${esc(b.title)})` : ""}</div>
            <div class="card-body">${esc(b.snippet || "")}</div>
            <div class="card-actions">
              <button class="drawer-nav-btn bookmark-jump-btn" data-act-id="${esc(b.actId)}" data-art-no="${esc(b.articleNo)}">${icon("zap", 13)} 前往</button>
              <button class="drawer-nav-btn ghost danger bookmark-delete-btn" data-act-id="${esc(b.actId)}" data-art-no="${esc(b.articleNo)}">${icon("trash", 13)} 移除</button>
            </div>
          </div>
        `).join("")}
      </section>`;
  }

  // ---------------- Fast Scrubber & Scrollspy ----------------
  buildFastScrubber(articles) {
    const scrubber = document.getElementById("fast-scrubber-index");
    if (!scrubber || window.innerWidth > 768 || articles.length < 30) return;

    const ticks = [];
    const step = Math.max(1, Math.floor(articles.length / 12));
    for (let i = 0; i < articles.length; i += step) {
      ticks.push({ idx: i, no: articles[i].article_no });
    }
    if (ticks[ticks.length - 1].idx !== articles.length - 1) {
      ticks.push({ idx: articles.length - 1, no: articles[articles.length - 1].article_no });
    }

    scrubber.innerHTML = ticks.map((t) => `<div class="scrubber-tick" data-art-no="${t.no}">${t.no}</div>`).join("");

    const bubble = document.getElementById("scrubber-bubble");
    const onTouch = (e) => {
      e.preventDefault();
      const touch = e.touches[0];
      const target = document.elementFromPoint(touch.clientX, touch.clientY);
      if (target && target.classList.contains("scrubber-tick")) {
        const no = target.dataset.artNo;
        if (bubble) {
          bubble.textContent = `第 ${no} 條`;
          bubble.classList.remove("hidden");
        }
        this.scrollToArticleCard(no, "start");
      }
    };

    scrubber.addEventListener("touchstart", onTouch);
    scrubber.addEventListener("touchmove", onTouch);
    scrubber.addEventListener("touchend", () => {
      if (bubble) bubble.classList.add("hidden");
    });
  }

  initScrollspy() {
    const list = document.getElementById("statute-stream-list");
    const chapterIndicator = document.getElementById("active-chapter-name");
    if (!list) return;

    list.addEventListener("scroll", () => {
      const cards = list.querySelectorAll(".stream-article-card");
      let visibleChapter = "";
      for (const card of cards) {
        const rect = card.getBoundingClientRect();
        if (rect.top >= 60 && rect.top <= 250) {
          visibleChapter = card.dataset.chapter;
          break;
        }
      }
      if (visibleChapter && chapterIndicator) {
        chapterIndicator.textContent = visibleChapter;
        // Sync Left TOC Active
        document.querySelectorAll("#sidebar-chapter-list .chapter-item").forEach((item) => {
          const match = item.dataset.fullChapter === visibleChapter;
          item.classList.toggle("active", match);
          if (match && !this.isTocCollapsed) {
            item.scrollIntoView({ block: "nearest", behavior: "smooth" });
          }
        });
      }
    });
  }

  initDraggableSplit() {
    const handle = document.getElementById("split-drag-handle");
    if (!handle) return;
    let isDragging = false;

    handle.addEventListener("mousedown", (e) => {
      isDragging = true;
      handle.classList.add("dragging");
      document.body.style.cursor = "col-resize";
    });

    document.addEventListener("mousemove", (e) => {
      if (!isDragging) return;
      const width = window.innerWidth - e.clientX;
      const pct = Math.max(25, Math.min(75, (width / window.innerWidth) * 100));
      document.documentElement.style.setProperty("--drawer-width", `${pct}%`);
    });

    document.addEventListener("mouseup", () => {
      if (isDragging) {
        isDragging = false;
        handle.classList.remove("dragging");
        document.body.style.cursor = "";
      }
    });
  }

  initMobileGestures() {
    const panel = document.getElementById("study-drawer-panel");
    const handle = document.getElementById("mobile-sheet-drag-handle");
    if (!panel || !handle || window.innerWidth > 768) return;

    let startY = 0, currentH = 0;
    handle.addEventListener("touchstart", (e) => {
      startY = e.touches[0].clientY;
      currentH = panel.getBoundingClientRect().height;
    });

    handle.addEventListener("touchmove", (e) => {
      const delta = startY - e.touches[0].clientY;
      const newH = currentH + delta;
      panel.style.height = `${newH}px`;
    });

    handle.addEventListener("touchend", () => {
      panel.style.height = "";
      const h = panel.getBoundingClientRect().height;
      if (h < window.innerHeight * 0.3) {
        this.closeStudyDrawer();
      } else if (h > window.innerHeight * 0.75) {
        panel.classList.add("expanded");
        panel.classList.remove("peek");
      } else {
        panel.classList.remove("expanded", "peek");
      }
    });
  }

  scrollToArticleCard(articleNo, block) {
    const card = document.getElementById(`article-card-${articleNo}`);
    if (!card) return false;
    card.scrollIntoView({ behavior: "smooth", block: block || "center" });
    return true;
  }

  async loadAndJumpArticle(articleNo) {
    if (!this.currentAct) return false;
    const exists = (this.currentAct.articles || []).some((a) => a.article_no === articleNo);
    if (!exists) return false;
    if (this.searchQuery) this.clearSearch();
    await new Promise((r) => requestAnimationFrame(r));
    this.scrollToArticleCard(articleNo);
    await this.openStudyDrawer(articleNo);
    return true;
  }

  parseArticleElements(art) {
    const content = art.content || "";
    const actName = this.currentAct.name;
    let autoSummary = `規範 ${actName} ${art.chapter ? `(${art.chapter})` : ""} 之條文規範。`;
    let behaviorType = "法定要件行為態樣";
    if (content.includes("駕駛")) behaviorType = "交通工具駕駛行為";
    let intentType = content.includes("過失") ? "故意或過失均罰" : "故意責任";
    let penaltyType = "法定效果";
    if (content.includes("有期徒刑") || content.includes("拘役")) {
      const m = content.match(/處([^，。]+)/);
      penaltyType = m ? m[1].trim() : "自由刑/罰金";
    }
    let prosecutionType = content.includes("告訴乃論") ? "告訴乃論之罪" : "公訴追訴";
    return { autoSummary, behaviorType, intentType, penaltyType, prosecutionType };
  }

  bindClearable(inputEl, clearEl, onChange) {
    if (!inputEl) return;
    const sync = () => { if (clearEl) clearEl.classList.toggle("hidden", !inputEl.value); };
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

  async copyToClipboard(text, triggerEl) {
    const original = triggerEl.innerHTML;
    try {
      await navigator.clipboard.writeText(text);
      triggerEl.innerHTML = `${icon("check", 13)}<span>已複製</span>`;
      triggerEl.classList.add("done");
    } catch (err) { triggerEl.innerHTML = `<span>失敗</span>`; }
    setTimeout(() => {
      triggerEl.innerHTML = original;
      triggerEl.classList.remove("done");
    }, 1500);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  window.legalHubApp = new LegalHubApp();
});

// Robust Global Harvest Handlers (Callable directly via onclick or event listeners)
window.handleStartHarvest = async function(resetCheckpoint = false) {
  const startBtn = document.getElementById("ccu-start-harvest-btn");
  const stopBtn = document.getElementById("ccu-stop-harvest-btn");
  const terminalBox = document.getElementById("harvest-terminal-logs");
  const configBox = document.getElementById("ccu-auth-config-box");
  const cookieInput = document.getElementById("ccu-cookie-input");

  if (startBtn) {
    startBtn.disabled = true;
    startBtn.textContent = "⏳ 正在啟動採集...";
  }

  if (terminalBox) {
    const ts = new Date().toTimeString().slice(0, 8);
    const existing = terminalBox.textContent.trim();
    terminalBox.textContent = (existing ? existing + "\n" : "") + `[${ts}] ⚡ 已發送啟動訊號，正在檢驗 AutoRPA 連線與兩階段快篩隊列...`;
    terminalBox.scrollTop = terminalBox.scrollHeight;
  }

  try {
    const actId = (window.legalHubApp && window.legalHubApp.currentActId) || "criminal_code";
    const res = await fetch("/api/ccu/harvest/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ act_id: actId, reset_checkpoint: resetCheckpoint })
    });
    const json = await res.json();
    if (!json.success) {
      if (terminalBox) {
        const ts = new Date().toTimeString().slice(0, 8);
        terminalBox.textContent += `\n[${ts}] ⚠️ 啟動受阻：${json.message || "連線未驗證"}`;
        terminalBox.scrollTop = terminalBox.scrollHeight;
      }
      alert(json.message || "啟動採集失敗");
      if (configBox && (json.message || "").includes("sessionid")) {
        configBox.style.display = "block";
        if (cookieInput) {
          cookieInput.focus();
          cookieInput.style.borderColor = "#ef4444";
          cookieInput.style.boxShadow = "0 0 12px rgba(239, 68, 68, 0.5)";
          setTimeout(() => {
            cookieInput.style.borderColor = "";
            cookieInput.style.boxShadow = "";
          }, 3500);
        }
      }
    } else {
      if (stopBtn) stopBtn.style.display = "inline-block";
      if (startBtn) startBtn.style.display = "none";
    }

    if (window.legalHubApp && window.legalHubApp.pollHarvestStatus) {
      await window.legalHubApp.pollHarvestStatus();
    }
  } catch (e) {
    if (terminalBox) {
      terminalBox.textContent += `\n[錯誤] 連線伺服器異常：${e.message}`;
    }
    alert("啟動採集出錯：" + e.message);
  } finally {
    if (startBtn) {
      startBtn.disabled = false;
      startBtn.textContent = "▶️ 啟動 / 續採";
    }
  }
};

window.handleStopHarvest = async function() {
  const stopBtn = document.getElementById("ccu-stop-harvest-btn");
  const terminalBox = document.getElementById("harvest-terminal-logs");

  if (stopBtn) {
    stopBtn.disabled = true;
    stopBtn.textContent = "⏳ 正在保存斷點...";
  }

  if (terminalBox) {
    const ts = new Date().toTimeString().slice(0, 8);
    terminalBox.textContent += `\n[${ts}] ⏹️ 正在安全保存斷點並停止採集...`;
    terminalBox.scrollTop = terminalBox.scrollHeight;
  }

  try {
    const res = await fetch("/api/ccu/harvest/stop", { method: "POST" });
    const json = await res.json();
    if (window.legalHubApp && window.legalHubApp.pollHarvestStatus) {
      await window.legalHubApp.pollHarvestStatus();
    }
  } catch (e) {
    alert("停止採集出錯：" + e.message);
  } finally {
    if (stopBtn) {
      stopBtn.disabled = false;
      stopBtn.textContent = "⏹️ 暫停保存";
    }
  }
};
