/**
 * Boutique de crédits : clic sur l'encart CR du header → popin d'achat (argent réel).
 *
 * Prototype : aucun paiement réel n'est déclenché, le pack crédite le wallet local.
 * Après achat, `charts:credits-changed` est émis pour que la page rafraîchisse son solde.
 */
(function () {
  const ACTIVE_USER_KEY = "charts.s1.activeUser";

  const PACKS = [
    { id: "p1", credits: 100, price: "0,99 €" },
    { id: "p2", credits: 550, price: "4,99 €", bonus: "+10 %" },
    { id: "p3", credits: 1200, price: "9,99 €", bonus: "+20 %", best: true },
    { id: "p4", credits: 3300, price: "24,99 €", bonus: "+32 %" }
  ];

  function uid() {
    const saved = localStorage.getItem(ACTIVE_USER_KEY);
    return saved === "u2" ? "u2" : "u1";
  }

  function walletKey(userId) {
    return `charts.s1.${userId || uid()}.wallet`;
  }

  function loadWallet() {
    try {
      const data = JSON.parse(localStorage.getItem(walletKey()) || "");
      if (data && typeof data === "object") return data;
    } catch {}
    return { v: 1, credits: 0, packs: 0, nextFreeAt: 0, starter: false };
  }

  function addCredits(n) {
    const w = loadWallet();
    w.v = 1;
    w.credits = Math.max(0, Number(w.credits) || 0) + n;
    localStorage.setItem(walletKey(), JSON.stringify(w));
    return w.credits;
  }

  function fmt(n) {
    return Number(n || 0).toLocaleString("fr-FR");
  }

  function injectStyle() {
    if (document.getElementById("credits-shop-style")) return;
    const style = document.createElement("style");
    style.id = "credits-shop-style";
    style.textContent = `
      #creditsShop {
        border: 1px solid #2a2c32; border-radius: 12px; padding: 0;
        background: #121418; color: #e8e8ea;
        width: min(420px, calc(100vw - 32px));
      }
      #creditsShop::backdrop { background: rgba(0,0,0,.6); }
      #creditsShop .cs-wrap { padding: 18px; }
      #creditsShop .cs-head {
        display: flex; align-items: flex-start; justify-content: space-between; gap: 12px;
      }
      #creditsShop h2 {
        margin: 0; font-family: Oswald, sans-serif; font-size: 18px;
        font-weight: 500; letter-spacing: .08em; text-transform: uppercase;
      }
      #creditsShop .cs-close {
        appearance: none; background: none; border: 0; cursor: pointer;
        color: #9aa0a8; font: inherit; font-size: 22px; line-height: 1;
        width: 32px; height: 32px; padding: 0; margin: -4px -4px 0 0;
      }
      #creditsShop .cs-close:hover { color: #e8e8ea; }
      #creditsShop .cs-bal {
        margin: 4px 0 14px; font-family: "IBM Plex Mono", ui-monospace, monospace;
        font-size: 11px; letter-spacing: .06em; text-transform: uppercase; color: #8a9099;
      }
      #creditsShop .cs-list { display: flex; flex-direction: column; gap: 8px; }
      #creditsShop .cs-pack {
        appearance: none; cursor: pointer; width: 100%; text-align: left;
        display: flex; align-items: center; gap: 12px;
        border: 1px solid #2a2c32; background: #161616; color: inherit;
        padding: 12px 14px; font: inherit;
      }
      #creditsShop .cs-pack:hover { border-color: #3a3c44; background: #1c1c1c; }
      #creditsShop .cs-pack .cs-ticket { width: 30px; height: 19px; flex: 0 0 auto; }
      #creditsShop .cs-pack .cs-amount {
        flex: 1 1 auto; font-family: Oswald, sans-serif;
        font-size: 15px; font-weight: 600; letter-spacing: .04em;
      }
      #creditsShop .cs-pack .cs-tag {
        font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 10px;
        letter-spacing: .08em; text-transform: uppercase; color: #d8b35c;
      }
      #creditsShop .cs-pack .cs-price {
        font-family: "IBM Plex Mono", ui-monospace, monospace;
        font-size: 12px; color: #e8e8ea; white-space: nowrap;
      }
      #creditsShop .cs-pack.best { border-color: #d8b35c; }
      #creditsShop .cs-note {
        margin: 14px 0 0; font-family: "IBM Plex Mono", ui-monospace, monospace;
        font-size: 10px; line-height: 1.5; letter-spacing: .04em; color: #6a7078;
      }
    `;
    document.head.appendChild(style);
  }

  function ensureDialog() {
    let dlg = document.getElementById("creditsShop");
    if (dlg) return dlg;

    injectStyle();
    dlg = document.createElement("dialog");
    dlg.id = "creditsShop";
    dlg.innerHTML = `
      <div class="cs-wrap">
        <div class="cs-head">
          <h2>Acheter des crédits</h2>
          <button type="button" class="cs-close" data-cs-close aria-label="Fermer">×</button>
        </div>
        <p class="cs-bal" data-cs-balance></p>
        <div class="cs-list">
          ${PACKS.map(p => `
            <button type="button" class="cs-pack${p.best ? " best" : ""}" data-cs-pack="${p.id}">
              <img class="cs-ticket" src="img/credit-ticket.png?v=1" alt="" aria-hidden="true">
              <span class="cs-amount">${fmt(p.credits)} CR</span>
              ${p.bonus ? `<span class="cs-tag">${p.bonus}</span>` : ""}
              <span class="cs-price">${p.price}</span>
            </button>
          `).join("")}
        </div>
        <p class="cs-note">Prototype : aucun paiement réel n’est effectué, les crédits sont ajoutés immédiatement.</p>
      </div>
    `;
    document.body.appendChild(dlg);

    dlg.addEventListener("click", ev => {
      if (ev.target.closest("[data-cs-close]")) {
        dlg.close();
        return;
      }
      const btn = ev.target.closest("[data-cs-pack]");
      if (!btn) return;
      const pack = PACKS.find(p => p.id === btn.dataset.csPack);
      if (!pack) return;
      const credits = addCredits(pack.credits);
      document.dispatchEvent(new CustomEvent("charts:credits-changed", { detail: { credits } }));
      dlg.close();
    });

    return dlg;
  }

  function refreshBalance(dlg) {
    const el = dlg.querySelector("[data-cs-balance]");
    if (el) el.textContent = `Solde actuel : ${fmt(loadWallet().credits)} CR`;
  }

  function open() {
    const dlg = ensureDialog();
    refreshBalance(dlg);
    if (!dlg.open) dlg.showModal();
  }

  function chipOf(target) {
    return target.closest?.(".top-actions .chip[aria-label='Crédits'], .top-actions .wallet-chip");
  }

  function bind() {
    document.querySelectorAll(".top-actions .chip[aria-label='Crédits'], .top-actions .wallet-chip")
      .forEach(chip => {
        chip.style.cursor = "pointer";
        chip.setAttribute("role", "button");
        chip.setAttribute("tabindex", "0");
        chip.setAttribute("title", "Acheter des crédits");
      });

    document.addEventListener("click", ev => {
      if (chipOf(ev.target)) open();
    });
    document.addEventListener("keydown", ev => {
      if (ev.key !== "Enter" && ev.key !== " ") return;
      if (!chipOf(ev.target)) return;
      ev.preventDefault();
      open();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind, { once: true });
  } else {
    bind();
  }

  window.ChartsCreditsShop = { open };
})();
