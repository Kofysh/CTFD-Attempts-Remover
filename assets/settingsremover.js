(() => {
  "use strict";

  const PLUGIN_BASE     = "/api/v1/attempts_remover";
  const CACHE_TTL_MS    = 60_000;
  const DEBOUNCE_MS     = 800;
  const BUTTON_SELECTOR = "[data-challenge-id], .challenge-button";

  
  async function api(path) {
    try {
      const resp = await fetch(PLUGIN_BASE + path, { credentials: "same-origin" });
      if (!resp.ok) return null;
      return await resp.json();
    } catch {
      return null;
    }
  }

  function t(key, vars = {}) {
    if (window.RemoverI18n) return RemoverI18n.t(key, vars);
    const fallbacks = {
      btn_request_unblock:        "Request a challenge unblock",
      challenge_locked_tooltip:   `🔒 Locked (${vars.current ?? "?"}/${vars.max ?? "?"} attempts)`,
    };
    return fallbacks[key] ?? key;
  }

  function injectStyle(id, css) {
    if (document.getElementById(id)) return;
    const el = document.createElement("style");
    el.id = id;
    el.textContent = css;
    document.head.appendChild(el);
  }

  function injectUnblockButton() {
    if (document.getElementById("btn-unblock-wrapper")) return;

    const container = document.querySelector(".row > .col-md-12");
    if (!container) return;

    injectStyle("remover-base-style", `
      #btn-unblock-page {
        transition: background-color 0.2s ease, transform 0.15s ease;
      }
      #btn-unblock-page:hover {
        background-color: #1a1f25 !important;
        transform: scale(1.02);
      }
    `);

    const wrapper = Object.assign(document.createElement("div"), {
      className: "d-flex justify-content-center mb-4",
      id:        "btn-unblock-wrapper",
    });

    const btn = Object.assign(document.createElement("a"), {
      href:      "/plugins/ctfd-attempts-remover/unblock",
      className: "btn btn-info text-white shadow rounded-pill px-4 py-2 fw-semibold d-inline-flex align-items-center gap-2",
      id:        "btn-unblock-page",
    });

    const icon = Object.assign(document.createElement("i"), { className: "fa fa-user-lock" });
    const text = Object.assign(document.createElement("span"), { textContent: t("btn_request_unblock") });

    btn.append(icon, text);
    wrapper.appendChild(btn);
    container.prepend(wrapper);
  }

  function buildBlockedStyle() {
    return `
      .challenge-button.remover-blocked,
      [data-challenge-id].remover-blocked {
        background: linear-gradient(135deg, #dc3545, #b02a37) !important;
        border-color: #dc3545 !important;
        position: relative;
        overflow: hidden;
      }
      .challenge-button.remover-blocked::before,
      [data-challenge-id].remover-blocked::before {
        content: "🔒";
        position: absolute;
        top: 4px;
        left: 7px;
        font-size: 11px;
        z-index: 10;
        pointer-events: none;
      }
      .challenge-button.remover-blocked:hover,
      [data-challenge-id].remover-blocked:hover {
        background: linear-gradient(135deg, #b02a37, #9c1e2a) !important;
        transform: scale(1.02);
        box-shadow: 0 4px 16px rgba(220, 53, 69, 0.45);
      }
      @keyframes remover-pulse {
        0%, 100% { box-shadow: 0 2px 8px rgba(220, 53, 69, 0.3); }
        50%       { box-shadow: 0 4px 18px rgba(220, 53, 69, 0.55); }
      }
      .challenge-button.remover-blocked,
      [data-challenge-id].remover-blocked {
        animation: remover-pulse 3s ease-in-out infinite;
      }
    `;
  }

  
  function createHighlighter() {
    let cache       = [];
    let fetchedAt   = 0;
    let debounceId  = null;

    async function refresh() {
      const data = await api("/blocked");
      if (Array.isArray(data)) {
        cache     = data;
        fetchedAt = Date.now();
      }
    }

    function applyStyles() {
      if (cache.length === 0) return;

      const idMap   = new Map(cache.map(c => [c.challenge_id, c]));
      const nameMap = new Map(cache.map(c => [c.challenge_name.trim().toLowerCase(), c]));

      document.querySelectorAll(BUTTON_SELECTOR).forEach(el => {
        const id      = parseInt(el.getAttribute("data-challenge-id") ?? el.dataset.challengeId, 10);
        const rawText = (el.textContent ?? el.innerText ?? "").trim().toLowerCase();

        const entry = idMap.get(id) ?? nameMap.get(rawText);
        if (!entry) return;

        if (!el.classList.contains("remover-blocked")) {
          el.classList.add("remover-blocked");
          el.title = t("challenge_locked_tooltip", {
            current: entry.fail_count,
            max:     entry.max_attempts,
          });
        }
      });
    }

    async function run(force = false) {
      const stale = Date.now() - fetchedAt > CACHE_TTL_MS;
      if (force || stale) await refresh();
      applyStyles();
    }

    function schedule() {
      clearTimeout(debounceId);
      debounceId = setTimeout(() => run(), DEBOUNCE_MS);
    }

    return { run, schedule };
  }

  async function main() {
    if (window.location.pathname !== "/challenges") return;

    injectUnblockButton();

    const config = await api("/config");
    if (!config?.highlight_blocked_challenges) return;

    injectStyle("remover-blocked-style", buildBlockedStyle());

    const highlighter = createHighlighter();

    setTimeout(() => highlighter.run(true), 900);

    window.addEventListener("focus", () => highlighter.run(true));

    const observer = new MutationObserver(mutations => {
      const relevant = mutations.some(m =>
        [...m.addedNodes].some(node => {
          if (node.nodeType !== Node.ELEMENT_NODE) return false;
          return (
            node.matches?.(BUTTON_SELECTOR) ||
            node.querySelector?.(BUTTON_SELECTOR)
          );
        })
      );
      if (relevant) highlighter.schedule();
    });

    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", main);
  } else {
    main();
  }
})();
