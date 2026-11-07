import os

with open('static/js/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

target = """  // ---------------- Tab 4: 立法理由與沿革 ----------------
  // ---------------- Tab 4: 立法理由與沿革 ----------------
  // ---------------- Tab 4: 立法理由與沿革 ----------------
  renderLegislativeHtml(art) {
    const history = (art.source && art.amendment_history) ? art.amendment_history : [];
    const sourceInfo = (art.source === "lawplayer" && art.source_url) 
      ? `法律人 (${(art.fetched_at || "").substring(0, 10)})` 
      : (art.source ? `${art.source} (${(art.fetched_at || "").substring(0, 10)})` : "");
    const paywalledReasons = (art.paywalled_counts && art.paywalled_counts.legislative_reasons) ? art.paywalled_counts.legislative_reasons : 0;

    let paywalledNoticeHtml = "";
    if (paywalledReasons > 0) {
      paywalledNoticeHtml = `
        <div class="card" style="margin-bottom:1rem; border-left:3px solid #f59e0b; background:rgba(245,158,11,0.05);">
          <div class="card-body" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
            <span>法律人頁面標示本條有 ${paywalledReasons} 段立法理由（會員內容），無法在此顯示</span>
            ${art.source_url ? `<a href="${esc(art.source_url)}" target="_blank" rel="noopener" class="source-link" style="color:#60a5fa; text-decoration:none;">在法律人查看 ↗</a>` : ""}
          </div>
        </div>`;
    }

    if (art.source && (history.length || art.legislative_reasons || paywalledReasons > 0)) {
      if (history.length) {
        return `
          <section>${sectionHeading("file", "歷次修法理由與新舊法對照 Diff", `${history.length}`, sourceInfo)}
            ${paywalledNoticeHtml}
            ${history.map((item) => `
              <div class="card">
                <div class="card-title accent">${item.date ? `${esc(item.date)} · ` : ""}${esc(item.change_type || item.type || "")}</div>
                <div class="card-body">${esc(item.reason || "")}</div>
                ${item.old_content ? `
                  <div class="diff-block">
                    <div class="diff-row del"><span class="diff-tag">修正前</span>${esc(item.old_content)}</div>
                    <div class="diff-row add"><span class="diff-tag">修正後</span>${esc(item.new_content || art.content)}</div>
                  </div>` : ""}
              </div>
            `).join("")}
          </section>`;
      } else if (art.legislative_reasons) {
        return `
          <section>${sectionHeading("file", "制定與修正理由", null, sourceInfo)}
            ${paywalledNoticeHtml}
            <div class="card">
              <div class="card-body">${esc(art.legislative_reasons)}</div>
            </div>
          </section>`;
      } else {
        return `
          <section>${sectionHeading("file", "制定與修正理由", null, sourceInfo)}
            ${paywalledNoticeHtml}
          </section>`;
      }
    }

    return `<div style="padding:1.5rem 0.5rem; text-align:center; color:#71717a; font-size:0.9rem;">
      此條尚無立法理由資料
    </div>`;
  }"""

replacement = """  // ---------------- Tab 4: 立法理由與沿革 ----------------
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
          const title = `${newDateStr} ${actionText} 對照表${subTitle}`;
          
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
                            ${esc(cell).replace(/\\n/g, '<br>')}
                          </td>
                        `).join("")}
                      </tr>
                    `).join("")}
                  </tbody>
                </table>
              </div>`;
          }

          const reasonBody = c.reason ? `<div class="card-body" style="white-space:pre-wrap; margin-top:0.5rem;"><strong style="color:#a1a1aa;">修正理由：</strong>\\n${esc(c.reason)}</div>` : "";

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
          const title = `${dateStr} ${actionText}`;
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
  }"""

c_norm = content.replace('\r\n', '\n')
t_norm = target.replace('\r\n', '\n')
r_norm = replacement.replace('\r\n', '\n')

if t_norm in c_norm:
    updated = c_norm.replace(t_norm, r_norm)
    with open('static/js/app.js', 'w', encoding='utf-8', newline='\n') as f:
        f.write(updated)
    print("SUCCESS: updated renderLegislativeHtml in static/js/app.js")
else:
    print("ERROR: Target not found in static/js/app.js")

