/**
 * Cloche de notifications (marché) — lisible sur tous les écrans.
 * Données : localStorage charts.s1.market.notifications
 *
 * Appeler ChartsNotif.bind({ getUserId }) au boot,
 * ChartsNotif.refresh(userId) après un switch de compte.
 *
 * Sur booster.html, si #notifWrap existe déjà, le module ne monte rien
 * (la page garde sa propre UI) — utiliser ce module sur les autres écrans.
 */
(function () {
  const MARKET_KEY = "charts.s1.market";
  const STYLE_ID = "charts-notif-css";
  const MARKET_HREF = "booster.html#marche";

  let getUserId = () => "u1";
  let marketBase = "booster.html";
  let bound = false;

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      .notif-wrap { position: relative; }
      .notif-btn {
        appearance: none; position: relative;
        width: 34px; height: 34px; padding: 0; margin: 0;
        border: 1px solid var(--line, #2a2a2a); background: var(--panel, #161616);
        border-radius: 0; cursor: pointer; color: var(--muted, #8a8680);
        display: inline-flex; align-items: center; justify-content: center;
        line-height: 0;
      }
      .notif-btn:hover,
      .notif-wrap.open .notif-btn {
        background: #1c1c1c; color: var(--ink, #f2f0eb);
        border-color: var(--line-hi, #3a3a3a);
      }
      .notif-btn svg {
        width: 16px; height: 16px; display: block;
        flex-shrink: 0; transform: translateY(-0.5px);
      }
      .notif-btn .notif-dot {
        position: absolute; top: 4px; right: 4px;
        width: 8px; height: 8px; border-radius: 50%;
        background: #d8b35c; box-shadow: 0 0 0 2px #141518;
        pointer-events: none;
      }
      .notif-btn .notif-dot[hidden] { display: none; }
      .notif-btn.has-unread { color: #e8e8ea; border-color: #3a3c44; }
      .notif-menu {
        display: none; position: absolute; top: calc(100% + 8px); right: 0; z-index: 60;
        width: min(320px, calc(100vw - 24px));
        background: #121418; border: 1px solid #2a2c32; border-radius: 12px;
        box-shadow: 0 16px 40px rgba(0,0,0,.55);
        overflow: hidden;
      }
      .notif-wrap.open .notif-menu { display: block; }
      .notif-menu .head {
        display: flex; align-items: center; justify-content: space-between; gap: 10px;
        padding: 10px 12px; font-size: 12px; font-weight: 600; color: #e8e8ea;
        border-bottom: 1px solid #1c1d21;
      }
      .notif-menu .head .mark-all {
        appearance: none; border: 0; background: transparent;
        color: #9aa0a8; font: inherit; font-size: 11px; font-weight: 500;
        padding: 0; cursor: pointer; white-space: nowrap;
      }
      .notif-menu .head .mark-all:hover { color: #e8e8ea; }
      .notif-menu .empty {
        padding: 18px 12px; font-size: 12px; color: #8a9099; text-align: center;
      }
      .notif-menu .item {
        appearance: none; width: 100%; display: block; text-align: left;
        border: 0; border-bottom: 1px solid #1c1d21; background: transparent;
        color: #d8d8dc; font: inherit; font-size: 12px; line-height: 1.4;
        padding: 10px 12px; cursor: pointer;
      }
      .notif-menu .item:last-child { border-bottom: 0; }
      .notif-menu .item:hover { background: #1a1c20; }
      .notif-menu .item.unread { background: #16181c; }
      .notif-menu .item .title { color: #b8bcc4; font-weight: 400; }
      .notif-menu .item.unread .title { color: #e8e8ea; font-weight: 600; }
      .notif-menu .item .meta { color: #8a9099; margin-top: 2px; font-size: 11px; }
    `;
    document.head.appendChild(style);
  }

  function loadMarket() {
    try {
      const data = JSON.parse(localStorage.getItem(MARKET_KEY) || "");
      if (data && data.v === 1 && Array.isArray(data.listings)) {
        if (!Array.isArray(data.notifications)) data.notifications = [];
        return data;
      }
    } catch {}
    return { v: 1, listings: [], offers: [], notifications: [], trades: [], seeded: false };
  }

  function saveMarket(data) {
    if (!Array.isArray(data.notifications)) data.notifications = [];
    localStorage.setItem(MARKET_KEY, JSON.stringify(data));
  }

  function uid() {
    return getUserId() || "u1";
  }

  function myNotifications() {
    const me = uid();
    return loadMarket().notifications.filter(n => !n.toUser || n.toUser === me);
  }

  function unreadCount() {
    return myNotifications().filter(n => !n.read).length;
  }

  function ensureMount() {
    let wrap = document.getElementById("notifWrap");
    if (wrap) return wrap;

    const host =
      document.getElementById("notifMount") ||
      document.querySelector(".top-actions");
    if (!host) return null;

    wrap = document.createElement("div");
    wrap.className = "notif-wrap";
    wrap.id = "notifWrap";
    wrap.innerHTML = `
      <button type="button" class="notif-btn" id="notifBtn" aria-label="Notifications" title="Notifications" aria-expanded="false" aria-haspopup="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M15 17h5l-1.4-1.4A2 2 0 0 1 18 14.2V11a6 6 0 1 0-12 0v3.2a2 2 0 0 1-.6 1.4L4 17h5"/>
          <path d="M9.5 17a2.5 2.5 0 0 0 5 0"/>
        </svg>
        <span class="notif-dot" id="notifDot" hidden></span>
      </button>
      <div class="notif-menu" id="notifMenu" role="menu" hidden>
        <div class="head">
          <span>Notifications</span>
          <button type="button" class="mark-all" id="notifMarkAll" hidden>Tout marquer lu</button>
        </div>
        <div id="notifList"><p class="empty">Aucune notification.</p></div>
      </div>
    `;

    if (host.id === "notifMount") {
      host.appendChild(wrap);
    } else {
      host.insertBefore(wrap, host.firstChild);
    }
    return wrap;
  }

  function renderMenu() {
    const list = document.getElementById("notifList");
    if (!list) return;
    const notes = myNotifications().slice(0, 12);
    const markAll = document.getElementById("notifMarkAll");
    if (markAll) markAll.hidden = notes.length < 1;
    if (!notes.length) {
      list.innerHTML = `<p class="empty">Aucune notification.</p>`;
      return;
    }
    list.innerHTML = notes.map(n =>
      `<button type="button" class="item${n.read ? "" : " unread"}" role="menuitem" data-nid="${esc(n.id)}" data-ntype="${esc(n.type)}">
        <div class="title">${esc(n.title)}</div>
        <div class="meta">${esc(n.meta || "")}</div>
      </button>`
    ).join("");
  }

  function refreshBadge() {
    const unread = unreadCount();
    const btn = document.getElementById("notifBtn");
    const dot = document.getElementById("notifDot");
    if (btn) {
      btn.classList.toggle("has-unread", unread > 0);
      btn.setAttribute(
        "aria-label",
        unread < 1
          ? "Notifications"
          : unread === 1
            ? "1 notification non lue"
            : `${unread} notifications non lues`
      );
    }
    if (dot) dot.hidden = unread < 1;
    const wrap = document.getElementById("notifWrap");
    if (!(wrap && wrap.classList.contains("open"))) renderMenu();
  }

  function setOpen(open) {
    const wrap = document.getElementById("notifWrap");
    const btn = document.getElementById("notifBtn");
    const menu = document.getElementById("notifMenu");
    if (!wrap || !btn || !menu) return;
    wrap.classList.toggle("open", open);
    btn.setAttribute("aria-expanded", open ? "true" : "false");
    menu.hidden = !open;
    if (open) renderMenu();
  }

  function markAllRead() {
    const m = loadMarket();
    const me = uid();
    let dirty = false;
    for (const n of m.notifications || []) {
      if (n.toUser && n.toUser !== me) continue;
      if (!n.read) {
        n.read = true;
        dirty = true;
      }
    }
    if (dirty) saveMarket(m);
    refreshBadge();
    renderMenu();
  }

  function tabForNote(note) {
    if (!note) return "all";
    if (note.type === "sold") return "mine";
    if (
      note.type === "offer" ||
      note.type === "trade" ||
      note.type === "offer_accepted" ||
      note.type === "offer_rejected"
    ) return "offers";
    if (note.type === "trade_accepted" || note.type === "trade_rejected") return "trades";
    return "all";
  }

  function marketUrl(tab) {
    const t = tab && tab !== "all" ? `?mtab=${encodeURIComponent(tab)}` : "";
    return `${marketBase}${t}#marche`;
  }

  function openNotification(nid) {
    const m = loadMarket();
    const note = (m.notifications || []).find(n => n.id === nid);
    if (!note) return;
    if (!note.read) {
      note.read = true;
      saveMarket(m);
    }
    if (note.type === "offer" && note.offerId) {
      const offer = (m.offers || []).find(o => o.id === note.offerId);
      if (offer && !offer.seenBySeller) {
        offer.seenBySeller = true;
        saveMarket(m);
      }
    }
    if (note.type === "trade" && note.tradeId) {
      const trade = (m.trades || []).find(t => t.id === note.tradeId);
      if (trade && !trade.seenByTarget) {
        trade.seenByTarget = true;
        saveMarket(m);
      }
    }
    refreshBadge();
    setOpen(false);
    location.href = marketUrl(tabForNote(note));
  }

  function refresh() {
    ensureStyles();
    if (!document.getElementById("notifWrap")) ensureMount();
    refreshBadge();
  }

  function bind(opts) {
    ensureStyles();
    if (opts && typeof opts.getUserId === "function") getUserId = opts.getUserId;
    if (opts && typeof opts.marketBase === "string") marketBase = opts.marketBase;
    // Ne pas écraser l’UI déjà présente sur booster/marché.
    if (document.getElementById("notifWrap") && !document.getElementById("notifMount") && !opts?.forceMount) {
      // Page booster : laisser la logique locale. On peut quand même refresh badge si demandé.
      return;
    }
    ensureMount();
    if (bound) {
      refresh();
      return;
    }
    bound = true;

    document.getElementById("notifBtn")?.addEventListener("click", ev => {
      ev.stopPropagation();
      const wrap = document.getElementById("notifWrap");
      setOpen(!(wrap && wrap.classList.contains("open")));
    });
    document.getElementById("notifMenu")?.addEventListener("click", ev => {
      ev.stopPropagation();
      if (ev.target.closest("#notifMarkAll")) {
        markAllRead();
        return;
      }
      const item = ev.target.closest("[data-nid]");
      if (!item) return;
      openNotification(item.dataset.nid);
    });
    document.addEventListener("click", ev => {
      const wrap = document.getElementById("notifWrap");
      if (!wrap || !wrap.classList.contains("open")) return;
      if (wrap.contains(ev.target)) return;
      setOpen(false);
    });
    document.addEventListener("keydown", ev => {
      if (ev.key === "Escape") setOpen(false);
    });
    window.addEventListener("storage", ev => {
      if (ev.key === MARKET_KEY) refreshBadge();
    });

    refresh();
  }

  window.ChartsNotif = {
    bind,
    refresh,
    MARKET_HREF
  };
})();
