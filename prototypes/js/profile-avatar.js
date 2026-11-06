/**
 * Photo de profil uploadable (localStorage, par joueur).
 * Attendu dans le DOM :
 *  - [data-avatar-face] : pastilles d’aperçu (menu + tiroir)
 *  - #avatarFile : input file accept="image/*" (souvent dans un label.avatar-pick)
 *  - #avatarStatus : message d’erreur (optionnel)
 *
 * Appeler ChartsAvatar.refresh(userId) après un switch de compte.
 */
(function () {
  const MAX_EDGE = 256;
  const MAX_CHARS = 220000;
  const STYLE_ID = "charts-avatar-css";

  function avatarKey(userId) {
    return `charts.s1.${userId || "u1"}.avatar`;
  }

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      .avatar-block { margin: 0 0 18px; }
      .avatar-pick {
        display: inline-flex;
        cursor: pointer;
        border-radius: 50%;
      }
      .avatar-pick:focus-within .avatar-face {
        border-color: #e68a1e;
      }
      .avatar-face {
        width: 72px; height: 72px; border-radius: 50%;
        background: #141414 center/cover no-repeat;
        border: 1px solid #3a3a3a;
        flex: 0 0 auto;
        overflow: hidden;
        position: relative;
        display: block;
      }
      .avatar-face.empty {
        background:
          radial-gradient(circle at 50% 36%, #3a3a3a 0 28%, transparent 29%),
          radial-gradient(ellipse at 50% 88%, #3a3a3a 0 42%, transparent 43%),
          #141414;
      }
      .avatar-face.sm {
        width: 22px; height: 22px; border-width: 1px;
      }
      .avatar-face.sm.empty {
        background: transparent;
        border-color: transparent;
      }
      .avatar-status {
        margin: 8px 0 0;
        font-family: "IBM Plex Mono", ui-monospace, monospace;
        font-size: 11px;
        letter-spacing: .04em;
        color: #e05050;
      }
      .avatar-status:empty { display: none; }
      #menuBtn .avatar-face.sm { margin-right: 2px; }
      #menuBtn .ico[data-avatar-fallback] { display: none; }
      #menuBtn.no-avatar .avatar-face.sm { display: none; }
      #menuBtn.no-avatar .ico[data-avatar-fallback] { display: block; }
    `;
    document.head.appendChild(style);
  }

  function get(userId) {
    try {
      const raw = localStorage.getItem(avatarKey(userId));
      if (raw && raw.startsWith("data:image/")) return raw;
    } catch {}
    return "";
  }

  function set(userId, dataUrl) {
    if (!dataUrl) {
      localStorage.removeItem(avatarKey(userId));
      return true;
    }
    if (dataUrl.length > MAX_CHARS) return false;
    localStorage.setItem(avatarKey(userId), dataUrl);
    return true;
  }

  function setStatus(msg) {
    const el = document.getElementById("avatarStatus");
    if (el) el.textContent = msg || "";
  }

  function refresh(userId) {
    ensureStyles();
    const url = get(userId);
    document.querySelectorAll("[data-avatar-face]").forEach(el => {
      if (url) {
        el.style.backgroundImage = `url("${url}")`;
        el.classList.remove("empty");
      } else {
        el.style.backgroundImage = "";
        el.classList.add("empty");
      }
    });
    const menu = document.getElementById("menuBtn");
    if (menu) menu.classList.toggle("no-avatar", !url);
    setStatus("");
  }

  function readFileAsDataUrl(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || ""));
      reader.onerror = () => reject(new Error("read"));
      reader.readAsDataURL(file);
    });
  }

  function loadImage(src) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error("img"));
      img.src = src;
    });
  }

  async function compress(file) {
    const raw = await readFileAsDataUrl(file);
    const img = await loadImage(raw);
    const scale = Math.min(1, MAX_EDGE / Math.max(img.width, img.height));
    const w = Math.max(1, Math.round(img.width * scale));
    const h = Math.max(1, Math.round(img.height * scale));
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(img, 0, 0, w, h);
    let quality = 0.84;
    let out = canvas.toDataURL("image/jpeg", quality);
    while (out.length > MAX_CHARS && quality > 0.45) {
      quality -= 0.12;
      out = canvas.toDataURL("image/jpeg", quality);
    }
    if (out.length > MAX_CHARS) throw new Error("too-big");
    return out;
  }

  let bound = false;
  let getUserId = () => "u1";

  function bind(opts) {
    ensureStyles();
    if (opts && typeof opts.getUserId === "function") getUserId = opts.getUserId;
    if (bound) {
      refresh(getUserId());
      return;
    }
    bound = true;

    const file = document.getElementById("avatarFile");
    if (file) {
      file.addEventListener("change", async () => {
        const picked = file.files && file.files[0];
        file.value = "";
        if (!picked) return;
        if (!picked.type.startsWith("image/")) {
          setStatus("Choisis une image (JPG, PNG…).");
          return;
        }
        try {
          const dataUrl = await compress(picked);
          if (!set(getUserId(), dataUrl)) {
            setStatus("Image trop lourde après compression.");
            return;
          }
          refresh(getUserId());
          if (typeof opts?.onChange === "function") opts.onChange(getUserId());
        } catch {
          setStatus("Impossible de lire cette image.");
        }
      });
    }

    refresh(getUserId());
  }

  window.ChartsAvatar = { get, set, refresh, bind };
})();
