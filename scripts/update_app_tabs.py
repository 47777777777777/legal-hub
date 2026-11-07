import sys

with open('static/js/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

pos_start = text.find('// ---------------- Tab 1:')
pos_end = text.find('// ---------------- Tab 5: 我的收藏 ----------------')
assert pos_start != -1 and pos_end != -1, f"pos_start={pos_start}, pos_end={pos_end}"

new_tabs_code = '''// ---------------- Tab 1: 關鍵知識 ----------------
  renderKeyKnowledgeHtml(art) {
    let html = "";
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
        ${insights.map((ins) => `
          <div class="card">
            <div class="card-title accent">${ins.court ? `${esc(ins.court)} · ` : ""}${esc(ins.ref || "重要裁判")}</div>
            <div class="card-body" style="line-height: 1.6;">${esc(ins.summary || "")}</div>
            ${ins.url ? `<div style="margin-top:0.35rem;"><a href="${esc(ins.url)}" target="_blank" rel="noopener noreferrer" style="font-size:0.8rem; color:#60a5fa; text-decoration:none;">查看裁判原文 ↗</a></div>` : ""}
          </div>
        `).join("")}
      </section>`;
    }

    if (letters.length) {
      const letterHeading = (art.source === "lawplayer") ? "相關令函與行政函釋 (法律人)" : "相關令函與行政函釋";
      html += `
        <section>${sectionHeading("book", letterHeading, `${letters.length}`, sourceInfo)}
          ${letters.map((letItem) => `
            <div class="card">
              <div class="card-title accent">${letItem.org ? `${esc(letItem.org)} · ` : ""}${esc(letItem.ref || "行政函釋")}${letItem.date ? ` · ${esc(letItem.date)}` : ""}</div>
              <div class="card-body" style="line-height: 1.6; white-space: pre-wrap;">${esc(letItem.summary || letItem.content || "")}</div>
              ${letItem.url ? `<div style="margin-top:0.35rem;"><a href="${esc(letItem.url)}" target="_blank" rel="noopener noreferrer" style="font-size:0.8rem; color:#60a5fa; text-decoration:none;">查看函釋原文 ↗</a></div>` : ""}
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
    const history = (art.source && art.amendment_history) ? art.amendment_history : [];
    const sourceInfo = (art.source === "lawplayer" && art.source_url) 
      ? `法律人 (${(art.fetched_at || "").substring(0, 10)})` 
      : (art.source ? `${art.source} (${(art.fetched_at || "").substring(0, 10)})` : "");

    if (art.source && (history.length || art.legislative_reasons)) {
      if (history.length) {
        return `
          <section>${sectionHeading("file", "歷次修法理由與新舊法對照 Diff", `${history.length}`, sourceInfo)}
            ${history.map((item) => `
              <div class="card">
                <div class="card-title accent">${item.date ? `${esc(item.date)} · ` : ""}${esc(item.change_type || item.type || "修正")}</div>
                <div class="card-body">${esc(item.reason || "")}</div>
                ${item.old_content ? `
                  <div class="diff-block">
                    <div class="diff-row del"><span class="diff-tag">修正前</span>${esc(item.old_content)}</div>
                    <div class="diff-row add"><span class="diff-tag">修正後</span>${esc(item.new_content || art.content)}</div>
                  </div>` : ""}
              </div>
            `).join("")}
          </section>`;
      } else {
        return `
          <section>${sectionHeading("file", "制定與修正理由", null, sourceInfo)}
            <div class="card">
              <div class="card-body">${esc(art.legislative_reasons)}</div>
            </div>
          </section>`;
      }
    }

    return `<div style="padding:1.5rem 0.5rem; text-align:center; color:#71717a; font-size:0.9rem;">
      此條尚無外部解析資料
    </div>`;
  }

  '''

text = text[:pos_start] + new_tabs_code + text[pos_end:]
with open('static/js/app.js', 'w', encoding='utf-8') as f:
    f.write(text)

print('Successfully updated static/js/app.js with clean tab rendering logic.')

