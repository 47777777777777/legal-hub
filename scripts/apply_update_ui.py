import os

APP_JS = "static/js/app.js"
INDEX_HTML = "static/index.html"

with open(APP_JS, "r", encoding="utf-8") as f:
    js_content = f.read()

# 1. Add hook in init()
if "this.bindUpdateStatusEvents();" not in js_content:
    js_content = js_content.replace(
        "this.bindCCUEvents();",
        "this.bindCCUEvents();\n    this.bindUpdateStatusEvents();\n    this.checkBookmarksAlert();"
    )

# 2. Update renderActMeta
old_meta = """    const meta = document.getElementById("act-meta-inline");
    if (meta && this.currentAct) {
      const parts = [this.currentAct.category, this.currentAct.last_modified].filter(Boolean);
      meta.textContent = parts.length ? `(${parts.join(" · ")})` : "";
    }"""

new_meta = """    const meta = document.getElementById("act-meta-inline");
    if (meta && this.currentAct) {
      const parts = [];
      if (this.currentAct.category) parts.push(this.currentAct.category);
      if (this.currentAct.last_modified) parts.push(`最新修正：${this.currentAct.last_modified}`);
      if (this.currentAct.sync_time) parts.push(`同步：${this.currentAct.sync_time.substring(0, 10)}`);
      if (this.currentAct.abandon_note) parts.push(`【已廢止：${this.currentAct.abandon_note}】`);
      else if (this.currentAct.status === "abolished") parts.push(`【已廢止】`);
      if (this.currentAct.effective_note) parts.push(`【${this.currentAct.effective_note}】`);
      meta.textContent = parts.length ? `(${parts.join(" · ")})` : "";
    }"""

if old_meta in js_content:
    js_content = js_content.replace(old_meta, new_meta)

# 3. Add stale warning in renderKeyKnowledgeHtml
old_key = """  renderKeyKnowledgeHtml(art) {
    let html = "";"""

new_key = """  renderKeyKnowledgeHtml(art) {
    let html = "";
    if (art.stale === 1 || art.stale === true) {
      const modDate = (this.currentAct && this.currentAct.last_modified) || "最新修法";
      html += `
        <div class="stale-alert-banner" style="background:rgba(234, 179, 8, 0.12); border:1px solid rgba(234, 179, 8, 0.4); color:#fde047; padding:0.65rem 0.85rem; border-radius:6px; margin-bottom:1rem; font-size:0.85rem; display:flex; align-items:center; gap:0.5rem;">
          <span style="font-size:1.1rem;">⚠️</span>
          <span>本條已於 ${esc(modDate)} 修正，下列法律人解析可能對應修正前條文。</span>
        </div>`;
    }"""

if old_key in js_content:
    js_content = js_content.replace(old_key, new_key)

# 4. Add Update Status & Bookmark alert methods to App class
update_methods = """
  // ---------------- Update Status & Legislative Tracking (Prompt 4) ----------------
  bindUpdateStatusEvents() {
    const btn = document.getElementById("update-status-btn");
    const modal = document.getElementById("update-status-modal");
    const closeBtn = document.getElementById("update-status-modal-close");
    const exportBtn = document.getElementById("export-bookmarks-btn");
    const importInput = document.getElementById("import-bookmarks-file");
    const alertClose = document.getElementById("bookmark-alert-close");

    if (btn && modal) {
      btn.addEventListener("click", () => this.openUpdateStatusModal());
    }
    if (closeBtn && modal) {
      closeBtn.addEventListener("click", () => modal.classList.add("hidden"));
      modal.addEventListener("click", (e) => {
        if (e.target === modal) modal.classList.add("hidden");
      });
    }
    if (exportBtn) {
      exportBtn.addEventListener("click", () => this.exportBookmarks());
    }
    if (importInput) {
      importInput.addEventListener("change", (e) => this.importBookmarks(e.target.files[0]));
    }
    if (alertClose) {
      alertClose.addEventListener("click", () => {
        const b = document.getElementById("bookmark-alert-banner");
        if (b) b.classList.add("hidden");
      });
    }
  }

  async checkBookmarksAlert() {
    if (!this.bookmarks || !this.bookmarks.length) return;
    try {
      const res = await fetch("/api/updates/check_bookmarks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ bookmarks: this.bookmarks.map(b => ({ act_id: b.actId, article_no: b.articleNo })) })
      });
      const json = await res.json();
      if (json.success && json.data && json.data.length > 0) {
        const banner = document.getElementById("bookmark-alert-banner");
        const content = document.getElementById("bookmark-alert-content");
        if (banner && content) {
          content.innerHTML = `<strong>收藏條文異動提醒：</strong> ${json.data.map(d => esc(d.message)).join("； ")}`;
          banner.classList.remove("hidden");
        }
      }
    } catch (e) {
      console.warn("checkBookmarksAlert failed:", e);
    }
  }

  exportBookmarks() {
    const blob = new Blob([JSON.stringify(this.bookmarks, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `legal_hub_bookmarks_${new Date().toISOString().substring(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  importBookmarks(file) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const imported = JSON.parse(e.target.result);
        if (Array.isArray(imported)) {
          let added = 0;
          for (const b of imported) {
            if (b.actId && b.articleNo && !this.isBookmarked(b.actId, b.articleNo)) {
              this.bookmarks.push(b);
              added++;
            }
          }
          this.saveBookmarks();
          this.refreshStreamBookmarkMarks();
          this.checkBookmarksAlert();
          alert(`成功匯入 ${added} 筆新收藏條文！`);
        }
      } catch (err) {
        alert("匯入失敗：JSON 格式無效。");
      }
    };
    reader.readAsText(file);
  }

  async openUpdateStatusModal() {
    const modal = document.getElementById("update-status-modal");
    if (!modal) return;
    modal.classList.remove("hidden");

    const sourcesGrid = document.getElementById("update-sources-grid");
    const changesList = document.getElementById("recent-changes-list");
    const pendingList = document.getElementById("pending-items-list");

    if (sourcesGrid) sourcesGrid.innerHTML = '<div style="color:#a1a1aa; font-size:0.85rem;">載入來源狀態中...</div>';
    if (changesList) changesList.innerHTML = '<div style="color:#a1a1aa; font-size:0.85rem;">載入最近修法記錄中...</div>';

    try {
      const res = await fetch("/api/updates/status");
      const json = await res.json();
      if (!json.success || !json.data) return;
      const data = json.data;

      // Render Sources
      if (sourcesGrid) {
        sourcesGrid.innerHTML = data.sources.map(s => {
          const isNormal = s.status === "normal";
          const statusColor = isNormal ? "#22c55e" : (s.status === "warning" ? "#eab308" : "#ef4444");
          const statusText = isNormal ? "正常運行" : (s.status === "warning" ? "排程警告" : "異常中止");
          const lastCheck = s.last_run ? s.last_run.started_at.substring(0, 19).replace("T", " ") : "尚未排程";
          const lastSuccess = s.last_success_at ? s.last_success_at.substring(0, 10) : "無";

          return `
            <div style="background:#18181b; border:1px solid #27272a; border-radius:8px; padding:0.85rem; display:flex; flex-direction:column; gap:0.4rem;">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:700; color:#fafafa; font-size:0.95rem;">${esc(s.name.toUpperCase())}</span>
                <span style="font-size:0.75rem; padding:0.15rem 0.5rem; border-radius:4px; background:${statusColor}22; color:${statusColor}; font-weight:600;">${statusText}</span>
              </div>
              <div style="font-size:0.8rem; color:#a1a1aa;">${esc(s.description)}</div>
              <div style="font-size:0.75rem; color:#71717a; margin-top:0.3rem;">
                <div>執行位置：${esc(s.location)} (${esc(s.check_frequency)})</div>
                <div>上次檢查：${esc(lastCheck)}</div>
                <div>上次成功：${esc(lastSuccess)}</div>
                ${s.consecutive_failures > 0 ? `<div style="color:#f87171;">連續失敗：${s.consecutive_failures} 次</div>` : ""}
              </div>
            </div>`;
        }).join("");
      }

      // Render Recent Changes with Red-Green Diff
      if (changesList) {
        if (!data.recent_changes || !data.recent_changes.length) {
          changesList.innerHTML = '<div style="color:#71717a; font-size:0.85rem; padding:0.5rem;">近 30 天無修法或條文變動記錄。</div>';
        } else {
          changesList.innerHTML = data.recent_changes.map(ch => {
            const actLabel = ch.act_name ? `${ch.act_name}` : ch.act_id;
            const artLabel = ch.article_no ? `第 ${ch.article_no} 條` : "";
            const typeBadges = {
              "add_article": { text: "新增條文", color: "#22c55e" },
              "modify_article": { text: "條文修正", color: "#3b82f6" },
              "delete_article": { text: "條文刪除", color: "#ef4444" },
              "add_act": { text: "新制定法規", color: "#22c55e" },
              "abolish_act": { text: "法規廢止", color: "#ef4444" }
            };
            const badge = typeBadges[ch.change_type] || { text: ch.change_type, color: "#a1a1aa" };
            let detail = {};
            try { detail = JSON.parse(ch.detail_json || "{}"); } catch (e) {}

            const oldText = detail.old_content || "";
            const newText = detail.new_content || "";
            const hasDiff = Boolean(oldText || newText);

            return `
              <div style="background:#18181b; border:1px solid #27272a; border-radius:6px; padding:0.75rem;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                  <div style="display:flex; align-items:center; gap:0.5rem;">
                    <span style="font-size:0.75rem; padding:0.15rem 0.45rem; border-radius:4px; background:${badge.color}22; color:${badge.color}; font-weight:700;">${badge.text}</span>
                    <span style="font-weight:600; color:#fafafa; font-size:0.9rem;">${esc(actLabel)} ${esc(artLabel)}</span>
                  </div>
                  <span style="font-size:0.75rem; color:#71717a;">${esc((ch.created_at || "").substring(0, 16))}</span>
                </div>
                ${hasDiff ? `
                  <details style="margin-top:0.5rem;">
                    <summary style="font-size:0.8rem; color:#60a5fa; cursor:pointer;">查看新舊條文逐字對照</summary>
                    <div style="margin-top:0.4rem; display:flex; flex-direction:column; gap:0.35rem;">
                      ${oldText ? `<div style="background:rgba(239, 68, 68, 0.12); border-left:3px solid #ef4444; padding:6px 10px; font-size:0.85rem; color:#fca5a5; line-height:1.5;"><span style="font-weight:700; margin-right:6px;">[舊]</span>${esc(oldText)}</div>` : ""}
                      ${newText ? `<div style="background:rgba(34, 197, 94, 0.12); border-left:3px solid #22c55e; padding:6px 10px; font-size:0.85rem; color:#86efac; line-height:1.5;"><span style="font-weight:700; margin-right:6px;">[新]</span>${esc(newText)}</div>` : ""}
                    </div>
                  </details>
                ` : ""}
              </div>`;
          }).join("");
        }
      }

      // Render Pending Queue
      if (pendingList) {
        if (!data.pending_lis || !data.pending_lis.length) {
          pendingList.innerHTML = '<div style="color:#71717a; font-size:0.85rem; padding:0.5rem;">目前無待處理項目（所有立法理由皆已最新）。</div>';
        } else {
          pendingList.innerHTML = data.pending_lis.map(p => `
            <div style="background:#18181b; border:1px solid #27272a; border-radius:6px; padding:0.6rem 0.85rem; display:flex; justify-content:space-between; align-items:center;">
              <div>
                <span style="font-weight:600; color:#fafafa; font-size:0.85rem;">${esc(p.act_id)} 第 ${esc(p.article_no)} 條</span>
                <span style="font-size:0.75rem; color:#a1a1aa; margin-left:0.5rem;">(立法院尚無本次修正立法理由，重試第 ${p.retry_count}/8 次)</span>
              </div>
              <span style="font-size:0.75rem; padding:0.15rem 0.45rem; border-radius:4px; background:#eab30822; color:#fde047;">排程輪巡中</span>
            </div>
          `).join("");
        }
      }
    } catch (e) {
      if (sourcesGrid) sourcesGrid.innerHTML = `<div style="color:#ef4444;">載入更新狀態失敗: ${esc(e.message)}</div>`;
    }
  }
"""

if "bindUpdateStatusEvents()" not in js_content:
    # insert before the last closing brace
    last_brace = js_content.rfind("}")
    js_content = js_content[:last_brace] + update_methods + "\n}\n"

with open(APP_JS, "w", encoding="utf-8") as f:
    f.write(js_content)

print("Updated static/js/app.js successfully.")

