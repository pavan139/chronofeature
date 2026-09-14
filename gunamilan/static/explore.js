/* Shared explanation UI. No external requests, generated predictions or storage. */
(() => {
  "use strict";
  const el = (tag, text, cls) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  };
  const keyOf = value => value.toLowerCase().replace(/[ _]/g, "-");
  const english = node => { node.lang = "en"; node.dir = "ltr"; return node; };
  function boot(t) {
    const knowledge = JSON.parse(document.querySelector("#knowledge").textContent);
    const dialog = document.querySelector("#help-dialog"), search = document.querySelector("#help-search");
    const results = document.querySelector("#help-results"), topic = document.querySelector("#help-topic");
    let opener, selectedKey = "birth-time", queryWords = [];
    // Native buttons retain their normal Tab behavior. Arrow keys are an optional shortcut.
    function keyboardGroup(container) {
      container.addEventListener("keydown", event => {
        if (!['ArrowDown','ArrowUp','ArrowLeft','ArrowRight','Home','End'].includes(event.key) || event.altKey || event.ctrlKey || event.metaKey) return;
        const items = [...container.querySelectorAll("button")];
        const index = items.indexOf(event.target);
        if (index < 0 || !items.length) return;
        event.preventDefault();
        const next = event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1 :
          (index + (['ArrowDown','ArrowRight'].includes(event.key) ? 1 : -1) + items.length) % items.length;
        items[next].focus();
      });
    }
    keyboardGroup(results);
    search.addEventListener("keydown", event => {
      if (event.key === "ArrowDown" && results.firstElementChild) {
        event.preventDefault(); results.firstElementChild.focus();
      }
    });
    const preferences = english(el("fieldset", undefined, "reading-preferences"));
    preferences.append(el("legend", "Reading comfort"));
    for (const [key, title] of [["quiet", "Turn off animations"], ["largeText", "Larger report text"]]) {
      const label = el("label"), input = el("input"); input.type = "checkbox";
      input.dataset.preference = key;
      input.checked = document.documentElement.dataset[key] === "true";
      input.addEventListener("change", () => { document.documentElement.dataset[key] = String(input.checked); });
      label.append(input, document.createTextNode(title)); preferences.append(label);
    }
    preferences.append(el("small", "Device reduced-motion settings are always respected. Preferences last until you reload."));
    dialog.append(preferences);
    const termMatches = item => queryWords.every(word => (item.title + " " + item.meaning + " " + item.next_step + " " + item.group).toLowerCase().includes(word));
    function showTerm(key) {
      const item = knowledge[key];
      if (!item) return;
      selectedKey = key;
      topic.replaceChildren(el("span", item.group, "eyebrow"), el("h3", item.title), el("p", item.meaning));
      const next = el("div", undefined, "help-next");
      next.append(el("h4", "Try this"), el("p", item.next_step)); topic.append(next);
      const link = el("a", "Open full glossary (new tab) ↗");
      link.href = "/en/guide/#" + key; link.target = "_blank"; link.rel = "noopener"; topic.append(link);
      results.querySelectorAll("button").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.term === key)));
    }
    function filter() {
      const stopWords = new Set(["what","does","is","a","an","the","how","do","i","my","mean","means","can","you","explain","please","tell","me","about","why","are","for","to"]);
      queryWords = search.value.toLowerCase().replace(/[^\p{L}\p{N}\s]/gu," ").trim().split(/\s+/).filter(word => word && !stopWords.has(word));
      const matches = Object.entries(knowledge).filter(([, item]) => termMatches(item));
      const query = queryWords.join(" ");
      const rank = item => item.title.toLowerCase() === query ? 3 : item.title.toLowerCase().startsWith(query) ? 2 : item.title.toLowerCase().includes(query) ? 1 : 0;
      if (query) matches.sort((a,b) => rank(b[1]) - rank(a[1]));
      results.replaceChildren();
      for (const [key, item] of matches) {
        const button = english(el("button", item.title, "help-term"));
        button.type = "button"; button.dataset.term = key;
        button.addEventListener("click", () => showTerm(key)); results.append(button);
      }
      if (matches.length) showTerm(!query && matches.some(([key]) => key === selectedKey) ? selectedKey : matches[0][0]);
      else topic.replaceChildren(el("h3", "No matching term"), el("p", "Try a shorter term such as Moon, time, score or PDF. This is a glossary search, not a chatbot."));
      const count = document.querySelector("#help-count"); count.lang = "en"; count.dir = "ltr";
      count.textContent = matches.length + " of " + Object.keys(knowledge).length + " terms";
    }
    function openHelp(key, trigger) {
      selectedKey = knowledge[key] ? key : "birth-time"; search.value = ""; filter();
      opener = trigger || document.activeElement;
      if (!dialog.open) dialog.showModal();
      search.focus(); results.querySelector('[aria-pressed="true"]')?.scrollIntoView({block:"nearest"});
    }
    document.querySelector("#help-close").addEventListener("click", () => dialog.close());
    dialog.addEventListener("close", () => { if (opener?.isConnected) opener.focus({preventScroll:true}); });
    dialog.addEventListener("keydown", event => {
      if (event.key === "Escape") {
        event.preventDefault(); event.stopPropagation(); dialog.close();
      }
    });
    dialog.addEventListener("click", event => {
      if (event.target !== dialog) return;
      const rect = dialog.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
    });
    search.addEventListener("input", filter);
    document.body.addEventListener("click", event => {
      const button = event.target.closest("[data-help]");
      if (button) openHelp(button.hasAttribute("data-chart-help") ? "graha" : button.dataset.help, button);
      const jump = event.target.closest("[data-jump]");
      if (!jump) return;
      const target = document.getElementById(jump.dataset.jump);
      if (!target) return;
      const parent = target.closest(".report-section");
      if (parent) {
        parent.open = true;
        const filter = parent.querySelector(".factor-filter input");
        if (filter) { filter.checked = false; filter.dispatchEvent(new Event("change")); }
      }
      target.hidden = false; target.open = true;
      target.querySelector("summary")?.focus(); target.scrollIntoView({block:"center", behavior:"auto"});
    });
    document.body.addEventListener("keydown", event => {
      if (event.key === "?" && !event.ctrlKey && !event.metaKey && !event.altKey &&
          !event.target.closest("input,textarea,select,[contenteditable=true]") && !dialog.open) {
        event.preventDefault(); openHelp("birth-time");
      }
    });
    const helpButton = key => {
      const item = knowledge[key];
      const button = el("button", "?", "help-button"); button.type = "button"; button.dataset.help = key;
      button.setAttribute("aria-label", t.help + ": " + (item?.title || key)); return button;
    };
    function definition(name) {
      const key = keyOf(name), item = knowledge[key];
      if (!item) return null;
      const div = english(el("div", undefined, "definition"));
      div.append(el("h4", "What this means"), el("p", item.meaning), el("h4", "Try this"), el("p", item.next_step));
      return div;
    }
    function matchOverview(analysis) {
      const section = el("section", undefined, "analysis-overview");
      const heading = el("div", undefined, "section-heading"); heading.append(el("h3", t.summary), helpButton("ashtakoota")); section.append(heading);
      const body = english(el("div"));
      body.append(el("p", analysis.summary, "analysis-lead"), el("p", analysis.accuracy, "accuracy-line"));
      const grid = el("div", undefined, "insight-grid");
      const groups = [["Full-point factors", analysis.full_points, "strength-card"], ["Where points differ", analysis.review_factors, "review-insight"]];
      for (const [title, rows, cls] of groups) {
        const card = el("article", undefined, "insight-card " + cls); card.append(el("h4", title));
        if (!rows.length) card.append(el("p", title === "Full-point factors" ? "No factor received its full points." : "Every included factor received full points."));
        for (const row of rows) {
          const button = el("button", undefined, "insight-link"); button.type = "button"; button.dataset.jump = "factor-" + row.system + "-" + row.key;
          button.append(el("span", row.name), el("b", row.score + " / " + row.maximum));
          card.append(button);
        }
        grid.append(card);
      }
      body.append(grid);
      const flags = el("div", undefined, "essential-review");
      flags.append(el("h4", "Essential checks"), el("p", analysis.essential_flags.length ? analysis.essential_flags.join(" · ") : "No essential review flags under the implemented rules. This is not a guarantee of an outcome."));
      for (const exception of analysis.exceptions) flags.append(el("p", exception.name + " exception: " + exception.text));
      flags.append(el("small", "Exceptions can remove a flag without restoring points.")); body.append(flags);
      body.append(el("p", analysis.context, "analysis-context")); section.append(body); return section;
    }
    function factorControls(section) {
      const label = english(el("label", undefined, "factor-filter"));
      const input = el("input"); input.type = "checkbox";
      label.append(input, document.createTextNode("Show only factors to review"));
      const count = english(el("p", "", "factor-count")); count.setAttribute("role", "status");
      input.addEventListener("change", () => {
        let shown = 0;
        const factors = section.querySelectorAll("[data-factor-state]");
        factors.forEach(item => { item.hidden = input.checked && item.dataset.factorState === "full"; if (!item.hidden) shown++; });
        count.textContent = input.checked ? shown + " of " + factors.length + " factors need review" : "";
      });
      section.prepend(label, count);
    }
    function chartExplorer(chart) {
      const section = el("section", undefined, "chart-explorer");
      section.append(el("h4", t.chartExplorer));
      const info = chart.analysis;
      if (info) {
        const highlights = english(el("div", undefined, "chart-highlights"));
        for (const item of info.highlights) {
          const card = el("article"); card.append(el("span", item.title), el("h4", item.value), el("p", item.detail), helpButton(item.key)); highlights.append(card);
        }
        section.append(highlights);
      }
      const layout = el("div", undefined, "chart-map-layout"), diagram = el("div", undefined, "chart-diagram");
      const NS = "http://www.w3.org/2000/svg";
      const svg = (tag, attrs, text) => {
        const node = document.createElementNS(NS, tag);
        Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
        if (text !== undefined) node.textContent = text; return node;
      };
      const wheel = svg("svg", {viewBox:"0 0 400 400",role:"img","aria-label":"Sidereal longitude diagram. Exact positions are available in the adjacent controls and table.",lang:"en"});
      const point = (angle, r) => { const a = (angle - 90) * Math.PI / 180; return [200 + Math.cos(a) * r, 200 + Math.sin(a) * r]; };
      [174,145,65].forEach(r => wheel.append(svg("circle", {cx:200,cy:200,r,class:"chart-ring"})));
      const signs = ["ARI","TAU","GEM","CAN","LEO","VIR","LIB","SCO","SAG","CAP","AQU","PIS"];
      for (let i = 0; i < 12; i++) {
        const [x1,y1] = point(i*30,65), [x2,y2] = point(i*30,174), [x,y] = point(i*30+15,159);
        wheel.append(svg("line",{x1,y1,x2,y2,class:"chart-spoke"}),svg("text",{x,y,"text-anchor":"middle","dominant-baseline":"central",class:"chart-sign"},signs[i]));
      }
      wheel.append(svg("text",{x:200,y:190,"text-anchor":"middle",class:"chart-center"},"D1"),svg("text",{x:200,y:216,"text-anchor":"middle",class:"chart-center-caption"},"SIDEREAL"));
      const ray = svg("line",{x1:200,y1:200,x2:200,y2:60,class:"chart-ray"}); wheel.append(ray);
      const dots = [];
      (chart.grahas || []).forEach((g,i) => {
        const [cx,cy] = point(g.longitude,82+i*6.5);
        const dot = svg("circle",{cx,cy,r:4,class:"chart-planet"}); dot.append(svg("title",{},g.name+": "+g.longitude+"°")); wheel.append(dot); dots.push(dot);
      });
      diagram.append(wheel); layout.append(diagram);
      const inspect = english(el("div", undefined, "planet-inspector")), buttons = el("div", undefined, "planet-buttons"), detail = el("div", undefined, "planet-detail");
      buttons.setAttribute("role","group"); buttons.setAttribute("aria-label","Choose a graha"); detail.setAttribute("aria-live","polite");
      keyboardGroup(buttons);
      function select(g,i) {
        [...buttons.children].forEach((button,index) => button.setAttribute("aria-pressed",String(index===i)));
        dots.forEach((dot,index) => dot.setAttribute("class", index===i ? "chart-planet selected" : "chart-planet"));
        const [x1,y1] = point(g.longitude,65), [x2,y2] = point(g.longitude,142);
        ray.setAttribute("x1",x1); ray.setAttribute("y1",y1); ray.setAttribute("x2",x2); ray.setAttribute("y2",y2);
        detail.replaceChildren(el("span", "POSITION / " + g.name, "eyebrow"), el("h4",g.rashi),el("p",g.degrees + " · " + g.nakshatra + " · Pada " + g.pada));
        const dl = el("dl");
        for (const [name,value,key] of [["Sidereal longitude",g.longitude+"°","longitude"],["Navamsa",g.navamsa,"navamsa"],["House",g.house ?? "Unknown time","house"],["Dignity",g.dignity || "Not specified","dignity"],["Retrograde",g.retrograde?"Yes":"No","retrograde"],["Combust",g.combust?"Yes":"No","combust"]]) {
          const row = el("div"), dt = el("dt",name); dt.append(helpButton(key)); row.append(dt,el("dd",value)); dl.append(row);
        }
        detail.append(dl);
      }
      (chart.grahas || []).forEach((g,i) => {
        const button = el("button",g.name); button.type = "button";
        button.addEventListener("click",()=>select(g,i)); buttons.append(button);
      });
      inspect.append(buttons,detail); layout.append(inspect); section.append(layout);
      if(chart.grahas?.length) select(chart.grahas.find(g=>g.name==="Moon") || chart.grahas[0],Math.max(0,chart.grahas.findIndex(g=>g.name==="Moon")));
      const caption = english(el("p","Positions are angular, not physical distances. ARI = Aries through PIS = Pisces. Select a graha for exact values.","chart-caption")); section.append(caption);
      return section;
    }
    function nextSteps(isChart) {
      const section = el("section",undefined,"next-steps"); section.append(el("h3",t.nextSteps));
      const body = english(el("div")); body.append(el("p","A short checklist. Ticks stay in this page only and are not included in exports."));
      const progress = el("progress"); progress.max = 4; progress.value = 0;
      progress.setAttribute("aria-label", "Checklist completion");
      const status = el("p", "0 of 4 complete", "checklist-status"); status.setAttribute("role", "status");
      body.append(progress, status);
      const steps = isChart ? ["Check the birth record, timezone and ayanamsa.","Explore the Moon, Sun and ascendant separately.","Read unknown-time and timing limits before using a date.","Download the PDF and keep the file private."] :
        ["Verify both birth records and calculation settings.","Open essential checks and their exceptions.","Discuss communication, boundaries and shared expectations directly.","Download the report only if both people are comfortable sharing it."];
      for(const text of steps){const label=el("label"),input=el("input");input.type="checkbox";label.append(input,document.createTextNode(text));body.append(label);}
      body.addEventListener("change", () => {
        const count = body.querySelectorAll("input:checked").length;
        progress.value = count; status.textContent = count + " of 4 complete";
      });
      section.append(body); return section;
    }
    function reportNavigation(output) {
      const nav = el("nav", undefined, "report-navigation"); nav.setAttribute("aria-label", t.result || "Report");
      const targets = [...output.querySelectorAll(".analysis-overview, .report-section, .chart-explorer, .next-steps")];
      for (const target of targets) {
        if (target.classList.contains("chart-explorer") && target.closest(".report-section")) continue;
        const heading = target.querySelector("summary, h3, h4");
        if (!heading) continue;
        const label = heading.cloneNode(true); label.querySelectorAll("button").forEach(button => button.remove());
        const button = el("button", label.textContent.trim()); button.type = "button";
        button.addEventListener("click", () => {
          if (target.tagName === "DETAILS") target.open = true;
          let parent = target.parentElement;
          while (parent && parent !== output) { if (parent.tagName === "DETAILS") parent.open = true; parent = parent.parentElement; }
          heading.tabIndex = -1; heading.focus({preventScroll:true});
          target.scrollIntoView({block:"start", behavior:"auto"});
        });
        nav.append(button);
      }
      output.prepend(nav);
    }
    function capture() { return [...document.querySelectorAll(".next-steps input")].map(input => input.checked); }
    function restore(ticks) {
      document.querySelectorAll(".next-steps input").forEach((input, index) => { input.checked = Boolean(ticks?.[index]); });
      document.querySelector(".next-steps input")?.dispatchEvent(new Event("change", {bubbles:true}));
    }
    function provenance(data) {
      const item = english(el("p",undefined,"report-provenance"));
      item.append(document.createTextNode("CALCULATION / Swiss Ephemeris · " + (data.ayanamsa || "lahiri") + " · Whole-sign houses · Definitions in English "),helpButton("birth-time")); return item;
    }
    return {definition,helpButton,matchOverview,factorControls,chartExplorer,nextSteps,provenance,reportNavigation,capture,restore};
  }
  window.AstroExplore = {boot};
})();
