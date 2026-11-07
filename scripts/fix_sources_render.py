with open('static/js/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''          sourcesGrid.innerHTML = sourceKeys.map((srcKey) => {
            const s = sources[srcKey];
            const isOk = s.status === "success" || s.status === "no_change" || s.status === "dry_run_completed";
            const badgeColor = isOk ? "#22c55e" : "#ef4444";
            const lastRunStr = s.last_run ? s.last_run.substring(0, 19).replace("T", " ") : "從未執行";
            const lastCheckStr = s.last_check ? s.last_check.substring(0, 19).replace("T", " ") : "無紀錄";
            return `
              <div style="background:#18181b; border:1px solid #27272a; border-radius:8px; padding:0.85rem;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                  <strong style="color:#f4f4f5; font-size:0.92rem;">${esc(s.name)}</strong>
                  <span style="font-size:0.75rem; color:${badgeColor}; border:1px solid ${badgeColor}; padding:1px 6px; border-radius:4px;">
                    ${esc(s.status)}
                  </span>
                </div>
                <div style="font-size:0.78rem; color:#a1a1aa; display:flex; flex-direction:column; gap:0.25rem;">
                  <div>上次執行：${esc(lastRunStr)}</div>
                  <div>檢查時間：${esc(lastCheckStr)}</div>
                  <div>同步週期：${esc(s.schedule)}</div>
                </div>
              </div>`;
          }).join("");'''

replacement = '''          sourcesGrid.innerHTML = sourceKeys.map((srcKey) => {
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
          }).join("");'''

if target in text:
    text = text.replace(target, replacement, 1)
    with open('static/js/app.js', 'w', encoding='utf-8') as f:
        f.write(text)
    print('Replaced target with LF!')
elif target.replace('\n', '\r\n') in text:
    text = text.replace(target.replace('\n', '\r\n'), replacement.replace('\n', '\r\n'), 1)
    with open('static/js/app.js', 'w', encoding='utf-8') as f:
        f.write(text)
    print('Replaced target with CRLF!')
else:
    print('Target not found!')

