(() => {
  "use strict";
  const search = document.querySelector("#glossary-search");
  if (!search) return;
  const terms = [...document.querySelectorAll(".glossary-term")];
  const filter = () => {
    const query = search.value.trim().toLocaleLowerCase("en");
    let matches = 0;
    for (const term of terms) {
      term.hidden = !term.textContent.toLocaleLowerCase("en").includes(query);
      if (!term.hidden) matches++;
    }
    document.querySelector("#glossary-count").textContent = matches + " of " + terms.length + " terms";
    document.querySelector("#glossary-empty").hidden = matches !== 0;
  };
  search.addEventListener("input", filter);
  const followHash = () => {
    let hash;
    try { hash = decodeURIComponent(location.hash.slice(1)); } catch { return; }
    const target = document.getElementById(hash);
    if (target?.classList.contains("glossary-term")) { search.value = ""; filter(); target.scrollIntoView(); }
  };
  window.addEventListener("hashchange", followHash);
  followHash();
})();
