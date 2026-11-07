/**
 * Legal Hub - Professional Legal Intelligence System
 * High-Density, Split-View, Hover Citations, Scrubber, Gestures & Keyboard Navigation
 */

const ESC_MAP = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ESC_MAP[c]);
}

const UNICODE_ROMAN = ["", "Ⅰ", "Ⅱ", "Ⅲ", "Ⅳ", "Ⅴ", "Ⅵ", "Ⅶ", "Ⅷ", "Ⅸ", "Ⅹ", "Ⅺ", "Ⅻ", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX"];
function toRoman(n) {
  if (n > 0 && n < UNICODE_ROMAN.length) return UNICODE_ROMAN[n];
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

// Render article structured blocks provided directly by backend
function renderArticleBody(art, q) {
  const blocks = art && art.blocks ? art.blocks : [];
  if (!blocks.length) {
    const rawContent = (typeof art === "string") ? art : (art && art.content ? art.content : "");
    return `<div class="article-body"><div class="block-text">${linkifyArticleRefs(rawContent, q)}</div></div>`;
  }

  const html = blocks.map((b) => {
    const roman = b.roman_no ? `<span class="para-no" data-para-idx="${b.para_idx || 0}" title="第 ${b.para_idx} 項 (點擊複製此項)">${esc(b.roman_no)}</span>` : "";
    const marker = b.no_raw ? `<span class="block-marker">${esc(b.no_raw)}</span>` : "";
    const textHtml = linkifyArticleRefs(b.text || "", q);
    const hasRomanClass = b.roman_no ? "has-roman" : "";
    return `<div class="structure-block block-${esc(b.kind)} ${hasRomanClass}" data-kind="${esc(b.kind)}" data-para-idx="${b.para_idx || 0}">
      ${roman}
      <div class="block-body para-body">${marker}<span class="block-text para-text">${textHtml}</span></div>
    </div>`;
  }).join("");

  return `<div class="article-body">${html}</div>`;
}

function formatArticleCopy(art, mode = "roman", actName = "") {
  if (!art) return "";
  const labelRaw = art.label_raw || "";
  const header = `${actName} ${labelRaw} ${art.title || ""}`.replace(/\s+/g, " ").trim();

  if (mode === "plain" || !art.blocks || !art.blocks.length) {
    return header ? `${header}\n${art.content}` : art.content;
  }

  const lines = header ? [header] : [];
  const paraBlocks = art.blocks.filter((b) => b.kind === "para");
  const isMultiPara = paraBlocks.length >= 2;

  for (const b of art.blocks) {
    const kind = b.kind;
    const roman = b.roman_no || "";
    const noRaw = b.no_raw || "";
    const text = b.text || "";

    if (kind === "para") {
      if (mode === "roman") {
        const prefix = roman ? `${roman}　` : "";
        lines.push(`${prefix}${text}`);
      } else if (mode === "label") {
        const prefix = (labelRaw && isMultiPara && b.para_idx) ? `第 ${b.para_idx} 項　` : "";
        lines.push(`${prefix}${text}`);
      } else {
        lines.push(text);
      }
    } else if (kind === "item") {
      lines.push(`　　${noRaw}${text}`);
    } else if (kind === "sub") {
      lines.push(`　　　　${noRaw}${text}`);
    } else if (kind === "sub_sub") {
      lines.push(`　　　　　　${noRaw}${text}`);
    }
  }
  return lines.join("\n");
}

function hydrateIcons(root) {
  (root || document).querySelectorAll("[data-icon]").forEach((el) => {
    if (el.dataset.hydrated) return;
    el.innerHTML = icon(el.dataset.icon, parseInt(el.dataset.size || "16", 10));
    el.dataset.hydrated = "1";
  });
}

function sectionHeading(iconName, title, note, sourceInfo) {
  return `<h3 class="sub-heading" style="display:flex; justify-content:space-between; align-items:center;">
    <span style="display:flex; align-items:center; gap:6px;">${icon(iconName, 16)}<span>${title}</span>${note ? `<span class="sub-note">${note}</span>` : ""}</span>
    ${sourceInfo ? `<span style="font-size:0.75rem; color:#a1a1aa; font-weight:normal;">來源：${esc(sourceInfo)}</span>` : ""}
  </h3>`;
}


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
    this.currentActId = "";
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
    this.openTabs = [];
    this.bookmarks = this.loadBookmarks();

    this.init();
  }

  async init() {
    hydrateIcons();
    this.initTheme();
    this.initDensity();
    this.initEventListeners();
    this.bindCCUEvents();
    this.bindUpdateStatusEvents();
    this.checkBookmarksAlert();
    this.refreshCCUStatus();
    this.renderResearchTabs();
    this.renderPopularActsModal();

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
      try {
        const resp = await fetch("/api/tiers");
        const json = await resp.json();
        const tiers = json.data || [];
        if (tiers.length > 0) {
          this.currentActId = tiers[0].id;
          this.openTabs = [{ id: tiers[0].id, name: tiers[0].name }];
        }
      } catch (e) { console.warn(e); }
      if (this.currentActId) {
        await this.loadAct(this.currentActId);
      }
    }

    window.addEventListener("hashchange", async () => {
      const r = this.parseHashRoute();
      if (!r) return;
      if (r.actId && r.actId !== this.currentActId) {
        this.selectedArticleNo = null;
        await this.loadAct(r.actId);
      }
      if (r.articleNo) {
        this.scrollToArticleCard(r.articleNo);
        await this.openStudyDrawer(r.articleNo);
      }
    });

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
    const actSearchDropdown = document.getElementById("act-search-dropdown");
    let activeDropdownIdx = -1;
    let actSearchDebounce = null;

    const highlightText = (text, q) => {
      if (!q || !text) return esc(text || "");
      const idx = text.toLowerCase().indexOf(q.toLowerCase());
      if (idx === -1) return esc(text);
      const before = text.substring(0, idx);
      const match = text.substring(idx, idx + q.length);
      const after = text.substring(idx + q.length);
      return `${esc(before)}<mark class="search-hl">${esc(match)}</mark>${esc(after)}`;
    };

    const renderDropdown = (items, q) => {
      if (!actSearchDropdown) return;
      if (!items || !items.length) {
        actSearchDropdown.innerHTML = `<div class="empty-note" style="padding:0.75rem; font-size:0.8rem; color:var(--text-dim);">查無相符法規</div>`;
        actSearchDropdown.classList.remove("hidden");
        return;
      }
      activeDropdownIdx = 0;
      actSearchDropdown.innerHTML = items.slice(0, 8).map((act, idx) => `
        <button class="act-dropdown-item ${idx === 0 ? 'active' : ''}" data-act-id="${esc(act.id)}" data-act-name="${esc(act.name)}" data-idx="${idx}">
          <span class="act-dropdown-name">${highlightText(act.name, q)}</span>
          ${act.category ? `<span class="act-dropdown-cat">${esc(act.category)}</span>` : ""}
        </button>
      `).join("");
      actSearchDropdown.classList.remove("hidden");

      actSearchDropdown.querySelectorAll(".act-dropdown-item").forEach((btn) => {
        btn.addEventListener("click", () => {
          this.openResearchTab(btn.dataset.actId, btn.dataset.actName);
          actSearchDropdown.classList.add("hidden");
          actSearchInput.value = "";
          actSearchInput.blur();
        });
      });
    };

    const hideDropdown = () => {
      if (actSearchDropdown) {
        actSearchDropdown.classList.add("hidden");
        actSearchDropdown.innerHTML = "";
        activeDropdownIdx = -1;
      }
    };

    this.bindClearable(actSearchInput, document.getElementById("act-search-clear"), () => hideDropdown());

    if (actSearchInput) {
      actSearchInput.addEventListener("input", (e) => {
        const query = e.target.value.trim();
        if (actSearchDebounce) clearTimeout(actSearchDebounce);
        if (!query) {
          hideDropdown();
          return;
        }
        actSearchDebounce = setTimeout(async () => {
          try {
            const resp = await fetch(`/api/acts?q=${encodeURIComponent(query)}`);
            const json = await resp.json();
            if (json.success) {
              renderDropdown(json.data, query);
            }
          } catch (err) { console.error(err); }
        }, 120);
      });

      actSearchInput.addEventListener("keydown", async (e) => {
        const items = actSearchDropdown ? actSearchDropdown.querySelectorAll(".act-dropdown-item") : [];
        if (e.key === "ArrowDown") {
          e.preventDefault();
          if (items.length > 0) {
            activeDropdownIdx = (activeDropdownIdx + 1) % items.length;
            items.forEach((it, idx) => it.classList.toggle("active", idx === activeDropdownIdx));
            items[activeDropdownIdx].scrollIntoView({ block: "nearest" });
          }
          return;
        }
        if (e.key === "ArrowUp") {
          e.preventDefault();
          if (items.length > 0) {
            activeDropdownIdx = (activeDropdownIdx - 1 + items.length) % items.length;
            items.forEach((it, idx) => it.classList.toggle("active", idx === activeDropdownIdx));
            items[activeDropdownIdx].scrollIntoView({ block: "nearest" });
          }
          return;
        }
        if (e.key === "Escape") {
          hideDropdown();
          return;
        }
        if (e.key !== "Enter") return;

        e.preventDefault();
        const query = actSearchInput.value.trim();
        if (!query) return;

        // If dropdown item is selected
        if (items.length > 0 && activeDropdownIdx >= 0 && items[activeDropdownIdx]) {
          const sel = items[activeDropdownIdx];
          this.openResearchTab(sel.dataset.actId, sel.dataset.actName);
          hideDropdown();
          actSearchInput.blur();
          return;
        }

        try {
          const resp = await fetch(`/api/acts?q=${encodeURIComponent(query)}`);
          const json = await resp.json();
          if (json.success && json.data.length > 0) {
            const hit = json.data[0];
            this.openResearchTab(hit.id, hit.name);
            hideDropdown();
            actSearchInput.blur();
          }
        } catch (err) { console.error(err); }
      });

      document.addEventListener("click", (e) => {
        if (!e.target.closest(".nav-search")) {
          hideDropdown();
        }
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
    tabSearchInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        const firstRow = document.querySelector("#tab-search-results .act-result-row");
        if (firstRow) {
          firstRow.click();
        }
      }
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

    // Literature Reader Modal Controls
    const litReaderModal = document.getElementById("lit-reader-modal");
    const litReaderClose = document.getElementById("lit-reader-modal-close");
    const closeLitReader = () => {
      if (litReaderModal) litReaderModal.classList.add("hidden");
      const litBody = document.getElementById("lit-reader-modal-body");
      if (litBody) litBody.innerHTML = "";
    };
    if (litReaderClose && litReaderModal) {
      litReaderClose.addEventListener("click", closeLitReader);
      litReaderModal.addEventListener("click", (e) => {
        if (e.target === litReaderModal) closeLitReader();
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
      
      // Only process shortcuts when NO modifier keys are pressed (prevent intercepting Ctrl+F / Cmd+F)
      if (!e.ctrlKey && !e.metaKey && !e.altKey) {
        if (e.key === "/" || e.key === "f") {
          e.preventDefault();
          const s = document.getElementById("search-input");
          if (s) { s.focus(); s.select(); }
        } else if (e.key === "ArrowLeft" || e.key === "[") {
          this.navigateAdjacentArticle(-1);
        } else if (e.key === "ArrowRight" || e.key === "]") {
          this.navigateAdjacentArticle(1);
        }
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
      quickTags = [
        `${actName}第${artNo}條`,
        `${actName} 第${artNo}條 專論評釋`,
        `第${artNo}條 構成要件爭議`,
        `${actName} 最新期刊`
      ];
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
      window.currentCCUStatus = data.authenticated ? 'authenticated' : 'unauthenticated';
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
                      <div style="font-weight:700; font-size:0.9rem;"><a href="javascript:;" class="lit-reader-trigger" data-lit-id="${item.id || ''}" data-lit-title="${esc(item.title)}" style="color:#60a5fa; text-decoration:none; cursor:pointer;">${esc(item.title)}</a></div>
                      <span class="badge" style="background:${badgeBg}; color:${badgeColor}; border:1px solid ${badgeBorder}; font-size:0.75rem; padding:1px 6px; border-radius:4px; flex-shrink:0;">${badgeLabel}</span>
                    </div>
                    <div style="font-size:0.75rem; color:#8e8e93; margin-top:0.35rem; display:flex; justify-content:space-between; align-items:center;">
                      <span>來源：${esc(item.source)}</span>
                      <button type="button" class="filter-chip lit-reader-trigger" data-lit-id="${item.id || ''}" data-lit-title="${esc(item.title)}" style="padding:0.25rem 0.65rem; font-size:0.75rem; cursor:pointer; background:#18181b; border:1px solid #3f3f46; color:#e4e4e7; border-radius:4px;">📖 全文閱覽</button>
                    </div>
                  </div>
                `}).join('')}
              </div>
            `;
            resultsContainer.querySelectorAll(".lit-reader-trigger").forEach(el => {
              el.addEventListener("click", (e) => {
                e.preventDefault();
                const lid = el.dataset.litId;
                const title = el.dataset.litTitle;
                this.openLiteratureReader(lid, title);
              });
            });
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
  async renderPopularActsModal() {
    const grid = document.getElementById("popular-acts-grid");
    try {
      const resp = await fetch("/api/tiers");
      const json = await resp.json();
      const popular = json.data || [];
      grid.innerHTML = popular
        .map((act) => `<button class="popular-act-chip" data-act-id="${esc(act.id)}" data-act-name="${esc(act.name)}">${esc(act.name)}</button>`)
        .join("");
    } catch (e) {
      console.warn("Failed to load tiers modal", e);
    }
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
    const highlight = (text, q) => {
      if (!q || !text) return esc(text || "");
      const idx = text.toLowerCase().indexOf(q.toLowerCase());
      if (idx === -1) return esc(text);
      const before = text.substring(0, idx);
      const match = text.substring(idx, idx + q.length);
      const after = text.substring(idx + q.length);
      return `${esc(before)}<mark class="search-hl">${esc(match)}</mark>${esc(after)}`;
    };
    try {
      const resp = await fetch(`/api/acts?q=${encodeURIComponent(query)}`);
      const json = await resp.json();
      const list = json.success ? json.data.slice(0, 12) : [];
      box.innerHTML = list.length
        ? list
            .map(
              (act) => `<button class="act-result-row" data-act-id="${esc(act.id)}" data-act-name="${esc(act.name)}">
                <span>${highlight(act.name, query)}</span><span class="act-result-cat">${esc(act.category || "")}</span></button>`
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
      this.currentActId = actId;
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

    const chapterIndicator = document.getElementById("active-chapter-name");
    if (chapterIndicator && this.currentAct) {
      const firstArt = (this.currentAct.articles || [])[0];
      chapterIndicator.textContent = (firstArt && firstArt.chapter) ? firstArt.chapter : this.currentAct.name;
    }

    const meta = document.getElementById("act-meta-inline");
    if (meta && this.currentAct) {
      const parts = [];
      const isAbolished = this.currentAct.status === "abolished" || 
                          (this.currentAct.category || "").startsWith("廢止法規") || 
                          this.currentAct.abandon_note === "廢";
      if (this.currentAct.category) {
        parts.push(`法規類別：${this.currentAct.category}`);
      }
      if (this.currentAct.last_modified) {
        if (isAbolished) {
          parts.push(`廢止日期：${this.currentAct.last_modified}`);
        } else {
          parts.push(`修正日期：${this.currentAct.last_modified}`);
        }
      }
      if (this.currentAct.effective_note) {
        parts.push(`【${this.currentAct.effective_note}】`);
      }
      meta.textContent = parts.length ? `(${parts.join(" · ")})` : "";
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
    // Render official foreword if present (unbadged plain text block before articles)
    if (this.currentAct && this.currentAct.foreword && !q) {
      html += `
        <div class="act-foreword-card stream-article-card" id="act-foreword-card" style="border-left: 3px solid #6366f1; background: rgba(99, 102, 241, 0.05); margin-bottom: 1.25rem;">
          <div class="article-card-content" style="white-space: pre-wrap; line-height: 1.8; color: #e4e4e7;">${esc(this.currentAct.foreword)}</div>
        </div>`;
    }

    let lastChapter = "";
    articles.forEach((art) => {
      if (art.chapter && art.chapter !== lastChapter && !q) {
        lastChapter = art.chapter;
        html += `
          <div class="stream-chapter-divider" style="padding: 1rem 0.5rem 0.5rem 0.5rem; font-weight: 700; font-size: 0.95rem; color: #a1a1aa; border-bottom: 1px solid rgba(255,255,255,0.08); margin: 1.5rem 0 1rem 0;">
            ${esc(art.chapter)}
          </div>`;
      }
      const marked = this.isBookmarked(this.currentActId, art.article_no);
      const artLabelHtml = art.label_raw ? `<span>${hl(art.label_raw, q)}</span>` : "";
      html += `
        <article class="stream-article-card ${this.selectedArticleNo === art.article_no ? 'active' : ''}" id="article-card-${esc(art.article_no)}" data-article-no="${esc(art.article_no)}" data-chapter="${esc(art.chapter || '')}">
          <div class="article-card-header">
            <div class="article-card-no">
              ${artLabelHtml}
              ${art.title ? `<span class="article-card-title">${hl(art.title, q)}</span>` : ""}
              <span class="card-bookmark-mark ${marked ? "" : "hidden"}" title="已收藏">${icon("bookmark-filled", 13)}</span>
            </div>
            <div class="article-card-actions">
              ${(art.lis_reasons && art.lis_reasons.length > 0) ? `<span class="article-history-badge" style="font-size:0.75rem; padding:2px 6px; background:rgba(59,130,246,0.15); color:#60a5fa; border:1px solid rgba(59,130,246,0.3); border-radius:4px; margin-right:6px;">沿革 ${art.lis_reasons.length} 版</span>` : ""}
              <button class="article-study-btn" data-article-no="${esc(art.article_no)}">研析</button>
            </div>
          </div>
          <div class="article-card-content">${renderArticleBody(art, q)}</div>
        </article>`;
    });

    list.innerHTML = html;

    // Click anywhere on card (or study button) to inspect in Split-view
    list.querySelectorAll(".stream-article-card").forEach((card) => {
      card.addEventListener("click", (e) => {
        if (e.target.closest(".article-ref-link")) return; // Don't trigger drawer if clicking citation popover link
        if (e.target.closest(".para-no")) {
          e.stopPropagation();
          const pEl = e.target.closest(".para-no");
          const pBlock = pEl.closest(".structure-block");
          const paraText = pBlock ? (pBlock.querySelector(".block-text")?.innerText || "") : "";
          const roman = pEl.innerText.trim();
          const artObj = (this.currentAct?.articles || []).find(a => a.article_no === card.dataset.articleNo);
          const label = artObj?.label_raw ? ` ${artObj.label_raw}` : "";
          const singleText = `${this.currentAct ? this.currentAct.name : ""}${label} ${roman}　${paraText}`.trim();
          this.copyToClipboard(singleText, pEl);
          return;
        }
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
    const nAmend = (art.lis_reasons && art.lis_reasons.length) ? art.lis_reasons.length : (art.amendment_history || []).length;

    const tabBtn = (id, iconName, label, count) =>
      `<button class="drawer-tab-btn ${this.activeTab === id ? "active" : ""}" data-tab="${id}">${icon(iconName, 15)}<span>${label}</span>${count ? `<span class="tab-count">${count}</span>` : ""}</button>`;

    // Consistent Drawer Structure: Fixed Top Article Quote Box, followed by Sticky Tabs & Analysis
    scrollBody.innerHTML = `
      <section class="drawer-hero-section">
        <h1 class="drawer-hero-title">${esc(this.currentAct.name)}${art.label_raw ? ` ${esc(art.label_raw)}` : ''}</h1>
        ${art.title ? `<div class="drawer-hero-subtitle">${esc(art.title)}</div>` : ""}
        <div class="drawer-hero-article-box">
          <div class="article-box-copy-group" style="display:flex; gap:6px; align-items:center; position:absolute; top:0.75rem; right:0.75rem;">
            <button class="article-box-copy-action" id="drawer-copy-roman-btn" title="複製條文（項冠羅馬數字 Ⅰ、Ⅱ）">${icon("copy", 13)}<span>複製 (羅馬項號)</span></button>
            <button class="article-box-copy-action" id="drawer-copy-label-btn" title="複製條文（項冠「第 1 項」標籤）">${icon("copy", 13)}<span>複製 (項標籤)</span></button>
            <button class="article-box-copy-action" id="drawer-copy-plain-btn" title="複製條文（官方純文字）">${icon("file", 13)}<span>複製 (純文字)</span></button>
          </div>
          ${renderArticleBody(art, "")}
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
          <span>${esc(art.label_raw || art.article_no)}</span>${icon("external", 13)}
        </button>
        <button class="drawer-nav-btn" id="drawer-next-btn"><span>下一條</span>${icon("arrowRight", 14)}</button>
      </footer>`;

    scrollBody.scrollTop = 0;

    const copyRomanBtn = scrollBody.querySelector("#drawer-copy-roman-btn");
    if (copyRomanBtn) {
      copyRomanBtn.addEventListener("click", (e) => {
        const full = formatArticleCopy(art, "roman", this.currentAct.name);
        this.copyToClipboard(full, e.currentTarget);
      });
    }

    const copyLabelBtn = scrollBody.querySelector("#drawer-copy-label-btn");
    if (copyLabelBtn) {
      copyLabelBtn.addEventListener("click", (e) => {
        const full = formatArticleCopy(art, "label", this.currentAct.name);
        this.copyToClipboard(full, e.currentTarget);
      });
    }

    const copyPlainBtn = scrollBody.querySelector("#drawer-copy-plain-btn");
    if (copyPlainBtn) {
      copyPlainBtn.addEventListener("click", (e) => {
        const full = formatArticleCopy(art, "plain", this.currentAct.name);
        this.copyToClipboard(full, e.currentTarget);
      });
    }

    // Paragraph-level Roman numeral click-to-copy
    scrollBody.querySelectorAll(".para-no").forEach((el) => {
      el.addEventListener("click", (e) => {
        e.stopPropagation();
        const pBlock = el.closest(".structure-block");
        const paraText = pBlock ? (pBlock.querySelector(".block-text")?.innerText || "") : "";
        const roman = el.innerText.trim();
        const label = art.label_raw ? ` ${art.label_raw}` : "";
        const singleText = `${this.currentAct ? this.currentAct.name : ""}${label} ${roman}　${paraText}`.trim();
        this.copyToClipboard(singleText, el);
      });
    });
    const permalinkBtn = scrollBody.querySelector("#drawer-permalink-btn");
    if (permalinkBtn) {
      permalinkBtn.addEventListener("click", () => {
        window.open(`${window.location.origin}${window.location.pathname}#/act/${this.currentActId}/article/${art.article_no}`, "_blank");
      });
    }

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
                <button type="button" class="filter-chip active drawer-lit-read-btn" data-lit-id="${lit.id}" data-lit-title="${esc(lit.title)}" style="padding:0.25rem 0.65rem; font-size:0.75rem; cursor:pointer; background:#2563eb; color:#fff; border:none; border-radius:4px;">📄 開啟全文閱讀</button>
              </div>
            </div>
          `).join('');
          litContainer.querySelectorAll(".drawer-lit-read-btn").forEach(btn => {
            btn.addEventListener("click", () => {
              const lid = btn.dataset.litId;
              const title = btn.dataset.litTitle;
              this.openLiteratureReader(lid, title);
            });
          });
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
    let html = "";
    if (art.stale === 1 || art.stale === true) {
      const modDate = (this.currentAct && this.currentAct.last_modified) ? `於 ${esc(this.currentAct.last_modified)} ` : "";
      html += `
        <div class="stale-alert-banner" style="background:rgba(234, 179, 8, 0.12); border:1px solid rgba(234, 179, 8, 0.4); color:#fde047; padding:0.65rem 0.85rem; border-radius:6px; margin-bottom:1rem; font-size:0.85rem; display:flex; align-items:center; gap:0.5rem;">
          <span style="font-size:1.1rem;">⚠️</span>
          <span>本條已${modDate}修正，下列法律人解析可能對應修正前條文。</span>
        </div>`;
    }
    const sourceInfo = (art.source === "lawplayer" && art.source_url) 
      ? `法律人 (${(art.fetched_at || "").substring(0, 10)})` 
      : (art.source ? `${art.source} (${(art.fetched_at || "").substring(0, 10)})` : "");

    if (art.summary && art.source) {
      const summaryTitle = art.source === "lawplayer" ? "重點摘要 (法律人)" : "重點摘要";
      html += `
        <div class="callout-box">
          <div class="callout-title" style="display:flex; justify-content:space-between; align-items:center;">
            <span style="display:flex; align-items:center; gap:6px;">${icon("lightbulb", 15)}<span>${summaryTitle}</span></span>
            ${sourceInfo ? `<span style="font-size:0.75rem; color:#a1a1aa; font-weight:normal;">來源：${esc(sourceInfo)}</span>` : ""}
          </div>
          <div style="margin-top:0.4rem; line-height:1.6;">${esc(art.summary)}</div>
        </div>`;
    }

    const qas = (art.source && art.vernacular_qa && art.vernacular_qa.length) ? art.vernacular_qa : [];
    if (qas.length) {
      const qaTitle = art.source === "lawplayer" ? "白話與實務解讀 (法律人)" : "白話與實務解讀";
      html += `<section>${sectionHeading("book", qaTitle, `${qas.length}`, sourceInfo)}
        ${qas.map((item) => `
          <div class="card">
            <div class="card-title">${esc(item.question || item.q || "")}</div>
            <div class="card-body" style="white-space: pre-wrap; line-height: 1.65;">${esc(item.answer || item.a || "")}</div>
          </div>
        `).join("")}
      </section>`;
    }

    if (art.legal_definition && art.source) {
      const deepTitle = art.source === "lawplayer" ? "深度解讀 (法律人)" : "深度解讀";
      html += `<section>${sectionHeading("file", deepTitle, null, sourceInfo)}
        <div class="card">
          <div class="card-body" style="white-space: pre-wrap; line-height: 1.7; font-size: 0.95rem; color: #d0d0d8;">${esc(art.legal_definition)}</div>
        </div>
      </section>`;
    }

    if (art.source === "lawplayer" && art.source_url) {
      html += `<section>${sectionHeading("branch", "法條流程圖", null, sourceInfo)}
        <div class="card" style="padding: 0.85rem; display:flex; justify-content:space-between; align-items:center;">
          <span style="font-size:0.88rem; color:#d4d4d8;">本條於法律人平台備有流程圖與進階對照分析</span>
          <a href="${esc(art.source_url)}" target="_blank" rel="noopener noreferrer" class="filter-chip active" style="text-decoration:none; display:inline-flex; align-items:center; gap:4px; padding:0.35rem 0.75rem;">
            在法律人查看 ↗
          </a>
        </div>
      </section>`;
    }

    if (!html) {
      html = `<div style="padding:1.5rem 0.5rem; text-align:center; color:#71717a; font-size:0.9rem;">
        此條尚無外部解析資料
      </div>`;
    }

    return html;
  }

  // ---------------- Tab 2: 實務見解 (Dedicated Tab) ----------------
  renderInsightsHtml(art) {
    const insights = (art.source && art.practical_insights) ? art.practical_insights : [];
    const letters = (art.source && art.official_letters) ? art.official_letters : [];
    const actName = esc(this.currentAct.name);
    const sourceInfo = (art.source === "lawplayer" && art.source_url) 
      ? `法律人 (${(art.fetched_at || "").substring(0, 10)})` 
      : (art.source ? `${art.source} (${(art.fetched_at || "").substring(0, 10)})` : "");

    let html = "";

    if (insights.length) {
      const insightHeading = (art.source === "lawplayer") ? "裁判書與重要實務見解 (法律人)" : "裁判書與重要實務見解";
      html += `<section>${sectionHeading("gavel", insightHeading, `${insights.length}`, sourceInfo)}
        ${insights.filter(ins => ins.ref).map((ins) => `
          <div class="card judgment-card">
            <div class="card-title accent">${ins.court ? `${esc(ins.court)} · ` : ""}${esc(ins.ref || "")}</div>
            <div class="card-body" style="line-height: 1.6;">${esc(ins.summary || "")}</div>
            ${ins.url ? `<div style="margin-top:0.35rem;"><a href="${esc(ins.url)}" target="_blank" rel="noopener noreferrer" style="font-size:0.8rem; color:#60a5fa; text-decoration:none;">查看裁判原文 ↗</a></div>` : ""}
          </div>
        `).join("")}
      </section>`;
    }

    if (letters.length) {
      const letterHeading = (art.source === "lawplayer") ? "相關函釋 (法律人)" : "相關函釋";
      html += `
        <section>${sectionHeading("book", letterHeading, `${letters.length}`, sourceInfo)}
          ${letters.filter(letItem => letItem.ref || letItem.org || letItem.summary || letItem.content).map((letItem) => {
            const titleParts = [letItem.org, letItem.ref, letItem.date].filter(Boolean);
            const titleText = titleParts.map(p => esc(p)).join(" · ");
            return `
            <div class="card">
              ${titleText ? `<div class="card-title accent">${titleText}</div>` : ""}
              <div class="card-body" style="line-height: 1.6; white-space: pre-wrap;">${esc(letItem.summary || letItem.content || "")}</div>
              ${letItem.url ? `<div style="margin-top:0.35rem;"><a href="${esc(letItem.url)}" target="_blank" rel="noopener noreferrer" style="font-size:0.8rem; color:#60a5fa; text-decoration:none;">查看函釋原文 ↗</a></div>` : ""}
            </div>`;
          }).join("")}
        </section>`;
    }

    if (!insights.length && !letters.length) {
      html += `<div style="padding:1.5rem 0.5rem; text-align:center; color:#71717a; font-size:0.9rem;">
        此條尚無實務見解資料
      </div>`;
    }

    const ccuAuth = window.currentCCUStatus === 'authenticated';
    html += `
      <section>${sectionHeading("search", "權威判解檢索 (含 AutoRPA 代理)")}
        <div class="link-grid">
          <a href="https://judgment.judicial.gov.tw/FJUD/default.aspx" target="_blank" rel="noopener noreferrer" class="judgment-link-btn">
            <span>🏛️ 司法院裁判書系統 (${actName} 第${esc(art.article_no)}條)</span>${icon("external", 13)}
          </a>
          ${ccuAuth ? `
            <a href="https://www-lawbank-com-tw.autorpa.lib.ccu.edu.tw:8443/" target="_blank" rel="noopener noreferrer" class="judgment-link-btn">
              <span>⚖️ 法源法律網 (中正代理，需登入)</span>${icon("external", 13)}
            </a>
            <a href="https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/anglekmc/ttswebx?@0:0:1:lawkm@@0.1702332962648232" target="_blank" rel="noopener noreferrer" class="judgment-link-btn">
              <span>📚 月旦知識庫 (中正代理，需登入)</span>${icon("external", 13)}
            </a>
          ` : ""}
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
    const rels = (art.source && art.related_articles) ? art.related_articles : [];
    const atts = (art.source && art.attachments) ? art.attachments : [];
    const sourceInfo = (art.source === "lawplayer" && art.source_url) 
      ? `法律人 (${(art.fetched_at || "").substring(0, 10)})` 
      : (art.source ? `${art.source} (${(art.fetched_at || "").substring(0, 10)})` : "");

    let html = "";
    if (rels.length) {
      html += `<section>${sectionHeading("link", "跨法規關聯條文", `${rels.length}`, sourceInfo)}
        <div class="chip-row">${rels.map((r) => `<span class="ref-chip">${esc(r)}</span>`).join("")}</div>
      </section>`;
    }
    if (atts.length) {
      html += `<section>${sectionHeading("file", "相關標準與附檔", `${atts.length}`, sourceInfo)}
        <div class="link-grid">${atts.map((a) => `<a href="${esc(a.url)}" target="_blank" rel="noopener noreferrer" class="judgment-link-btn"><span>${esc(a.title)}</span>${icon("external", 13)}</a>`).join("")}</div>
      </section>`;
    }
    if (!html) {
      html = `<div style="padding:1.5rem 0.5rem; text-align:center; color:#71717a; font-size:0.9rem;">
        此條尚無外部解析資料
      </div>`;
    }
    return html;
  }

  // ---------------- Tab 4: 立法理由與沿革 ----------------
  renderLegislativeHtml(art) {
    const lisReasons = art.lis_reasons || [];
    const lisComp = art.lis_comparison || [];

    if (lisReasons.length > 0 || lisComp.length > 0) {
      const fetchedAt = (lisReasons[0] && lisReasons[0].fetched_at) || (lisComp[0] && lisComp[0].fetched_at) || "";
      const sourceDateStr = fetchedAt ? fetchedAt.substring(0, 10) : "";
      const sourceLabel = sourceDateStr ? `立法院法律系統 (抓取於 ${sourceDateStr})` : "立法院法律系統";

      const formatRoc = (rawDate) => {
        if (!rawDate) return "";
        const s = String(rawDate).trim();
        if (s.length === 7) {
          const y = parseInt(s.substring(0, 3), 10);
          const m = parseInt(s.substring(3, 5), 10);
          const d = parseInt(s.substring(5, 7), 10);
          return `民國 ${y} 年 ${m} 月 ${d} 日`;
        }
        return s;
      };

      let compHtml = "";
      if (lisComp.length > 0) {
        compHtml = lisComp.map((c) => {
          const newDateStr = formatRoc(c.new_version_date);
          const oldDateStr = formatRoc(c.old_version_date);
          const subTitle = oldDateStr ? ` (修正前：${oldDateStr})` : "";
          const actionText = c.action_type ? c.action_type : "";
          const title = c.date_label_raw ? `${c.date_label_raw} 對照表${subTitle}` : `${newDateStr} ${actionText} 對照表${subTitle}`;
          
          let tableRowsHtml = "";
          if (c.table_data && Array.isArray(c.table_data) && c.table_data.length > 0) {
            tableRowsHtml = `
              <div style="overflow-x:auto; margin:0.75rem 0;">
                <table style="width:100%; border-collapse:collapse; border:1px solid #3f3f46; font-size:0.875rem;">
                  <tbody>
                    ${c.table_data.map((row) => `
                      <tr style="border-bottom:1px solid #27272a;">
                        ${row.map((cell, idx) => `
                          <td style="padding:8px 12px; border-right:1px solid #27272a; vertical-align:top; ${idx === 0 ? 'width:120px; font-weight:600; color:#a1a1aa;' : ''}">
                            ${esc(cell).replace(/\n/g, '<br>')}
                          </td>
                        `).join("")}
                      </tr>
                    `).join("")}
                  </tbody>
                </table>
              </div>`;
          }

          const reasonBody = c.reason ? `<div class="card-body" style="white-space:pre-wrap; margin-top:0.5rem;"><strong style="color:#a1a1aa;">修正理由：</strong>\n${esc(c.reason)}</div>` : "";

          return `
            <div class="card" style="margin-bottom:1.25rem;">
              <div class="card-title accent">${esc(title)}</div>
              ${tableRowsHtml}
              ${reasonBody}
            </div>`;
        }).join("");
      }

      let reasonsHtml = "";
      if (lisReasons.length > 0) {
        reasonsHtml = lisReasons.map((v) => {
          const dateStr = formatRoc(v.version_date);
          const actionText = v.action_type ? v.action_type : "";
          const title = v.date_label_raw ? v.date_label_raw : `${dateStr} ${actionText}`;
          return `
            <div class="card" style="margin-bottom:1rem;">
              <div class="card-title accent">${esc(title)}</div>
              <div class="card-body" style="white-space:pre-wrap;">${esc(v.reason)}</div>
            </div>`;
        }).join("");
      }

      const countStr = String(lisReasons.length);
      return `
        <section>
          ${sectionHeading("file", "立法理由與沿革 (立法院法律系統)", countStr, sourceLabel)}
          ${compHtml}
          ${reasonsHtml}
        </section>`;
    }

    return `<div style="padding:1.5rem 0.5rem; text-align:center; color:#71717a; font-size:0.9rem;">
      立法院法律系統無此條資料
    </div>`;
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
          <div class="card judgment-card">
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

  openLiteratureReader(litId, title) {
    const modal = document.getElementById("lit-reader-modal");
    const modalTitle = document.getElementById("lit-reader-modal-title");
    const modalBody = document.getElementById("lit-reader-modal-body");
    const openTabBtn = document.getElementById("lit-reader-open-tab");
    if (!modal || !modalBody) return;

    if (modalTitle) modalTitle.textContent = title ? `📄 ${title}` : "論文全文閱讀器";
    if (openTabBtn) {
      openTabBtn.style.display = "none";
      openTabBtn.href = "#";
    }

    modal.classList.remove("hidden");
    modalBody.innerHTML = `
      <div style="padding: 3.5rem 1.5rem; text-align: center; color: #a1a1aa; height: 100%; display: flex; flex-direction: column; justify-content: center; align-items: center;">
        <div style="font-size: 2.2rem; margin-bottom: 0.75rem;">⏳</div>
        <div style="font-size: 1rem; font-weight: 600; color: #e4e4e7;">正在調閱論文全文...</div>
        <div style="font-size: 0.82rem; color: #71717a; margin-top: 0.35rem;">透過中正校外連線 (AutoRPA) 授權代理即時連線中</div>
      </div>
    `;

    if (!litId) {
      modalBody.innerHTML = `
        <div style="padding: 3rem 1.5rem; text-align: center; color: #f87171;">
          <div style="font-size: 2rem; margin-bottom: 0.5rem;">⚠️</div>
          <div>未指定論文編號，無法調閱全文。</div>
        </div>
      `;
      return;
    }

    const readUrl = `/api/literature/${encodeURIComponent(litId)}/read`;
    fetch(readUrl)
      .then(async (res) => {
        if (res.status === 200) {
          const contentType = res.headers.get("content-type") || "";
          if (contentType.includes("application/pdf")) {
            if (openTabBtn) {
              openTabBtn.href = readUrl;
              openTabBtn.style.display = "inline-block";
            }
            modalBody.innerHTML = `
              <iframe src="${readUrl}" style="width: 100%; height: 100%; border: none; background: #27272a;" title="${esc(title || '文獻全文')}"></iframe>
            `;
            return;
          }
        }

        let errData = {};
        try {
          errData = await res.json();
        } catch (_) {}

        if (res.status === 401 || errData.error === "session_expired" || errData.error === "not_authenticated") {
          modalBody.innerHTML = `
            <div style="max-width: 580px; margin: auto; padding: 2rem; background: #111115; border: 1px solid #dc2626; border-radius: 10px; box-shadow: 0 10px 30px rgba(0,0,0,0.6); text-align: center;">
              <div style="font-size: 2.4rem; margin-bottom: 0.6rem;">🔒</div>
              <h4 style="color: #f87171; font-size: 1.05rem; font-weight: 700; margin-bottom: 0.5rem;">中正 AutoRPA 代理通行證已過期</h4>
              <p style="color: #a1a1aa; font-size: 0.85rem; line-height: 1.6; margin-bottom: 1.25rem;">
                中正大學校外連線認證 (AutoRPA) 具備時效保護（通常閒置 20-30 分鐘自動失效）。請貼上最新的 Session Cookie 或 cURL，即可立即續期並閱讀全文。
              </p>
              <textarea id="lit-reader-renew-cookie" placeholder="請在此貼上最新中正 AutoRPA Cookie (包含 flysheet-proxy) 或完整 cURL..." style="width: 100%; height: 95px; background: #18181b; border: 1px solid #3f3f46; color: #fafafa; border-radius: 6px; padding: 0.6rem; font-size: 0.8rem; font-family: monospace; resize: none; margin-bottom: 0.85rem; box-sizing: border-box;"></textarea>
              <div style="display: flex; justify-content: center; gap: 0.75rem;">
                <button type="button" id="lit-reader-renew-submit" class="primary-btn" style="padding: 0.45rem 1.4rem; font-size: 0.88rem; cursor: pointer; background: #2563eb; color: #fff; border: none; border-radius: 6px; font-weight: 600;">🔄 續期通行證並開啟全文</button>
              </div>
              <div id="lit-reader-renew-msg" style="margin-top: 0.65rem; font-size: 0.8rem; display: none;"></div>
            </div>
          `;

          const submitBtn = modalBody.querySelector("#lit-reader-renew-submit");
          const cookieInput = modalBody.querySelector("#lit-reader-renew-cookie");
          const renewMsg = modalBody.querySelector("#lit-reader-renew-msg");

          if (submitBtn && cookieInput) {
            submitBtn.addEventListener("click", async () => {
              const raw = cookieInput.value.trim();
              if (!raw) {
                if (renewMsg) {
                  renewMsg.style.display = "block";
                  renewMsg.style.color = "#ef4444";
                  renewMsg.textContent = "請輸入有效的 Cookie 或 cURL。";
                }
                return;
              }
              submitBtn.disabled = true;
              submitBtn.textContent = "驗證續期中...";
              try {
                const sRes = await fetch("/api/ccu/session", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ cookies: raw })
                });
                const sJson = await sRes.json();
                if (sJson.success && sJson.data && sJson.data.authenticated) {
                  if (renewMsg) {
                    renewMsg.style.display = "block";
                    renewMsg.style.color = "#22c55e";
                    renewMsg.textContent = "✓ 憑證續期成功！即刻重新調閱全文...";
                  }
                  setTimeout(() => {
                    this.openLiteratureReader(litId, title);
                  }, 800);
                } else {
                  throw new Error(sJson.message || "憑證無效或仍未通過認證");
                }
              } catch (err) {
                submitBtn.disabled = false;
                submitBtn.textContent = "🔄 續期通行證並開啟全文";
                if (renewMsg) {
                  renewMsg.style.display = "block";
                  renewMsg.style.color = "#ef4444";
                  renewMsg.textContent = `續期失敗：${err.message}`;
                }
              }
            });
          }
          return;
        }

        const mRes = await fetch(`/api/literature/${encodeURIComponent(litId)}`);
        const mJson = await mRes.json();
        const lit = mJson.data || {};

        modalBody.innerHTML = `
          <div style="padding: 2rem 2.5rem; overflow-y: auto; max-width: 800px; margin: 0 auto; color: #e4e4e7;">
            <div style="font-size: 1.3rem; font-weight: 700; color: #60a5fa; margin-bottom: 0.5rem; line-height: 1.4;">
              ${esc(lit.title || title)}
            </div>
            ${lit.subtitle ? `<div style="font-size: 1rem; color: #a1a1aa; margin-bottom: 0.75rem;">${esc(lit.subtitle)}</div>` : ''}
            
            <div style="display: flex; flex-wrap: wrap; gap: 0.75rem; background: #121216; padding: 0.85rem 1.1rem; border-radius: 8px; border: 1px solid #27272a; margin-bottom: 1.5rem; font-size: 0.85rem;">
              <div>👤 <b>作者：</b>${esc(lit.author || "")}${lit.author_affiliation ? ` (${esc(lit.author_affiliation)})` : ''}</div>
              <div>📚 <b>期刊：</b>${esc(lit.journal_name || "")}</div>
              <div>📅 <b>出刊：</b>${esc(lit.pub_date || String(lit.pub_year || ''))}</div>
              ${lit.volume || lit.issue ? `<div>🔖 <b>卷期：</b>${esc(lit.volume || '')} ${esc(lit.issue || '')}</div>` : ''}
              ${lit.pages ? `<div>📄 <b>頁碼：</b>p. ${esc(lit.pages)}</div>` : ''}
            </div>

            ${lit.abstract ? `
              <div style="margin-bottom: 1.5rem;">
                <div style="font-size: 0.92rem; font-weight: 700; color: #fbbf24; margin-bottom: 0.45rem;">【中文摘要】</div>
                <div style="font-size: 0.88rem; line-height: 1.75; color: #d4d4d8; background: #18181b; padding: 1rem 1.25rem; border-radius: 6px; border: 1px solid #2e2e36;">
                  ${esc(lit.abstract)}
                </div>
              </div>
            ` : ''}

            ${lit.keywords && lit.keywords.length ? `
              <div style="margin-bottom: 1.5rem;">
                <div style="font-size: 0.92rem; font-weight: 700; color: #60a5fa; margin-bottom: 0.45rem;">【關鍵詞】</div>
                <div style="display: flex; flex-wrap: wrap; gap: 0.45rem;">
                  ${lit.keywords.map(kw => `<span class="filter-chip" style="font-size:0.8rem; padding:0.25rem 0.6rem;"># ${esc(kw)}</span>`).join('')}
                </div>
              </div>
            ` : ''}

            <div style="margin-top: 1.5rem; padding: 1rem; background: #18181b; border: 1px dashed #3f3f46; border-radius: 8px; font-size: 0.82rem; color: #a1a1aa; text-align: center;">
              ℹ️ 本篇論文目次與索引已完整納入系統。若需下載線上專論 PDF 原檔，請確保中正 AutoRPA 代理通行證處於有效授權連線狀態。
            </div>
          </div>
        `;
      })
      .catch((err) => {
        modalBody.innerHTML = `
          <div style="padding: 3rem 1.5rem; text-align: center; color: #ef4444;">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">⚠️</div>
            <div style="font-size: 0.95rem; font-weight: 600;">連線失敗：${esc(err.message)}</div>
          </div>
        `;
      });
  }

  bindUpdateStatusEvents() {
    const btn = document.getElementById("update-status-btn");
    const modal = document.getElementById("update-status-modal");
    const closeBtn = document.getElementById("update-status-modal-close");
    const alertClose = document.getElementById("bookmark-alert-close");
    const expBtn = document.getElementById("export-bookmarks-btn");
    const impInput = document.getElementById("import-bookmarks-file");

    if (btn) {
      btn.addEventListener("click", () => this.openUpdateStatusModal());
    }
    if (closeBtn && modal) {
      closeBtn.addEventListener("click", () => modal.classList.add("hidden"));
    }
    if (alertClose) {
      alertClose.addEventListener("click", () => {
        const banner = document.getElementById("bookmark-alert-banner");
        if (banner) banner.classList.add("hidden");
      });
    }
    if (expBtn) {
      expBtn.addEventListener("click", () => this.exportBookmarks());
    }
    if (impInput) {
      impInput.addEventListener("change", (e) => this.importBookmarks(e));
    }
  }

  async openUpdateStatusModal() {
    const modal = document.getElementById("update-status-modal");
    if (!modal) return;
    modal.classList.remove("hidden");

    const sourcesGrid = document.getElementById("update-sources-grid");
    const changesList = document.getElementById("recent-changes-list");
    const pendingList = document.getElementById("pending-items-list");

    if (sourcesGrid) sourcesGrid.innerHTML = `<div style="color:#a1a1aa; font-size:0.85rem;">載入中...</div>`;
    if (changesList) changesList.innerHTML = `<div style="color:#a1a1aa; font-size:0.85rem;">載入中...</div>`;
    if (pendingList) pendingList.innerHTML = `<div style="color:#a1a1aa; font-size:0.85rem;">載入中...</div>`;

    try {
      const res = await fetch("/api/updates/status");
      const resp = await res.json();
      const data = (resp && resp.data) ? resp.data : resp;

      // 1. Sources Cards
      if (sourcesGrid) {
        let sources = data.sources || [];
        if (!Array.isArray(sources)) {
          sources = Object.values(sources);
        }
        const sourceKeys = Object.keys(sources);
        if (sourceKeys.length === 0) {
          sourcesGrid.innerHTML = `<div style="color:#71717a; font-size:0.85rem;">目前無來源紀錄</div>`;
        } else {
          sourcesGrid.innerHTML = sourceKeys.map((srcKey) => {
            const s = sources[srcKey];
            const isOk = s.status === "normal" || s.status === "success" || s.status === "no_change" || s.status === "dry_run_completed";
            const badgeColor = isOk ? "#22c55e" : "#ef4444";
            let lastRunStr = "從未執行";
            if (s.last_run && typeof s.last_run === "object" && s.last_run.finished_at) {
              lastRunStr = s.last_run.finished_at.substring(0, 19).replace("T", " ");
            } else if (typeof s.last_run === "string") {
              lastRunStr = s.last_run.substring(0, 19).replace("T", " ");
            } else if (s.last_success_at) {
              lastRunStr = s.last_success_at.substring(0, 19).replace("T", " ");
            }
            let lastCheckStr = "無紀錄";
            if (s.last_run && typeof s.last_run === "object" && s.last_run.started_at) {
              lastCheckStr = s.last_run.started_at.substring(0, 19).replace("T", " ");
            } else if (typeof s.last_check === "string") {
              lastCheckStr = s.last_check.substring(0, 19).replace("T", " ");
            }
            const freqStr = s.check_frequency || s.schedule || "daily";
            return `
              <div style="background:#18181b; border:1px solid #27272a; border-radius:8px; padding:0.85rem;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                  <strong style="color:#f4f4f5; font-size:0.92rem;">${esc(s.name)}</strong>
                  <span style="font-size:0.75rem; color:${badgeColor}; border:1px solid ${badgeColor}; padding:1px 6px; border-radius:4px;">
                    ${esc(s.status || "normal")}
                  </span>
                </div>
                <div style="font-size:0.78rem; color:#a1a1aa; display:flex; flex-direction:column; gap:0.25rem;">
                  <div>上次執行：${esc(lastRunStr)}</div>
                  <div>檢查時間：${esc(lastCheckStr)}</div>
                  <div>同步週期：${esc(freqStr)}</div>
                </div>
              </div>`;
          }).join("");
        }
      }

      // Pending Human Review Alert
      if (data.pending_human && data.pending_human.length > 0) {
        const phHtml = `
          <div style="background:rgba(239, 68, 68, 0.15); border:1px solid #ef4444; border-radius:8px; padding:0.85rem; margin-bottom:1rem; color:#fca5a5;">
            <div style="font-weight:700; font-size:0.92rem; display:flex; align-items:center; gap:6px;">
              <span>⚠️ 待人工確認事項 (疑似換號或法規異常)</span>
            </div>
            <div style="font-size:0.82rem; margin-top:0.4rem; display:flex; flex-direction:column; gap:0.4rem;">
              ${data.pending_human.map(ph => `
                <div style="background:#18181b; padding:6px 10px; border-radius:4px; border:1px solid #3f3f46;">
                  <strong>${esc(ph.law_name)}</strong> (舊號: ${esc(ph.old_pcode || '-')} → 新號: ${esc(ph.new_pcode || '-')})：${esc(ph.reason || '')}
                </div>
              `).join('')}
            </div>
          </div>`;
        const container = changesList.parentElement;
        if (!container.querySelector('.pending-human-banner')) {
          const phDiv = document.createElement('div');
          phDiv.className = 'pending-human-banner';
          phDiv.innerHTML = phHtml;
          container.insertBefore(phDiv, changesList);
        }
      }

      // 2. Recent Changes List (Separated into 新增法規 & 條文修正 per Prompt 4C)
      if (changesList) {
        const newActs = data.new_acts || [];
        const modArts = data.modified_articles || [];
        let html = "";

        // Section 2A: 新增法規
        html += `<div style="margin-bottom:1rem;">
          <div style="font-size:0.88rem; font-weight:700; color:#22c55e; margin-bottom:0.5rem; display:flex; align-items:center; gap:6px;">
            <span>✨ 新增法規</span>
            <span style="font-size:0.75rem; background:#14532d; color:#86efac; padding:1px 6px; border-radius:10px;">${newActs.length}</span>
          </div>`;
        if (newActs.length === 0) {
          html += `<div style="color:#71717a; font-size:0.8rem; padding:0.3rem 0.5rem;">近期無新增法規</div>`;
        } else {
          html += `<div style="display:flex; flex-direction:column; gap:0.5rem;">` + newActs.map((na) => {
            const detail = na.detail || {};
            const pubDate = na.act_date_raw || detail.source_modified_date || detail.date_raw || "";
            const effNote = na.effective_note || detail.effective_note_raw || "";
            return `
              <div class="new-act-change-card" style="background:#18181b; border:1px solid #166534; border-radius:6px; padding:0.65rem 0.85rem;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                  <div style="display:flex; align-items:center; gap:0.5rem;">
                    <span class="badge-new-act" style="background:#15803d; color:#ffffff; font-size:0.72rem; font-weight:700; padding:2px 6px; border-radius:4px;">新增</span>
                    <strong style="color:#f4f4f5; font-size:0.92rem;">${esc(na.act_name || na.act_id)}</strong>
                  </div>
                  <span class="source-date-raw" style="color:#86efac; font-family:monospace; font-size:0.8rem;">${esc(pubDate)}</span>
                </div>
                ${effNote ? `<div class="effective-note-raw" style="margin-top:0.35rem; font-size:0.78rem; color:#f59e0b; background:#291e0a; padding:3px 8px; border-radius:4px;">⏳ 未生效備註：${esc(effNote)}</div>` : ""}
              </div>`;
          }).join("") + `</div>`;
        }
        html += `</div>`;

        // Section 2B: 條文修正
        html += `<div>
          <div style="font-size:0.88rem; font-weight:700; color:#60a5fa; margin-bottom:0.5rem; display:flex; align-items:center; gap:6px;">
            <span>📝 條文修正</span>
            <span style="font-size:0.75rem; background:#1e3a8a; color:#93c5fd; padding:1px 6px; border-radius:10px;">${modArts.length}</span>
          </div>`;
        if (modArts.length === 0) {
          html += `<div style="color:#71717a; font-size:0.8rem; padding:0.3rem 0.5rem;">近 30 天內無條文修正紀錄</div>`;
        } else {
          html += `<div style="display:flex; flex-direction:column; gap:0.5rem;">` + modArts.map((c) => {
            const dateStr = c.created_at ? c.created_at.substring(0, 10) : "";
            const actLabel = c.act_name ? `${c.act_name} (${c.act_id})` : c.act_id;
            const artLabel = c.article_no ? `第 ${c.article_no} 條` : "全法規";
            let diffHtml = "";
            const detail = c.detail || {};
            if (detail.old_content || detail.new_content) {
              diffHtml = `
                <div class="diff-block" style="margin-top:0.4rem; font-size:0.8rem;">
                  ${detail.old_content ? `<div class="diff-row del" style="padding:4px 8px;"><span class="diff-tag">修正前</span>${esc(detail.old_content)}</div>` : ""}
                  ${detail.new_content ? `<div class="diff-row add" style="padding:4px 8px;"><span class="diff-tag">修正後</span>${esc(detail.new_content)}</div>` : ""}
                </div>`;
            }
            return `
              <div style="background:#18181b; border:1px solid #27272a; border-radius:6px; padding:0.65rem 0.85rem;">
                <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.85rem;">
                  <div>
                    <span style="font-weight:600; color:#60a5fa;">${esc(actLabel)}</span>
                    <span style="color:#f4f4f5; margin-left:0.4rem;">${esc(artLabel)}</span>
                    <span style="color:#a1a1aa; font-size:0.75rem; margin-left:0.5rem;">[${esc(c.change_type)}]</span>
                  </div>
                  <span style="color:#71717a; font-size:0.75rem;">${esc(dateStr)}</span>
                </div>
                ${diffHtml}
              </div>`;
          }).join("") + `</div>`;
        }
        html += `</div>`;

        changesList.innerHTML = html;
      }

      // 3. Pending Queue
      if (pendingList) {
        const pending = data.pending_items || [];
        if (pending.length === 0) {
          pendingList.innerHTML = `<div style="color:#71717a; font-size:0.85rem; padding:0.5rem 0;">待抓取與異常佇列均已清空</div>`;
        } else {
          pendingList.innerHTML = pending.map((p) => {
            return `
              <div style="background:#18181b; border:1px solid #27272a; border-radius:6px; padding:0.5rem 0.85rem; display:flex; justify-content:space-between; align-items:center; font-size:0.82rem;">
                <div>
                  <span style="color:#e4e4e7;">${esc(p.act_id)} 第 ${esc(p.article_no)} 條</span>
                  <span style="color:#a1a1aa; font-size:0.75rem; margin-left:0.5rem;">重試次數：${esc(String(p.retry_count))}</span>
                </div>
                <span style="font-size:0.75rem; color:${p.status === 'expired_8_weeks' ? '#f59e0b' : '#38bdf8'};">
                  ${esc(p.status)}
                </span>
              </div>`;
          }).join("");
        }
      }
    } catch (e) {
      if (sourcesGrid) sourcesGrid.innerHTML = `<div style="color:#ef4444; font-size:0.85rem;">載入失敗：${esc(e.message)}</div>`;
    }
  }

  async checkBookmarksAlert() {
    try {
      const raw = localStorage.getItem("legal_hub_bookmarks");
      if (!raw) return;
      const bmarks = JSON.parse(raw);
      if (!Array.isArray(bmarks) || bmarks.length === 0) return;

      const res = await fetch("/api/updates/check_bookmarks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ bookmarks: bmarks })
      });
      const data = await res.json();
      if (data.stale_count && data.stale_count > 0) {
        const banner = document.getElementById("bookmark-alert-banner");
        const content = document.getElementById("bookmark-alert-content");
        if (banner && content) {
          content.innerHTML = `⚠️ 提醒：您收藏的法條中有 <b>${data.stale_count}</b> 條已由主管機關發布新修正案，點擊上方更新按鈕可查看歷次修正與比對。`;
          banner.classList.remove("hidden");
        }
      }
    } catch (e) {
      console.warn("Bookmark update check failed:", e);
    }
  }

  exportBookmarks() {
    const raw = localStorage.getItem("legal_hub_bookmarks") || "[]";
    const blob = new Blob([raw], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `legal_hub_bookmarks_${new Date().toISOString().substring(0,10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  importBookmarks(e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const imported = JSON.parse(event.target.result);
        if (Array.isArray(imported)) {
          const current = JSON.parse(localStorage.getItem("legal_hub_bookmarks") || "[]");
          const merged = [...current];
          for (const item of imported) {
            if (item && item.actId && item.articleNo) {
              const exists = merged.some(b => b.actId === item.actId && b.articleNo === item.articleNo);
              if (!exists) merged.push(item);
            }
          }
          localStorage.setItem("legal_hub_bookmarks", JSON.stringify(merged));
          alert(`成功匯入 ${imported.length} 筆書籤`);
          this.renderBookmarksList();
          this.checkBookmarksAlert();
        }
      } catch (err) {
        alert("匯入失敗：檔案格式不正確");
      }
    };
    reader.readAsText(file);
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
    const actId = (window.legalHubApp && window.legalHubApp.currentActId) || "";
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
