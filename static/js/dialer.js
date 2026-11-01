/**
 * Legal Hub - 0-9 Quick Dial Pad Controller
 * Implements instant numeric key dialing and smooth jump to target article.
 */

class QuickDialer {
  constructor(app) {
    this.app = app;
    this.buffer = "";
    this.container = document.getElementById("quick-dialer");
    this.display = document.getElementById("dialer-display");
    this.fab = document.getElementById("dialer-fab");
    this.autoJumpTimer = null;
    
    this.initEvents();
  }

  initEvents() {
    // Keypad button clicks
    const keys = document.querySelectorAll(".dialer-key");
    keys.forEach(key => {
      key.addEventListener("click", (e) => {
        const val = e.currentTarget.dataset.val;
        this.handleKey(val);
      });
    });

    // Close button
    const closeBtn = document.getElementById("dialer-close-btn");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => this.toggle(false));
    }

    // Jump button in dialer footer
    const jumpBtn = document.getElementById("dialer-jump-btn");
    if (jumpBtn) {
      jumpBtn.addEventListener("click", () => this.executeJump(true));
    }

    // Floating FAB toggle
    if (this.fab) {
      this.fab.addEventListener("click", () => this.toggle());
    }

    // Top navbar dialer toggle button
    const toggleBtn = document.getElementById("dialer-toggle-btn");
    if (toggleBtn) {
      toggleBtn.addEventListener("click", () => this.toggle());
    }

    // Physical keyboard shortcut for numbers (when not typing in search box)
    window.addEventListener("keydown", (e) => {
      const activeEl = document.activeElement;
      if (activeEl && (activeEl.tagName === "INPUT" || activeEl.tagName === "TEXTAREA")) {
        return;
      }

      if ((e.key >= "0" && e.key <= "9") || e.key === "-") {
        this.toggle(true);
        this.handleKey(e.key);
      } else if (e.key === "Backspace") {
        if (this.buffer.length > 0) {
          this.handleKey("backspace");
        }
      } else if (e.key === "Enter") {
        if (this.buffer.length > 0) {
          this.handleKey("go");
        }
      }
    });
  }

  toggle(show = null) {
    if (!this.container) return;
    const isHidden = this.container.classList.contains("hidden");
    const shouldShow = show !== null ? show : isHidden;
    
    if (shouldShow) {
      this.container.classList.remove("hidden");
      if (this.fab) this.fab.style.display = "none";
    } else {
      this.container.classList.add("hidden");
      if (this.fab) this.fab.style.display = "flex";
      this.clear();
    }
  }

  handleKey(val) {
    if (val === "backspace") {
      this.buffer = this.buffer.slice(0, -1);
    } else if (val === "clear") {
      this.buffer = "";
    } else if (val === "go") {
      this.executeJump();
      return;
    } else if (val) {
      // Append digit or dash (limit length to 8 characters)
      if (this.buffer.length < 8) {
        this.buffer += val;
      }
    }

    this.updateDisplay();

    // Debounced smart jump: if user stops typing for 1000ms, auto-trigger jump
    if (this.autoJumpTimer) clearTimeout(this.autoJumpTimer);
    if (this.buffer.length > 0) {
      this.autoJumpTimer = setTimeout(() => {
        this.executeJump(false); // Soft jump without clearing
      }, 1200);
    }
  }

  updateDisplay() {
    if (this.display) {
      this.display.textContent = this.buffer ? `第 ${this.buffer} 條` : "請輸入條號";
    }
  }

  clear() {
    this.buffer = "";
    this.updateDisplay();
    if (this.autoJumpTimer) clearTimeout(this.autoJumpTimer);
  }

  async executeJump(clearAfter = true) {
    const targetNo = this.buffer.trim();
    if (!targetNo) return;

    const found = await this.app.loadAndJumpArticle(targetNo);
    if (found) {
      if (clearAfter) {
        setTimeout(() => {
          this.clear();
          // on mobile, auto close dialer when jumped to article
          if (window.innerWidth <= 768) {
            this.toggle(false);
          }
        }, 300);
      }
    } else {
      if (this.display) {
        this.display.textContent = `查無 第 ${targetNo} 條`;
      }
    }
  }
}

window.QuickDialer = QuickDialer;
