/* Force l’échelle UI globale sur <html> uniquement (évite le double zoom). */
(function () {
  var s = "0.82";
  try {
    document.documentElement.style.zoom = s;
  } catch (e) {}
})();
