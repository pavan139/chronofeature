(() => {
  "use strict";
  let generation = 0, navigation = 0, cleanup = () => {}, capture = () => ({}), installPrompt = null;
  if (matchMedia("(prefers-color-scheme: dark)").matches) document.documentElement.dataset.theme = "dark";
  window.addEventListener("beforeinstallprompt", event => {
    event.preventDefault(); installPrompt = event;
    document.querySelector("#install-app")?.removeAttribute("hidden");
  });
  window.addEventListener("appinstalled", () => {
    installPrompt = null; document.querySelector("#install-app")?.setAttribute("hidden", "");
  });
  const node = (tag, text, cls) => {
    const el = document.createElement(tag);
    if (text !== undefined && text !== null) el.textContent = String(text);
    if (cls) el.className = cls;
    return el;
  };
  function boot(saved) {
    cleanup();
    const version = ++generation;
    const t = Object.fromEntries([...document.querySelectorAll("#messages [data-key]")].map(el => [el.dataset.key, el.textContent]));
    const explorer = window.AstroExplore.boot(t);
    const form = document.querySelector("#birth-form"), reading = document.querySelector("#reading");
    const output = document.querySelector("#report-content"), error = document.querySelector("#form-error");
    const button = form.querySelector('[type="submit"]'), label = button.querySelector(".submit-label");
    const locale = document.documentElement.lang, view = document.body.dataset.view;
    const shareStatus = document.querySelector("#share-status"), installButton = document.querySelector("#install-app");
    let shareSummary = "", lastReport = null, lastRequest = null, lastAyanamsa = "lahiri", calculatedAt = null, pdfController;
    const pdfButton = document.querySelector("#download-pdf"), exportError = document.querySelector("#export-error");
    const toggleDetails = document.querySelector("#toggle-details"), objectUrls = new Set();
    const controllers = new Set(), timers = new Set(), selected = new Map();
    let resultController;
    const workspace = document.querySelector(".workspace"), people = [...form.querySelectorAll("[data-person]")];
    const reviewStep = document.querySelector("#review-step"), reviewPeople = document.querySelector("#review-people");
    const exampleButton = document.querySelector("#try-example"), sampleNotice = document.querySelector("#sample-notice");
    const resetStatus = document.querySelector("#reset-status");
    let step = 0, sample = false, resetSnapshot = null, resetTimer, returnToReview = false;
    const val = name => form.elements.namedItem(name);
    const cleanUrl = () => document.querySelector('link[rel="canonical"]')?.href || location.origin + location.pathname;
    async function share(text = document.title) {
      const data = {title: document.title, text, url: cleanUrl()};
      try {
        if (navigator.share) await navigator.share(data);
        else {
          await navigator.clipboard.writeText(data.text + "\n" + data.url);
          shareStatus.textContent = t.copied;
          const timer = setTimeout(() => shareStatus.textContent = "", 2600); timers.add(timer);
        }
      } catch (err) {
        if (err.name !== "AbortError") shareStatus.textContent = t.copy + ": " + data.url;
      }
    }
    document.querySelector("#share-page").addEventListener("click", () => share());
    document.querySelector("#share-result").addEventListener("click", () => share(shareSummary || document.title));
    document.querySelector("#theme-toggle").setAttribute("aria-pressed", String(document.documentElement.dataset.theme === "dark"));
    document.querySelector('meta[name="theme-color"]').content = document.documentElement.dataset.theme === "dark" ? "#18152b" : "#5b38df";
    document.querySelector("#theme-toggle").addEventListener("click", () => {
      const dark = document.documentElement.dataset.theme !== "dark";
      if (dark) document.documentElement.dataset.theme = "dark";
      else delete document.documentElement.dataset.theme;
      document.querySelector("#theme-toggle").setAttribute("aria-pressed", String(dark));
      document.querySelector('meta[name="theme-color"]').content = dark ? "#18152b" : "#5b38df";
    });
    if (installPrompt) installButton.hidden = false;
    installButton.addEventListener("click", async () => {
      if (!installPrompt) return;
      await installPrompt.prompt(); installPrompt = null; installButton.hidden = true;
    });
    const number = value => {
      try { return new Intl.NumberFormat(locale, {maximumFractionDigits: 1}).format(value); }
      catch { return String(value); }
    };
    const date = value => {
      try { return new Intl.DateTimeFormat(locale, {dateStyle: "medium"}).format(new Date(value + "T12:00:00")); }
      catch { return value; }
    };
    cleanup = () => {
      controllers.forEach(c => c.abort("navigation")); timers.forEach(clearTimeout);
      objectUrls.forEach(url => URL.revokeObjectURL(url)); objectUrls.clear();
    };
    capture = () => ({
      fields: [...form.elements].filter(el => el.name).map(el => [el.name, el.type === "checkbox" ? el.checked : el.value]),
      selected: [...selected], open: [...form.querySelectorAll(".coordinates")].map(el => el.open),
      view, report: lastReport, request: lastRequest, ayanamsa: lastAyanamsa, calculatedAt,
      step, sample, returnToReview, showingReport: !reading.hidden
    });
    function forgetUndo() {
      resetSnapshot = null; resetStatus.hidden = true; clearTimeout(resetTimer);
    }
    function updateExample() {
      exampleButton.hidden = people.some(el => [...el.querySelectorAll("input")].some(input =>
        input.type === "checkbox" ? input.checked : input.name.endsWith("-timezone") ? input.value !== "Asia/Kolkata" : input.value.trim()));
      sampleNotice.hidden = !sample;
    }
    function invalidate() {
      reading.hidden = true;
      lastReport = null; lastRequest = null; calculatedAt = null; shareSummary = "";
      if (pdfController) pdfController.abort("edit");
      if (resultController) resultController.abort("edit");
      forgetUndo(); updateExample();
    }
    form.addEventListener("input", invalidate);
    form.addEventListener("change", invalidate);
    const today = new Date();
    const maxDate = today.getFullYear() + "-" + String(today.getMonth() + 1).padStart(2,"0") + "-" + String(today.getDate()).padStart(2,"0");
    const closeMenus = (restoreFocus = false) => document.querySelectorAll(".language-menu,.export-menu").forEach(el => {
      if (restoreFocus && el.open && el.contains(document.activeElement)) el.querySelector("summary").focus();
      el.open = false;
    });
    document.querySelectorAll(".export-options button").forEach(el => el.addEventListener("click", () => closeMenus(true)));
    document.body.addEventListener("pointerdown", event => {
      document.querySelectorAll(".language-menu[open],.export-menu[open]").forEach(el => { if (!el.contains(event.target)) el.open = false; });
    });
    for (const fieldset of form.querySelectorAll("[data-person]")) {
      const person = fieldset.dataset.person, search = val(person + "-place");
      const list = fieldset.querySelector(".suggestions"), status = fieldset.querySelector(".place-status");
      const unknown = val(person + "-unknown"), time = val(person + "-time");
      search.setAttribute("aria-describedby", person + "-place-status");
      val(person + "-date").max = maxDate;
      const close = () => { list.hidden = true; search.setAttribute("aria-expanded", "false"); search.removeAttribute("aria-activedescendant"); };
      unknown.addEventListener("change", () => { time.disabled = unknown.checked; time.required = !unknown.checked; });
      for (const key of ["latitude", "longitude", "timezone"]) val(person + "-" + key).addEventListener("input", () => {
        selected.delete(person); search.value = ""; status.textContent = "";
      });
      let pending, timer, active = -1, results = [];
      function choose(index) {
        const item = results[index];
        if (!item) return;
        selected.set(person, item);
        search.value = item.label;
        val(person + "-latitude").value = item.latitude;
        val(person + "-longitude").value = item.longitude;
        val(person + "-timezone").value = item.timezone;
        status.textContent = item.label + " · " + item.timezone;
        close(); search.focus(); invalidate();
      }
      function highlight(index) {
        active = index;
        [...list.children].forEach((li, i) => li.setAttribute("aria-selected", String(i === active)));
        const option = list.children[active];
        if (option) { search.setAttribute("aria-activedescendant", option.id); option.scrollIntoView({block: "nearest"}); }
      }
      search.addEventListener("keydown", event => {
        if (event.key === "Escape") { close(); return; }
        if (list.hidden) return;
        if (event.key === "ArrowDown" || event.key === "ArrowUp") {
          event.preventDefault();
          const step = event.key === "ArrowDown" ? 1 : -1;
          highlight((active + step + results.length) % results.length);
        }
        if (event.key === "Enter" && active >= 0) { event.preventDefault(); choose(active); }
      });
      search.addEventListener("blur", () => { const id = setTimeout(close, 160); timers.add(id); });
      search.addEventListener("input", () => {
        selected.delete(person);
        val(person + "-latitude").value = ""; val(person + "-longitude").value = "";
        clearTimeout(timer); if (pending) pending.abort(); close(); status.textContent = "";
        const query = search.value.trim();
        if (query.length < 2) return;
        timer = setTimeout(async () => {
          pending = new AbortController(); controllers.add(pending);
          const own = pending;
          status.textContent = t.loading;
          try {
            const response = await fetch("/places?q=" + encodeURIComponent(query) + "&limit=8", {signal: own.signal, cache: "no-store"});
            if (!response.ok) throw new Error("places");
            const data = await response.json();
            if (version !== generation || search.value.trim() !== query) return;
            results = data.results || []; active = -1; list.replaceChildren();
            status.textContent = results.length ? "" : t.unavailable;
            results.forEach((item, i) => {
              const li = node("li", item.label);
              li.id = person + "-option-" + i; li.setAttribute("role", "option"); li.setAttribute("aria-selected", "false");
              li.addEventListener("pointerdown", e => e.preventDefault());
              li.addEventListener("click", () => choose(i)); list.append(li);
            });
            list.hidden = !results.length; search.setAttribute("aria-expanded", String(Boolean(results.length)));
            if (!results.length) fieldset.querySelector(".coordinates").open = true;
          } catch (err) {
            if (err.name !== "AbortError" && version === generation) {
              status.textContent = t.unavailable; fieldset.querySelector(".coordinates").open = true;
            }
          } finally { controllers.delete(own); }
        }, 220);
        timers.add(timer);
      });
    }
    function restoreFields(snapshot) {
      for (const [name,value] of snapshot.fields || []) {
        const el = val(name);
        if (el) { if (el.type === "checkbox") el.checked = value; else el.value = value; }
      }
      selected.clear();
      for (const [key,value] of snapshot.selected || []) selected.set(key,value);
      [...form.querySelectorAll(".coordinates")].forEach((el,i) => el.open = Boolean(snapshot.open?.[i]));
      form.querySelectorAll("[data-person]").forEach(el => {
        const p = el.dataset.person, u = val(p + "-unknown");
        val(p + "-time").disabled = u.checked; val(p + "-time").required = !u.checked;
        const place = selected.get(p);
        if (place) el.querySelector(".place-status").textContent = place.label + " · " + place.timezone;
      });
      sample = Boolean(snapshot.sample); updateExample();
    }
    if (saved) restoreFields(saved);
    function showError(message = t.error) { error.textContent = message; error.hidden = false; error.focus(); }
    function clearFieldErrors() {
      form.querySelectorAll(".field-error").forEach(el => el.remove());
      form.querySelectorAll('[aria-invalid="true"]').forEach(el => {
        el.removeAttribute("aria-invalid");
        const ids = (el.getAttribute("aria-describedby") || "").split(" ").filter(id => id && !id.endsWith("-error"));
        if (ids.length) el.setAttribute("aria-describedby", ids.join(" ")); else el.removeAttribute("aria-describedby");
      });
      error.hidden = true;
    }
    form.addEventListener("input", clearFieldErrors);
    form.addEventListener("change", clearFieldErrors);
    function flagField(input, message) {
      const fieldError = node("p", message, "field-error"); fieldError.id = input.id + "-error";
      input.setAttribute("aria-invalid", "true");
      input.setAttribute("aria-describedby", [input.getAttribute("aria-describedby"), fieldError.id].filter(Boolean).join(" "));
      const container = input.closest(".place-control");
      (container || input).after(fieldError);
      const details = input.closest("details"); if (details) details.open = true;
    }
    function validatePerson(index) {
      clearFieldErrors();
      const fieldset = people[index], person = fieldset.dataset.person, invalid = [];
      for (const input of fieldset.querySelectorAll("input")) {
        if (input.disabled || input.type === "checkbox") continue;
        if (!input.validity.valid || ((input.required || input.name.endsWith("-timezone")) && !input.value.trim())) {
          flagField(input, input.value.trim() ? t.error : t.required); invalid.push(input);
        }
      }
      if (val(person + "-latitude").value === "" || val(person + "-longitude").value === "") {
        const input = val(person + "-place"); flagField(input, t.locationRequired); invalid.push(input);
      }
      const zone = val(person + "-timezone");
      if (zone.value.trim() && !invalid.includes(zone)) {
        try { new Intl.DateTimeFormat("en", {timeZone:zone.value.trim()}); }
        catch { flagField(zone, t.error); invalid.push(zone); }
      }
      if (!invalid.length) return true;
      showStep(index, false); invalid[0].focus();
      return false;
    }
    function buildReview() {
      reviewPeople.replaceChildren();
      people.forEach((fieldset, index) => {
        const person = fieldset.dataset.person, card = node("article", null, "review-card");
        const heading = node("div", null, "review-card-heading");
        heading.append(node("h4", val(person + "-name").value.trim()));
        const edit = node("button", t.edit, "text-button"); edit.type = "button";
        edit.setAttribute("aria-label", t.edit + ": " + val(person + "-name").value.trim());
        edit.addEventListener("click", () => { returnToReview = true; showStep(index); }); heading.append(edit); card.append(heading);
        const dl = node("dl");
        const entries = [[t.date, date(val(person + "-date").value)],
          [t.time, val(person + "-unknown").checked ? t.unknown : val(person + "-time").value],
          [t.place, selected.get(person)?.label || val(person + "-latitude").value + ", " + val(person + "-longitude").value],
          [t.timezone, val(person + "-timezone").value]];
        for (const [key,value] of entries) { const row = node("div"); row.append(node("dt", key), node("dd", value)); dl.append(row); }
        card.append(dl); reviewPeople.append(card);
      });
      document.querySelector("#review-unknown").hidden = !people.some(el => val(el.dataset.person + "-unknown").checked);
    }
    function showStep(index, focus = true) {
      step = Math.max(0, Math.min(index, people.length));
      document.body.classList.remove("showing-report");
      workspace.hidden = false; reading.hidden = true;
      people.forEach((el, i) => el.hidden = i !== step);
      form.querySelector(".people").hidden = step === people.length;
      reviewStep.hidden = step !== people.length;
      form.querySelector(".settings").hidden = step !== people.length;
      document.querySelector("#flow-back").hidden = step === 0;
      label.textContent = step === people.length ? t.calculate : t.continue;
      form.querySelectorAll("[data-flow-step]").forEach((el, i) => {
        if (i === step) el.setAttribute("aria-current", "step"); else el.removeAttribute("aria-current");
        el.dataset.complete = String(i < step);
      });
      document.querySelector("#flow-count").textContent = number(step + 1) + " / " + number(people.length + 1);
      if (step === people.length) { returnToReview = false; buildReview(); }
      if (focus) (step === people.length ? document.querySelector("#review-heading") : people[step].querySelector("legend")).focus();
    }
    form.querySelectorAll("[data-flow-step]").forEach(el => el.addEventListener("click", () => {
      if (resultController) return;
      const next = Number(el.dataset.flowStep);
      for (let i = 0; i < next; i++) if (!validatePerson(i)) return;
      clearFieldErrors(); showStep(next);
    }));
    document.querySelector("#flow-back").addEventListener("click", () => {
      if (resultController) return;
      clearFieldErrors(); showStep(step - 1);
    });
    document.querySelector("#same-place")?.addEventListener("click", () => {
      for (const key of ["latitude","longitude","timezone","place"]) val("bride-" + key).value = val("groom-" + key).value;
      const place = selected.get("groom");
      if (place) selected.set("bride", place); else selected.delete("bride");
      const fieldset = people[1];
      fieldset.querySelector(".place-status").textContent = t.samePlace + " · " + val("bride-timezone").value;
      if (!place) fieldset.querySelector(".coordinates").open = true;
      clearFieldErrors(); invalidate();
    });
    exampleButton.addEventListener("click", () => {
      if (exampleButton.hidden) return;
      people.forEach((fieldset, i) => {
        const person = fieldset.dataset.person;
        const values = {name:i ? "Example B" : "Example A",date:i ? "1994-11-02" : "1992-03-14",time:"07:25",
          latitude:"17.385",longitude:"78.4867",timezone:"Asia/Kolkata"};
        for (const [key,value] of Object.entries(values)) val(person + "-" + key).value = value;
      });
      sample = true; invalidate(); clearFieldErrors(); showStep(people.length);
    });
    showStep(saved?.view === view ? saved.step || 0 : 0, false);
    returnToReview = Boolean(saved?.returnToReview); updateExample();
    function personData(person) {
      const lat = val(person + "-latitude"), lon = val(person + "-longitude");
      if (lat.value === "" || lon.value === "") {
        form.querySelector('[data-person="' + person + '"] .coordinates').open = true;
        throw new Error("location");
      }
      const name = val(person + "-name").value.trim();
      const timezone = val(person + "-timezone").value.trim();
      if (!name || !timezone || !Number.isFinite(Number(lat.value)) || !Number.isFinite(Number(lon.value))) throw new Error("input");
      return {name, date: val(person + "-date").value,
        time: val(person + "-unknown").checked ? null : val(person + "-time").value,
        latitude: Number(lat.value), longitude: Number(lon.value), timezone};
    }
    const original = (parent, text) => {
      if (!text) return;
      const p = node("p", text); p.lang = "en"; p.dir = "ltr"; parent.append(p);
    };
    function sourceDetails(parent, title, texts) {
      const details = node("details", null, "factor");
      const summary = node("summary");
      summary.append(node("span", title), node("span", "English", "badge"));
      details.append(summary);
      const inner = node("div", null, "factor-content");
      const definition = explorer.definition(title);
      if (definition) inner.append(definition);
      for (const text of texts.filter(Boolean)) original(inner, text);
      details.append(inner); parent.append(details);
    }
    function factor(parent, item, porutham) {
      const details = node("details", null, "factor"), summary = node("summary");
      const name = locale === "ta" && item.tamil_name ? item.tamil_name : item.name;
      const good = porutham ? item.passed : item.score === item.maximum;
      details.id = "factor-" + (porutham ? "porutham" : "ashtakoota") + "-" + item.name.toLowerCase().replace(/[ _]/g, "-");
      details.dataset.factorState = good ? "full" : "review";
      const value = porutham ? (good ? t.passed : t.review) : number(item.score) + " / " + number(item.maximum);
      summary.append(node("span", name), node("span", value, good ? "badge" : "badge review"));
      details.append(summary);
      const inner = node("div", null, "factor-content");
      inner.append(node("p", t.groom + ": " + item.groom_attribute), node("p", t.bride + ": " + item.bride_attribute));
      const language = node("small", "English"); language.lang = "en"; inner.append(language);
      const definition = explorer.definition(item.name);
      if (definition) inner.append(definition);
      original(inner, "How your result was calculated");
      original(inner, item.explanation);
      details.append(inner); parent.append(details);
    }
    function scoreCard(parent, name, value, maximum, warnings) {
      const card = node("article", null, "score-card");
      card.append(node("p", name, "score-label"));
      card.append(explorer.helpButton(name === "Ashtakoota" ? "ashtakoota" : "porutham"));
      const total = node("div", number(value), "score-value"); total.append(node("small", " / " + number(maximum)));
      card.append(total);
      const progress = node("progress"); progress.max = maximum; progress.value = value; progress.setAttribute("aria-label", name + ": " + value + "/" + maximum);
      card.append(progress);
      if (warnings.length) card.append(node("p", t.review + ": " + warnings.join(", "), "badge review"));
      parent.append(card);
    }
    function reportSection(title) {
      const section = node("details", null, "report-section"), summary = node("summary");
      summary.append(node("span", title)); section.append(summary);
      const content = node("div", null, "report-section-content"); section.append(content); output.append(section);
      return content;
    }
    function renderMatch(data) {
      const scores = node("div", null, "scores"); output.append(scores);
      const order = view === "porutham" ? ["porutham","ashtakoota"] : ["ashtakoota","porutham"];
      for (const key of order) {
        const match = data[key]; if (!match) continue;
        const porutham = key === "porutham", title = porutham ? "Dasa Porutham" : "Ashtakoota";
        scoreCard(scores, title, porutham ? match.passed : match.total, porutham ? match.total : match.maximum,
          porutham ? match.essential_failures : match.blocking_doshas);
        const section = reportSection(title);
        for (const item of (porutham ? match.poruthams : match.kootas)) factor(section, item, porutham);
        explorer.factorControls(section);
        sourceDetails(section, t.details, [match.verdict, ...Object.values(match.exceptions || {}).flat()]);
      }
      if (data.doshas) {
        const section = reportSection("Dosha");
        const d = data.doshas;
        sourceDetails(section, "Mangal", [d.mangal.summary, t.groom + ": " + d.mangal.groom.detail,
          ...d.mangal.groom.cancellations, t.bride + ": " + d.mangal.bride.detail, ...d.mangal.bride.cancellations]);
        for (const key of ["kaal_sarp","sade_sati"]) {
          if (d[key]) sourceDetails(section, key === "kaal_sarp" ? "Kaal Sarp" : "Sade Sati",
            [t.groom + ": " + d[key].groom.detail, t.bride + ": " + d[key].bride.detail]);
        }
      }
      if (data.full_charts) for (const c of Object.values(data.full_charts)) renderChart(c, reportSection(c.name + " · " + t.chart));
      if (data.dasha) sourceDetails(output, "Vimshottari", [data.dasha.groom, data.dasha.bride]);
      if (data.analysis) scores.after(explorer.matchOverview(data.analysis));
    }
    function renderChart(chart, parent = output) {
      const output = parent;
      output.append(node("h3", chart.name + " · " + t.chart));
      output.append(explorer.chartExplorer(chart));
      const wrapper = node("div", null, "table-scroll"), table = node("table"), thead = node("thead"), header = node("tr");
      for (const heading of ["Graha","Rashi","°","Nakshatra","Pada","Navamsa","House"]) {
        const th = node("th",heading); th.scope = "col";
        th.append(explorer.helpButton(({Graha:"graha",Rashi:"rashi","°":"longitude",Nakshatra:"nakshatra",Pada:"pada",Navamsa:"navamsa",House:"house"})[heading])); header.append(th);
      }
      thead.append(header); table.append(thead); const body = node("tbody");
      for (const g of chart.grahas || []) {
        const tr = node("tr");
        for (const value of [g.name,g.rashi,g.degrees,g.nakshatra,g.pada,g.navamsa,g.house ?? "—"]) tr.append(node("td",value));
        body.append(tr);
      }
      table.append(body); wrapper.append(table); output.append(wrapper);
      sourceDetails(output, "Planet condition", (chart.grahas || []).map(g =>
        g.name + ": " + (g.dignity || "Not specified") + "; retrograde: " + (g.retrograde ? "Yes" : "No") + "; combust: " + (g.combust ? "Yes" : "No")));
      if (chart.ascendant) sourceDetails(output, "Lagna", [chart.ascendant.rashi + " · " + chart.ascendant.degrees]);
      if (chart.dasha?.mahadashas) {
        const timeline = node("ol", null, "dasha-timeline");
        for (const period of chart.dasha.mahadashas) {
          timeline.append(node("li", period.lord + " · " + date(period.start) + " → " + date(period.end)));
        }
        output.append(node("h3","Vimshottari"),timeline);
        const definition = explorer.definition("Vimshottari"); if (definition) output.append(definition);
      }
      if (chart.doshas) for (const d of Object.values(chart.doshas)) sourceDetails(output,d.name,[d.detail,...d.cancellations]);
    }
    function renderRecord(data, body) {
      output.replaceChildren(); exportError.hidden = true;
      if (sample) output.append(node("p", t.sampleNotice, "notice"));
      if (data.accuracy_warning) {
        output.append(node("p", t.unknown + " · " + t.review, "notice"));
        sourceDetails(output,t.details,[data.accuracy_warning]);
      }
      if (view === "chart") renderChart(data); else renderMatch(data);
      output.append(explorer.nextSteps(view === "chart"), explorer.provenance(data));
      shareSummary = [...output.querySelectorAll(".score-card")].map(card =>
        card.querySelector(".score-label").textContent + " " + card.querySelector(".score-value").textContent.replace(/\s+/g, " ").trim()
      ).join(" · ") || document.title;
      reading.hidden = false; workspace.hidden = true;
      document.body.classList.add("showing-report");
      toggleDetails.textContent = t.expandAll; toggleDetails.setAttribute("aria-expanded", "false");
      document.querySelector("#result-heading").textContent = view === "chart" ? body.name : body.groom.name + " & " + body.bride.name;
    }
    function saveBlob(blob, filename) {
      const url = URL.createObjectURL(blob); objectUrls.add(url);
      const link = node("a"); link.href = url; link.download = filename;
      document.body.append(link); link.click(); link.remove();
      const timer = setTimeout(() => { URL.revokeObjectURL(url); objectUrls.delete(url); timers.delete(timer); }, 60000);
      timers.add(timer);
    }
    pdfButton.addEventListener("click", async () => {
      if (!lastRequest || pdfController) return;
      const own = new AbortController(); pdfController = own; controllers.add(own);
      const timeout = setTimeout(() => own.abort("timeout"), 60000); timers.add(timeout);
      pdfButton.disabled = true; pdfButton.textContent = t.loading; pdfButton.setAttribute("aria-busy", "true");
      exportError.hidden = true;
      try {
        const kind = view === "chart" ? "chart" : "match";
        const query = new URLSearchParams({locale, ayanamsa:lastAyanamsa});
        const response = await fetch("/reports/" + kind + ".pdf?" + query, {
          method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(lastRequest),
          signal:own.signal, cache:"no-store"
        });
        if (!response.ok || !response.headers.get("content-type")?.startsWith("application/pdf")) throw new Error("PDF export");
        const blob = await response.blob();
        if (version === generation && !own.signal.aborted) saveBlob(blob, "astro-" + kind + ".pdf");
      } catch (err) {
        if (version === generation && (!own.signal.aborted || own.signal.reason === "timeout")) {
          exportError.textContent = t.error; exportError.hidden = false;
        }
      } finally {
        clearTimeout(timeout); timers.delete(timeout); controllers.delete(own);
        if (pdfController === own) pdfController = null;
        pdfButton.disabled = false; pdfButton.textContent = t.downloadPdf; pdfButton.removeAttribute("aria-busy");
      }
    });
    document.querySelector("#download-json").addEventListener("click", () => {
      if (!lastReport || !lastRequest) return;
      const file = {schemaVersion:1, application:"Astro", view, locale, calculatedAt, ayanamsa:lastAyanamsa, sample,
        inputs:lastRequest, report:lastReport};
      saveBlob(new Blob([JSON.stringify(file,null,2)], {type:"application/json"}), "astro-" + (view === "chart" ? "chart" : "match") + ".json");
    });
    toggleDetails.addEventListener("click", () => {
      const items = [...output.querySelectorAll("details")], open = items.some(el => !el.open);
      items.forEach(el => el.open = open);
      toggleDetails.textContent = open ? t.collapseAll : t.expandAll;
      toggleDetails.setAttribute("aria-expanded", String(open));
    });
    output.addEventListener("toggle", () => {
      const items = [...output.querySelectorAll("details")], allOpen = items.length > 0 && items.every(el => el.open);
      toggleDetails.textContent = allOpen ? t.collapseAll : t.expandAll;
      toggleDetails.setAttribute("aria-expanded", String(allOpen));
    }, true);
    if (saved?.report && saved?.request && saved.view === view) {
      lastReport = saved.report; lastRequest = saved.request; lastAyanamsa = saved.ayanamsa; calculatedAt = saved.calculatedAt;
      renderRecord(lastReport, lastRequest);
      if (!saved.showingReport) showStep(step, false);
    }
    form.addEventListener("submit", async event => {
      event.preventDefault();
      if (resultController) return;
      if (step < people.length) {
        if (validatePerson(step)) showStep(returnToReview ? people.length : step + 1);
        return;
      }
      for (let i = 0; i < people.length; i++) if (!validatePerson(i)) return;
      error.hidden = true; invalidate();
      let body;
      try {
        const groom = personData("groom");
        body = view === "chart" ? groom : {groom,bride:personData("bride"),system:"both",ayanamsa:val("ayanamsa").value};
      } catch (err) { showError(t.error); return; }
      const calculationAyanamsa = val("ayanamsa").value;
      resultController = new AbortController(); const own = resultController; controllers.add(own);
      const timeout = setTimeout(() => own.abort("timeout"), 30000); timers.add(timeout);
      button.disabled = true; label.textContent = t.loading; form.setAttribute("aria-busy", "true");
      form.querySelectorAll("[data-flow-step],#flow-back").forEach(el => el.disabled = true);
      try {
        const endpoint = view === "chart" ? "/chart?ayanamsa=" + encodeURIComponent(calculationAyanamsa) : "/match/full";
        const response = await fetch(endpoint, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body),signal:own.signal,cache:"no-store"});
        if (!response.ok) throw new Error("response");
        const data = await response.json();
        if (version !== generation || own.signal.aborted) return;
        lastReport = data; lastRequest = body; lastAyanamsa = calculationAyanamsa; calculatedAt = new Date().toISOString();
        renderRecord(data, body);
        reading.focus({preventScroll:true});
        reading.scrollIntoView({behavior:matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",block:"start"});
      } catch (err) {
        if (version === generation && (!own.signal.aborted || own.signal.reason === "timeout")) showError();
      } finally {
        clearTimeout(timeout); controllers.delete(own);
        if (version === generation && resultController === own) { button.disabled = false; label.textContent = step === people.length ? t.calculate : t.continue; form.removeAttribute("aria-busy"); resultController = null; form.querySelectorAll("[data-flow-step],#flow-back").forEach(el => el.disabled = false); }
      }
    });
    form.addEventListener("reset", () => {
      const snapshot = capture();
      invalidate(); cleanup(); selected.clear(); output.replaceChildren(); error.hidden = true; exportError.hidden = true;
      clearFieldErrors(); sample = false;
      form.querySelectorAll(".place-status").forEach(el => el.textContent = "");
      form.querySelectorAll(".coordinates,.settings").forEach(el => el.open = false);
      form.querySelectorAll(".suggestions").forEach(el => el.hidden = true);
      form.querySelectorAll('[role="combobox"]').forEach(el => { el.setAttribute("aria-expanded", "false"); el.removeAttribute("aria-activedescendant"); });
      queueMicrotask(() => {
        form.querySelectorAll('[type="time"]').forEach(el => {el.disabled = false; el.required = true;});
        button.disabled = false; form.removeAttribute("aria-busy"); resultController = null;
        form.querySelectorAll("[data-flow-step],#flow-back").forEach(el => el.disabled = false);
        showStep(0); updateExample();
        resetSnapshot = snapshot; resetStatus.hidden = false;
        resetTimer = setTimeout(forgetUndo, 15000); timers.add(resetTimer);
      });
    });
    document.querySelector("#undo-reset").addEventListener("click", () => {
      if (!resetSnapshot) return;
      const snapshot = resetSnapshot; forgetUndo(); restoreFields(snapshot);
      lastReport = snapshot.report; lastRequest = snapshot.request; lastAyanamsa = snapshot.ayanamsa; calculatedAt = snapshot.calculatedAt;
      showStep(snapshot.step);
      if (lastReport && lastRequest && snapshot.showingReport) { renderRecord(lastReport, lastRequest); reading.focus(); }
    });
    document.querySelector("#edit").addEventListener("click", () => showStep(people.length));
    let printOpen = [], printHidden = [];
    const beforePrint = () => {
      printOpen = [...reading.querySelectorAll("details")].map(el => [el,el.open]);
      printOpen.forEach(([el]) => el.open = true);
      printHidden = [...reading.querySelectorAll("[data-factor-state]")].map(el => [el,el.hidden]);
      printHidden.forEach(([el]) => el.hidden = false);
    };
    const afterPrint = () => { printOpen.forEach(([el,open]) => el.open = open); printHidden.forEach(([el,hidden]) => el.hidden = hidden); };
    window.onbeforeprint = beforePrint; window.onafterprint = afterPrint;
    document.querySelector("#print").addEventListener("click", () => window.print());
    document.querySelectorAll(".locale-link").forEach(link => link.addEventListener("click", event => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault(); closeMenus(); navigate(link.href,true);
    }));
    document.body.addEventListener("keydown", event => { if (event.key === "Escape") closeMenus(true); });
  }
  async function navigate(url,push) {
    const nav = ++navigation;
    try {
      const response = await fetch(url,{headers:{"Accept":"text/html"}});
      if (!response.ok) throw new Error("language");
      const doc = new DOMParser().parseFromString(await response.text(),"text/html");
      if (nav !== navigation) return;
      if (!doc.querySelector("#birth-form")) throw new Error("language");
      const saved = capture();
      cleanup();
      document.documentElement.lang = doc.documentElement.lang;
      document.documentElement.dir = doc.documentElement.dir;
      document.title = doc.title;
      for (const selector of ['meta[name="description"]','meta[name="robots"]','meta[name^="twitter:"]','meta[property^="og:"]','link[rel="canonical"]','link[rel="alternate"]']) {
        document.head.querySelectorAll(selector).forEach(el => el.remove());
        doc.head.querySelectorAll(selector).forEach(el => document.head.append(document.importNode(el,true)));
      }
      document.body.replaceWith(document.importNode(doc.body,true));
      const structured = document.head.querySelector('script[type="application/ld+json"]');
      if (structured) structured.textContent = doc.head.querySelector('script[type="application/ld+json"]').textContent;
      if (push) history.pushState(null,"",url);
      boot(saved);
    } catch {
      if (nav !== navigation) return;
      const error = document.querySelector("#form-error");
      error.textContent = document.querySelector('[data-key="error"]').textContent; error.hidden = false; error.focus();
    }
  }
  window.addEventListener("popstate", () => navigate(location.href,false));
  boot();
})();
