(() => {
  "use strict";

  const DATA_PATHS = {
    atlas: "./data/atlas.json",
    taxonomy: "./data/taxonomy.json",
    annotations: "./data/annotations.json",
    exhibits: "./data/exhibits.json",
  };
  const LOCAL_KEY = "agd-atlas-local-annotations-v1";
  const REPO_RAW_BASE = "https://github.com/zazieproductions/A-taxonomy-of-generative-anomalies/blob/main/";
  const PAGE_SIZE = 24;
  const NS = "http://www.w3.org/2000/svg";
  const state = {
    atlas: null,
    records: [],
    taxonomy: [],
    taxonomyById: new Map(),
    annotations: [],
    localAnnotations: [],
    exhibits: [],
    experiments: [],
    pairs: [],
    filtered: [],
    visibleLimit: PAGE_SIZE,
    activeRecord: null,
    toastTimer: null,
  };

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  function node(tag, className = "", text = null) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== null && text !== undefined) element.textContent = String(text);
    return element;
  }

  function svgNode(tag, attributes = {}, text = null) {
    const element = document.createElementNS(NS, tag);
    Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, String(value)));
    if (text !== null) element.textContent = String(text);
    return element;
  }

  function maskDisplayText(value) {
    if (typeof value !== "string") return "";
    const patterns = [
      [/\b\d{3}-\d{2}-\d{4}\b/g, "[REDACTED STRUCTURED VALUE]"],
      [/\b(?:\d[ -]?){13,19}\b/g, "[REDACTED STRUCTURED VALUE]"],
      [/\b(?:CVV2?|CVC|security\s+code)\s*[:=#]?\s*\d{3,4}\b/gi, "[REDACTED STRUCTURED VALUE]"],
      [/\b(?:\d{1,3}\.){3}\d{1,3}\b/g, "[REDACTED STRUCTURED VALUE]"],
      [/\b(?:\+?1[ .-]?)?(?:\(\d{3}\)|\d{3})[ .-]\d{3}[ .-]\d{4}\b/g, "[REDACTED STRUCTURED VALUE]"],
      [/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, "[REDACTED STRUCTURED VALUE]"],
    ];
    return patterns.reduce((text, [pattern, replacement]) => text.replace(pattern, replacement), value);
  }

  function clip(value, max = 150) {
    const clean = maskDisplayText(value || "").replace(/\s+/g, " ").trim();
    return clean.length > max ? `${clean.slice(0, max - 1)}…` : clean;
  }

  function exact(value) {
    if (value === null || value === undefined || value === "") return "not recorded";
    if (typeof value === "number") return String(value);
    if (typeof value === "boolean") return value ? "true" : "false";
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
  }

  function formatTime(value, includeSeconds = false) {
    if (!value) return "not recorded";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return new Intl.DateTimeFormat("en-GB", {
      timeZone: "UTC",
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      ...(includeSeconds ? { second: "2-digit" } : {}),
      hour12: false,
    }).format(date) + " UTC";
  }

  function modelColor(model) {
    if (model === "llama-8b") return "#82a9ff";
    if (model === "trinity-truebase") return "#66d6c4";
    return "#c1ef75";
  }

  function statusClass(status) {
    if (status === "completed") return "completed";
    if (status === "cancelled") return "cancelled";
    return "other";
  }

  function experimentTitle(id) {
    const experiment = state.experiments.find((item) => item.experiment_id === id);
    return experiment?.title || id || "Experiment not recorded";
  }

  function labelsFor(generationId) {
    const labels = new Set();
    [...state.annotations, ...state.localAnnotations]
      .filter((annotation) => annotation.generation_id === generationId)
      .forEach((annotation) => (annotation.labels || []).forEach((label) => labels.add(label)));
    return Array.from(labels);
  }

  function labelName(id) {
    return state.taxonomyById.get(id)?.label || id.replaceAll("_", " ");
  }

  function labelChip(id) {
    const chip = node("span", "taxonomy-chip", labelName(id));
    const term = state.taxonomyById.get(id);
    if (term?.color) chip.style.borderColor = `${term.color}66`;
    if (term?.color) chip.style.color = term.color;
    return chip;
  }

  function showToast(message) {
    const toast = $("#toast");
    toast.textContent = message;
    toast.classList.add("visible");
    window.clearTimeout(state.toastTimer);
    state.toastTimer = window.setTimeout(() => toast.classList.remove("visible"), 2800);
  }

  async function fetchJson(path) {
    const response = await fetch(path, { cache: "no-cache" });
    if (!response.ok) throw new Error(`Could not load ${path} (${response.status})`);
    return response.json();
  }

  function loadLocalAnnotations() {
    try {
      const value = localStorage.getItem(LOCAL_KEY);
      const parsed = value ? JSON.parse(value) : [];
      state.localAnnotations = Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      state.localAnnotations = [];
      console.warn("Local annotation storage is unavailable.", error);
    }
    updateLocalAnnotationCount();
  }

  async function init() {
    try {
      const [atlas, taxonomyBundle, annotationBundle, exhibitBundle] = await Promise.all([
        fetchJson(DATA_PATHS.atlas),
        fetchJson(DATA_PATHS.taxonomy),
        fetchJson(DATA_PATHS.annotations),
        fetchJson(DATA_PATHS.exhibits),
      ]);
      state.atlas = atlas;
      state.records = atlas.generations || [];
      state.experiments = atlas.experiments || [];
      state.taxonomy = taxonomyBundle.terms || [];
      state.taxonomyById = new Map(state.taxonomy.map((term) => [term.id, term]));
      state.annotations = annotationBundle.annotations || [];
      state.exhibits = exhibitBundle.exhibits || [];
      loadLocalAnnotations();
      state.pairs = buildPairs();
      setPrivacyNotice(atlas.privacy_projection?.notice);
      populateFilters();
      renderMetrics();
      renderTaxonomy();
      renderExhibits(exhibitBundle.editorial_status || "Initial editorial pass");
      renderPairs();
      renderGallery();
      drawLexicalChart();
      populateTimelineFilter();
      drawTimeline();
      renderDistribution();
      bindEvents();
      $("#gallery-grid").setAttribute("aria-busy", "false");
    } catch (error) {
      console.error(error);
      $("#gallery-grid").setAttribute("aria-busy", "false");
      $("#gallery-grid").replaceChildren(
        Object.assign(node("div", "empty-state", "The Atlas data could not be loaded. Serve the docs folder over HTTP; opening index.html directly will block JSON fetches."), {
          role: "alert",
        }),
      );
      $("#visible-count").textContent = "DATA LOAD ERROR";
    }
  }

  function setPrivacyNotice(message) {
    if (message) $("#privacy-notice").textContent = message;
  }

  function renderMetrics() {
    const completed = state.records.filter((record) => record.status === "completed").length;
    const cancelled = state.records.filter((record) => record.status === "cancelled").length;
    const traces = state.records.filter((record) => Array.isArray(record.logprobs)).length;
    $("#stat-generations").textContent = state.records.length.toLocaleString();
    $("#stat-experiments").textContent = state.experiments.length.toLocaleString();
    $("#stat-status").textContent = `${completed} / ${cancelled}`;
    $("#stat-logprobs").textContent = `${traces} / ${state.records.length}`;
  }

  function addOption(select, value, label) {
    const option = node("option", "", label);
    option.value = value;
    select.append(option);
  }

  function populateFilters() {
    const statusSelect = $("#status-filter");
    const modelSelect = $("#model-filter");
    const experimentSelect = $("#experiment-filter");
    const labelSelect = $("#label-filter");
    const topPSelect = $("#top-p-filter");
    const topKSelect = $("#top-k-filter");
    const minPSelect = $("#min-p-filter");

    Array.from(new Set(state.records.map((record) => record.status).filter(Boolean))).sort().forEach((value) => addOption(statusSelect, value, value));
    Array.from(new Set(state.records.map((record) => record.model).filter(Boolean))).sort().forEach((value) => addOption(modelSelect, value, value));
    state.experiments.forEach((item) => addOption(experimentSelect, item.experiment_id, item.title || item.experiment_id));
    state.taxonomy.forEach((term) => addOption(labelSelect, term.id, term.label));

    function distinctParameter(field) {
      return Array.from(new Set(state.records.map((record) => record.sampling?.[field]).filter((value) => value !== undefined && value !== null)))
        .sort((a, b) => Number(a) - Number(b));
    }
    distinctParameter("top_p").forEach((value) => addOption(topPSelect, String(value), String(value)));
    distinctParameter("top_k").forEach((value) => addOption(topKSelect, String(value), String(value)));
    distinctParameter("min_p").forEach((value) => addOption(minPSelect, String(value), String(value)));
  }

  function getFilters() {
    return {
      query: $("#search").value.trim().toLocaleLowerCase(),
      status: $("#status-filter").value,
      model: $("#model-filter").value,
      experiment: $("#experiment-filter").value,
      label: $("#label-filter").value,
      tempMin: $("#temp-min").value === "" ? null : Number($("#temp-min").value),
      tempMax: $("#temp-max").value === "" ? null : Number($("#temp-max").value),
      topP: $("#top-p-filter").value,
      topK: $("#top-k-filter").value,
      minP: $("#min-p-filter").value,
      sort: $("#sort-filter").value,
    };
  }

  function hasParameter(record, field, filterValue) {
    if (filterValue === "") return true;
    const value = record.sampling?.[field];
    if (filterValue === "__null") return value === null || value === undefined;
    return value !== null && value !== undefined && String(value) === filterValue;
  }

  function matchesFilters(record, filters) {
    if (filters.status && record.status !== filters.status) return false;
    if (filters.model && record.model !== filters.model) return false;
    if (filters.experiment && record.experiment_id !== filters.experiment) return false;
    if (filters.label && !labelsFor(record.generation_id).includes(filters.label)) return false;
    const temperature = record.sampling?.temperature;
    if (filters.tempMin !== null && (typeof temperature !== "number" || temperature < filters.tempMin)) return false;
    if (filters.tempMax !== null && (typeof temperature !== "number" || temperature > filters.tempMax)) return false;
    if (!hasParameter(record, "top_p", filters.topP)) return false;
    if (!hasParameter(record, "top_k", filters.topK)) return false;
    if (!hasParameter(record, "min_p", filters.minP)) return false;
    if (filters.query) {
      const terms = [record.generation_id, record.model, record.model_identifier, record.experiment_title, record.prompt, record.completion, ...labelsFor(record.generation_id)];
      if (!terms.filter(Boolean).join(" ").toLocaleLowerCase().includes(filters.query)) return false;
    }
    return true;
  }

  function sortedRecords(records, sort) {
    const result = [...records];
    if (sort === "oldest") {
      return result.sort((a, b) => String(a.timestamps?.started_at || "").localeCompare(String(b.timestamps?.started_at || "")));
    }
    if (sort === "temperature") {
      return result.sort((a, b) => (Number(b.sampling?.temperature) || 0) - (Number(a.sampling?.temperature) || 0));
    }
    if (sort === "completion") {
      return result.sort((a, b) => (Number(b.tokens?.completion) || (b.completion || "").length) - (Number(a.tokens?.completion) || (a.completion || "").length));
    }
    return result.sort((a, b) => String(b.timestamps?.started_at || "").localeCompare(String(a.timestamps?.started_at || "")));
  }

  function recordHeadline(record) {
    const output = maskDisplayText(record.completion || "").replace(/\s+/g, " ").trim();
    if (output) return output.length > 82 ? `${output.slice(0, 81)}…` : output;
    return record.completion === "" ? "No rendered completion text" : "Completion text not recorded";
  }

  function renderGallery() {
    const filters = getFilters();
    const matching = state.records.filter((record) => matchesFilters(record, filters));
    state.filtered = sortedRecords(matching, filters.sort);
    state.visibleLimit = PAGE_SIZE;
    $("#visible-count").textContent = `${matching.length.toLocaleString()} / ${state.records.length.toLocaleString()} specimens`;
    paintGallery();
  }

  function paintGallery() {
    const grid = $("#gallery-grid");
    const page = state.filtered.slice(0, state.visibleLimit);
    const fragment = document.createDocumentFragment();
    if (!page.length) {
      fragment.append(node("div", "empty-state", "No specimens match these filters. Clear one constraint or reset the index."));
    } else {
      page.forEach((record) => fragment.append(createSpecimenCard(record)));
    }
    grid.replaceChildren(fragment);
    $("#load-more").hidden = state.filtered.length <= state.visibleLimit;
    $("#load-more").textContent = `Load ${Math.min(PAGE_SIZE, state.filtered.length - state.visibleLimit)} more specimens ＋`;
  }

  function createSpecimenCard(record) {
    const card = node("article", "specimen-card");
    const top = node("div", "specimen-top");
    top.append(node("span", "run-id", record.generation_id));
    const status = node("span", `status-chip status-${statusClass(record.status)}`, record.status || "unrecorded");
    top.append(status);
    card.append(top);

    const title = node("h3", "", recordHeadline(record));
    card.append(title);
    const meta = node("div", "specimen-meta");
    const metaValues = [
      ["MODEL", record.model || "not recorded"],
      ["T", exact(record.sampling?.temperature)],
      ["TOP P", exact(record.sampling?.top_p)],
      ["TOKENS", exact(record.tokens?.completion)],
    ];
    metaValues.forEach(([label, value]) => {
      const item = node("span");
      item.append(node("b", "", `${label}:`), document.createTextNode(` ${value}`));
      meta.append(item);
    });
    card.append(meta);

    const prompt = node("p", "prompt-fragment");
    prompt.append(node("span", "", "Prompt / "), document.createTextNode(clip(record.prompt, 128) || "No prompt text recorded"));
    card.append(prompt);
    const completion = node("p", "completion-fragment", clip(record.completion, 200) || "[No rendered completion text]");
    card.append(completion);

    const bottom = node("div", "specimen-bottom");
    const chips = node("div", "label-row");
    labelsFor(record.generation_id).slice(0, 3).forEach((label) => chips.append(labelChip(label)));
    if (!chips.childElementCount) chips.append(node("span", "taxonomy-chip", "unclassified"));
    bottom.append(chips);
    const open = node("button", "open-specimen", "Open record ↗");
    open.type = "button";
    open.setAttribute("aria-label", `Open generation ${record.generation_id}`);
    open.addEventListener("click", () => openSpecimen(record));
    bottom.append(open);
    card.append(bottom);
    return card;
  }

  function buildPairs() {
    const groups = new Map();
    state.records.forEach((record) => {
      if (!record.comparison_group_id) return;
      const group = groups.get(record.comparison_group_id) || [];
      group.push(record);
      groups.set(record.comparison_group_id, group);
    });
    return Array.from(groups.entries())
      .filter(([, records]) => records.length === 2 && new Set(records.map((record) => record.model)).size === 2)
      .map(([id, records]) => ({ id, records: [...records].sort((a, b) => a.model.localeCompare(b.model)) }));
  }

  function renderPairs() {
    $("#pair-count").textContent = state.pairs.length.toLocaleString();
    const select = $("#pair-select");
    select.replaceChildren();
    if (!state.pairs.length) {
      addOption(select, "", "No exact matched pairs in this snapshot");
      $("#comparison-grid").replaceChildren(node("div", "empty-state", "No prompt-matched model pairs were found."));
      return;
    }
    addOption(select, "", "Select a pair");
    state.pairs.forEach((pair) => {
      const a = pair.records[0];
      const b = pair.records[1];
      const promptText = clip(a.prompt, 66) || "[prompt unavailable]";
      addOption(select, pair.id, `${promptText} · ${a.model} / ${b.model}`);
    });
    const featured = state.pairs.find((pair) => pair.records.some((record) => record.generation_id === "d699f9d6-7894-495b-8a97-02cee4c7c6b5"));
    select.value = featured?.id || state.pairs[0].id;
    renderPair(select.value);
  }

  function renderPair(pairId) {
    const pair = state.pairs.find((item) => item.id === pairId);
    const grid = $("#comparison-grid");
    if (!pair) {
      grid.replaceChildren(node("div", "empty-state", "Choose a matched pair to compare the recorded continuations."));
      return;
    }
    const [a, b] = pair.records;
    grid.replaceChildren();
    // Pair membership is computed against the exact canonical prompt before
    // masking; only the display string below is redacted.
    const promptBlock = node("div", "pair-prompt");
    promptBlock.append(node("span", "", "EXACT MATCHED PROMPT / "), document.createTextNode(maskDisplayText(a.prompt || "[Prompt text not recorded]")));
    grid.append(promptBlock);
    grid.append(createCompareLane(a));
    grid.append(createCompareLane(b));

    const warning = node("p", "pair-warning", `Seeds differ (${exact(a.sampling?.seed)} / ${exact(b.sampling?.seed)}). The public pair ID was computed from exact canonical prompts and matching non-model settings before display masking.`);
    grid.append(warning);
    const source = node("div", "pair-source");
    source.append(node("span", "", `${experimentTitle(a.experiment_id)} · ${pair.id}`));
    const action = node("button", "", "Open first record");
    action.type = "button";
    action.addEventListener("click", () => {
      openSpecimen(a);
    });
    source.append(action);
    grid.append(source);
  }

  function createCompareLane(record) {
    const lane = node("article", "compare-lane");
    const head = node("div", "compare-lane-head");
    const modelTitle = node("div");
    const model = node("span", "compare-model", record.model || "Model not recorded");
    model.style.color = modelColor(record.model);
    modelTitle.append(model, node("small", "", record.model_identifier || "upstream identifier not recorded"));
    const status = node("span", `status-chip status-${statusClass(record.status)}`, record.status || "unrecorded");
    head.append(modelTitle, status);
    lane.append(head);
    const text = node("pre", "compare-text", maskDisplayText(record.completion || "[No rendered completion text]"));
    lane.append(text);
    const settings = node("div", "compare-settings");
    ["temperature", "top_p", "top_k", "min_p", "presence_penalty", "frequency_penalty", "max_tokens"].forEach((key) => {
      if (record.sampling?.[key] !== undefined) settings.append(node("span", "setting-pill", `${key} ${exact(record.sampling[key])}`));
    });
    settings.append(node("span", "setting-pill", `seed ${exact(record.sampling?.seed)}`));
    lane.append(settings);
    const open = node("button", "open-specimen", "Inspect this run ↗");
    open.type = "button";
    open.style.marginTop = "14px";
    open.addEventListener("click", () => openSpecimen(record));
    lane.append(open);
    return lane;
  }

  function wordTokens(text) {
    try {
      return (maskDisplayText(text || "").toLocaleLowerCase().match(/[\p{L}\p{N}_]+(?:['’][\p{L}\p{N}_]+)*/gu) || []);
    } catch (_error) {
      return (maskDisplayText(text || "").toLocaleLowerCase().match(/[\w]+/g) || []);
    }
  }

  function wordMetrics(record) {
    if (record.privacy_redactions?.completion?.length) return null;
    const words = wordTokens(record.completion || "");
    if (!words.length) return null;
    return { ratio: new Set(words).size / words.length, words: words.length };
  }

  function drawLexicalChart() {
    const svg = $("#lexical-chart");
    svg.replaceChildren();
    const width = 760;
    const height = 330;
    const left = 66;
    const right = 23;
    const top = 22;
    const bottom = 48;
    const plotW = width - left - right;
    const plotH = height - top - bottom;
    const eligible = state.records.map((record) => ({ record, metric: wordMetrics(record) }))
      .filter((item) => item.metric && typeof item.record.sampling?.temperature === "number" && item.record.sampling.temperature > 0);
    if (!eligible.length) {
      svg.append(svgNode("text", { x: 30, y: 60, class: "chart-axis-label" }, "No records available for this view."));
      return;
    }
    const logTemps = eligible.map((item) => Math.log10(item.record.sampling.temperature));
    const xMin = Math.min(...logTemps);
    const xMax = Math.max(...logTemps);
    const range = Math.max(xMax - xMin, 1);
    const ticks = [
      { value: Math.max(xMin, -11), label: "1e−11" },
      { value: -1, label: "0.1" },
      { value: 0, label: "1" },
      { value: 1, label: "10" },
      { value: xMax, label: String(Math.max(...eligible.map((item) => item.record.sampling.temperature)).toPrecision(3)) },
    ].filter((tick, index, arr) => tick.value >= xMin && tick.value <= xMax && arr.findIndex((other) => other.value === tick.value) === index);

    [0, 0.25, 0.5, 0.75, 1].forEach((value) => {
      const y = top + (1 - value) * plotH;
      svg.append(svgNode("line", { x1: left, y1: y, x2: width - right, y2: y, class: "chart-grid-line" }));
      svg.append(svgNode("text", { x: left - 12, y: y + 4, class: "chart-axis-label", "text-anchor": "end" }, value.toFixed(2).replace(/0+$/, "").replace(/\.$/, "")));
    });
    ticks.forEach((tick) => {
      const x = left + ((tick.value - xMin) / range) * plotW;
      svg.append(svgNode("line", { x1: x, y1: top, x2: x, y2: top + plotH, class: "chart-grid-line" }));
      svg.append(svgNode("text", { x, y: height - 23, class: "chart-axis-label", "text-anchor": "middle" }, tick.label));
    });
    svg.append(svgNode("text", { x: left + plotW / 2, y: height - 4, class: "chart-axis-title", "text-anchor": "middle" }, "RECORDED TEMPERATURE · LOG₁₀ SCALE"));
    svg.append(svgNode("text", { x: 14, y: top + plotH / 2, class: "chart-axis-title", transform: `rotate(-90 14 ${top + plotH / 2})`, "text-anchor": "middle" }, "TYPE / TOKEN RATIO"));

    eligible.forEach(({ record, metric }) => {
      const x = left + ((Math.log10(record.sampling.temperature) - xMin) / range) * plotW;
      const y = top + (1 - metric.ratio) * plotH;
      const radius = 2.5 + Math.min(4.2, metric.words / 62);
      const titleText = `${record.generation_id} · ${record.model} · T=${exact(record.sampling.temperature)} · ratio=${metric.ratio.toFixed(3)} · ${metric.words} regex word tokens · ${record.status}`;
      if (record.status === "cancelled") {
        const points = `${x},${y - radius} ${x - radius},${y + radius} ${x + radius},${y + radius}`;
        const point = svgNode("polygon", { points, fill: "#f2a66d", stroke: modelColor(record.model), "stroke-width": 1.4, class: "chart-point" });
        point.append(svgNode("title", {}, titleText));
        point.addEventListener("click", () => openSpecimen(record));
        svg.append(point);
      } else {
        const point = svgNode("circle", { cx: x, cy: y, r: radius, fill: modelColor(record.model), opacity: 0.86, class: "chart-point" });
        point.append(svgNode("title", {}, titleText));
        point.addEventListener("click", () => openSpecimen(record));
        svg.append(point);
      }
    });
    const legend = $("#lexical-legend");
    legend.replaceChildren();
    Array.from(new Set(state.records.map((record) => record.model).filter(Boolean))).sort().forEach((model) => {
      const item = node("span", "legend-item");
      const dot = node("span", "legend-dot");
      dot.style.background = modelColor(model);
      item.append(dot, document.createTextNode(model));
      legend.append(item);
    });
    const cancelled = node("span", "legend-item");
    cancelled.append(node("span", "legend-square"), document.createTextNode("cancelled / triangle"));
    legend.append(cancelled);
  }

  function populateTimelineFilter() {
    const select = $("#timeline-experiment");
    select.replaceChildren();
    addOption(select, "", "All experiments");
    state.experiments.forEach((experiment) => addOption(select, experiment.experiment_id, experiment.title || experiment.experiment_id));
    select.value = "";
    renderTimelineLegend();
  }

  function renderTimelineLegend() {
    const legend = $("#timeline-legend");
    legend.replaceChildren();
    Array.from(new Set(state.records.map((record) => record.model).filter(Boolean))).sort().forEach((model) => {
      const item = node("span", "legend-item");
      const dot = node("span", "legend-dot");
      dot.style.background = modelColor(model);
      item.append(dot, document.createTextNode(model));
      legend.append(item);
    });
    const complete = node("span", "legend-item");
    complete.append(node("span", "legend-dot"), document.createTextNode("completed / circle"));
    const cancelled = node("span", "legend-item");
    cancelled.append(node("span", "legend-square"), document.createTextNode("cancelled / square"));
    legend.append(complete, cancelled);
  }

  function drawTimeline() {
    const svg = $("#timeline-chart");
    svg.replaceChildren();
    const experimentId = $("#timeline-experiment").value;
    const records = state.records.filter((record) => !experimentId || record.experiment_id === experimentId);
    const parsed = records.map((record) => ({ record, time: new Date(record.timestamps?.started_at).getTime() })).filter((item) => Number.isFinite(item.time));
    if (!parsed.length) {
      svg.append(svgNode("text", { x: 25, y: 60, class: "chart-axis-label" }, "No timestamped runs for this selection."));
      return;
    }
    const width = 760;
    const height = 330;
    const left = 132;
    const right = 25;
    const top = 31;
    const bottom = 44;
    const plotW = width - left - right;
    const models = Array.from(new Set(parsed.map((item) => item.record.model || "unrecorded"))).sort();
    const laneHeight = (height - top - bottom) / Math.max(models.length, 1);
    const min = Math.min(...parsed.map((item) => item.time));
    const max = Math.max(...parsed.map((item) => item.time));
    const range = Math.max(max - min, 1);
    const tickCount = 4;
    for (let index = 0; index <= tickCount; index += 1) {
      const x = left + (index / tickCount) * plotW;
      const date = new Date(min + (range * index) / tickCount);
      const label = new Intl.DateTimeFormat("en-GB", { timeZone: "UTC", hour: "2-digit", minute: "2-digit", hour12: false }).format(date);
      svg.append(svgNode("line", { x1: x, y1: top, x2: x, y2: height - bottom, class: "chart-grid-line" }));
      svg.append(svgNode("text", { x, y: height - 19, class: "chart-axis-label", "text-anchor": "middle" }, label));
    }
    models.forEach((model, index) => {
      const y = top + laneHeight * (index + 0.5);
      svg.append(svgNode("line", { x1: left, y1: y, x2: width - right, y2: y, class: "chart-grid-line" }));
      svg.append(svgNode("text", { x: left - 12, y: y + 4, class: "chart-axis-label", "text-anchor": "end" }, model));
    });
    const lanes = new Map(models.map((model, index) => [model, index]));
    parsed.forEach(({ record, time }, index) => {
      const x = left + ((time - min) / range) * plotW;
      const laneIndex = lanes.get(record.model || "unrecorded");
      const jitter = ((index % 5) - 2) * 5;
      const y = top + laneHeight * (laneIndex + 0.5) + jitter;
      const titleText = `${formatTime(record.timestamps?.started_at, true)} · ${record.model} · ${record.status} · T=${exact(record.sampling?.temperature)} · ${record.generation_id}`;
      if (record.status === "cancelled") {
        const mark = svgNode("rect", { x: x - 4.2, y: y - 4.2, width: 8.4, height: 8.4, rx: 0.5, class: "timeline-point cancelled", stroke: modelColor(record.model) });
        mark.append(svgNode("title", {}, titleText));
        mark.addEventListener("click", () => openSpecimen(record));
        svg.append(mark);
      } else {
        const mark = svgNode("circle", { cx: x, cy: y, r: 4.3, class: "timeline-point completed", fill: modelColor(record.model) });
        mark.append(svgNode("title", {}, titleText));
        mark.addEventListener("click", () => openSpecimen(record));
        svg.append(mark);
      }
    });
  }

  function renderDistribution() {
    const container = $("#status-distribution");
    container.replaceChildren();
    const statuses = ["completed", "cancelled"];
    const max = Math.max(...statuses.map((status) => state.records.filter((record) => record.status === status).length), 1);
    statuses.forEach((status) => {
      const count = state.records.filter((record) => record.status === status).length;
      const row = node("div", `distribution-row ${status}`);
      row.append(node("span", "", status));
      const track = node("div", "distribution-track");
      const fill = node("div", "distribution-fill");
      fill.style.width = `${(count / max) * 100}%`;
      track.append(fill);
      row.append(track, node("span", "distribution-count", String(count)));
      container.append(row);
    });
    const unknown = state.records.filter((record) => !statuses.includes(record.status)).length;
    if (unknown) {
      const row = node("div", "distribution-row");
      row.append(node("span", "", "other / unrecorded"));
      const track = node("div", "distribution-track");
      const fill = node("div", "distribution-fill");
      fill.style.width = `${(unknown / max) * 100}%`;
      fill.style.background = "#979a8f";
      track.append(fill);
      row.append(track, node("span", "distribution-count", String(unknown)));
      container.append(row);
    }
  }

  function renderTaxonomy() {
    const container = $("#taxonomy-grid");
    container.replaceChildren();
    state.taxonomy.forEach((term) => {
      const card = node("article", "taxonomy-card");
      const head = node("div", "taxonomy-card-head");
      const swatch = node("span", "taxonomy-swatch");
      swatch.style.background = term.color || "#c1ef75";
      head.append(swatch, node("h3", "", term.label));
      card.append(head, node("p", "", term.definition), node("code", "taxonomy-id", term.id));
      container.append(card);
    });
  }

  function renderExhibits(editorialStatus) {
    $("#editorial-status").textContent = editorialStatus.toLocaleUpperCase();
    const container = $("#exhibit-grid");
    container.replaceChildren();
    state.exhibits.forEach((exhibit, index) => {
      const card = node("article", "exhibit-card");
      card.dataset.number = String(index + 1).padStart(2, "0");
      card.append(node("p", "exhibit-kicker", exhibit.subtitle || "CURATED SPECIMEN"));
      card.append(node("h3", "", exhibit.title));
      if (exhibit.content_note) card.append(node("p", "exhibit-content-note", `CONTENT NOTE · ${exhibit.content_note}`));
      card.append(node("p", "exhibit-subtitle", exhibit.question || ""));
      if (exhibit.excerpt) card.append(node("blockquote", "exhibit-quote", `“${maskDisplayText(exhibit.excerpt)}”`));
      card.append(node("p", "exhibit-commentary", exhibit.commentary));
      const foot = node("div", "exhibit-foot");
      const tags = node("div", "label-row");
      (exhibit.labels || []).forEach((label) => tags.append(labelChip(label)));
      foot.append(tags);
      const actions = node("div", "label-row");
      const open = node("button", "", "Open specimen");
      open.type = "button";
      open.addEventListener("click", () => {
        const record = state.records.find((item) => item.generation_id === exhibit.generation_id);
        if (record) openSpecimen(record);
      });
      actions.append(open);
      if (exhibit.paired_generation_id) {
        const compare = node("button", "", "Compare pair");
        compare.type = "button";
        compare.addEventListener("click", () => {
          const record = state.records.find((item) => item.generation_id === exhibit.generation_id);
          const pair = record && state.pairs.find((item) => item.records.some((run) => run.generation_id === record.generation_id));
          if (pair) {
            $("#pair-select").value = pair.id;
            renderPair(pair.id);
            $("#comparisons").scrollIntoView({ behavior: "smooth" });
          }
        });
        actions.append(compare);
      }
      foot.append(actions);
      card.append(foot);
      container.append(card);
    });
  }

  function bindEvents() {
    $("#filters").addEventListener("submit", (event) => event.preventDefault());
    ["#search", "#status-filter", "#model-filter", "#experiment-filter", "#label-filter", "#temp-min", "#temp-max", "#top-p-filter", "#top-k-filter", "#min-p-filter", "#sort-filter"].forEach((selector) => {
      $(selector).addEventListener(selector === "#search" ? "input" : "change", renderGallery);
    });
    $("#reset-filters").addEventListener("click", () => {
      $("#filters").reset();
      renderGallery();
    });
    $("#load-more").addEventListener("click", () => {
      state.visibleLimit += PAGE_SIZE;
      paintGallery();
    });
    $("#pair-select").addEventListener("change", (event) => renderPair(event.target.value));
    $("#timeline-experiment").addEventListener("change", drawTimeline);
    $("#export-annotations").addEventListener("click", exportAnnotations);
    $(".dialog-close").addEventListener("click", () => $("#detail-dialog").close());
    $("#detail-dialog").addEventListener("click", (event) => {
      if (event.target === $("#detail-dialog")) $("#detail-dialog").close();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && $("#detail-dialog").open) $("#detail-dialog").close();
    });
  }

  function openSpecimen(record) {
    state.activeRecord = record;
    const dialog = $("#detail-dialog");
    const container = $("#detail-content");
    container.replaceChildren();
    $("#dialog-index").textContent = String(state.records.findIndex((item) => item.generation_id === record.generation_id) + 1).padStart(3, "0");
    const content = node("div", "detail-content");
    const titleRow = node("div", "detail-title-row");
    const heading = node("h2", "", recordHeadline(record));
    heading.id = "detail-title";
    titleRow.append(heading, node("span", `status-chip status-${statusClass(record.status)}`, record.status || "unrecorded"));
    content.append(titleRow);
    const subhead = node("p", "detail-subhead", `${record.generation_id} · ${experimentTitle(record.experiment_id)} · ${record.model_identifier || "upstream model ID not recorded"}`);
    content.append(subhead);

    const metrics = node("div", "detail-metrics");
    [
      ["RUN MODEL", record.model],
      ["TEMPERATURE", record.sampling?.temperature],
      ["TOP P", record.sampling?.top_p],
      ["PROMPT TOKENS", record.tokens?.prompt],
      ["COMPLETION TOKENS", record.tokens?.completion],
    ].forEach(([label, value]) => {
      const cell = node("div");
      cell.append(node("span", "", label), node("strong", "", exact(value)));
      metrics.append(cell);
    });
    content.append(metrics);

    const textGrid = node("div", "detail-text-grid");
    const promptPanel = node("section", "detail-text-block");
    promptPanel.append(node("h3", "", "Prompt / recorded before generation"));
    promptPanel.append(node("pre", "detail-pre", maskDisplayText(record.prompt || "[Prompt text not recorded]")));
    const completionPanel = node("section", "detail-text-block");
    completionPanel.append(node("h3", "", record.status === "cancelled" ? "Completion / cancelled record may be partial" : "Completion / recorded text"));
    completionPanel.append(node("pre", "detail-pre", maskDisplayText(record.completion || "[No rendered completion text]")));
    textGrid.append(promptPanel, completionPanel);
    content.append(textGrid);
    if (Object.keys(record.privacy_redactions || {}).length) {
      content.append(node("p", "privacy-inline", "One or more structured values were masked in this public view. The canonical corpus and source record have not been changed; the mask may not catch all sensitive content."));
    }

    const settingsPanel = node("section", "detail-panel");
    settingsPanel.append(node("h3", "", "Recorded sampling + completion fields"));
    const settings = node("table", "settings-table");
    const body = node("tbody");
    const orderedKeys = ["temperature", "top_p", "top_k", "min_p", "seed", "seed_mode", "presence_penalty", "frequency_penalty", "repetition_penalty", "max_tokens", "logprobs", "stream", "stop"];
    const keys = [...orderedKeys.filter((key) => Object.prototype.hasOwnProperty.call(record.sampling || {}, key)), ...Object.keys(record.sampling || {}).filter((key) => !orderedKeys.includes(key)).sort()];
    keys.forEach((key) => {
      const row = node("tr");
      row.append(node("th", "", key), node("td", "", exact(record.sampling[key])));
      body.append(row);
    });
    [
      ["configured prompt", record.configured_prompt],
      ["wrapper model ID", record.wrapper_model_id],
      ["started at", record.timestamps?.started_at],
      ["ended at", record.timestamps?.ended_at],
      ["finish reason", record.finish_reason],
      ["stop reason", record.stop_reason],
      ["finalized", record.finalized],
      ["token usage source", record.tokens?.source],
    ].forEach(([key, value]) => {
      const row = node("tr");
      row.append(node("th", "", key), node("td", "", exact(value)));
      body.append(row);
    });
    settings.append(body);
    settingsPanel.append(settings);
    const presenceDetails = node("details", "source-presence");
    presenceDetails.append(node("summary", "", "Source-key presence · distinguishes absent from explicit null"));
    const presenceTable = node("table", "settings-table");
    const presenceBody = node("tbody");
    Object.entries(record.source_field_presence || {}).sort(([a], [b]) => a.localeCompare(b)).forEach(([field, wasPresent]) => {
      const row = node("tr");
      row.append(node("th", "", field), node("td", "", wasPresent ? "present in source" : "absent from source"));
      presenceBody.append(row);
    });
    presenceTable.append(presenceBody);
    presenceDetails.append(presenceTable);
    settingsPanel.append(presenceDetails);
    content.append(settingsPanel);

    renderSourcePanel(content, record);
    renderAnnotationPanel(content, record);
    renderProbabilityPanel(content, record);

    container.append(content);
    if (!dialog.open && typeof dialog.showModal === "function") dialog.showModal();
    else if (!dialog.open) dialog.setAttribute("open", "");
  }

  function renderSourcePanel(container, record) {
    const panel = node("section", "detail-panel");
    panel.append(node("h3", "", "Original source provenance"));
    const list = node("div", "source-list");
    (record.source_provenance || []).forEach((provenance) => {
      const row = node("div", "source-row");
      const details = node("span", "", `${provenance.source_file} · run index ${provenance.run_index} · export ${provenance.export_updated_at || "time not recorded"}`);
      const filePath = String(provenance.source_file || "").split("/").map(encodeURIComponent).join("/");
      const link = node("a", "", "Open raw Workbench export ↗");
      link.href = `${REPO_RAW_BASE}${filePath}#L1`;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      row.append(details, link);
      list.append(row);
    });
    const idRow = node("div", "source-row");
    idRow.append(node("span", "", `Original generation ID · ${record.generation_id}`));
    const copy = node("button", "copy-id", "Copy ID");
    copy.type = "button";
    copy.addEventListener("click", () => copyText(record.generation_id));
    idRow.append(copy);
    list.append(idRow);
    panel.append(list, node("p", "chart-note", "The export file contains the original Workbench record; use this stable run ID to locate the matching object inside its runs array. The link opens the repository source, not a transformed copy."));
    container.append(panel);
  }

  function renderAnnotationPanel(container, record) {
    const panel = node("section", "detail-panel");
    panel.append(node("h3", "", "Existing annotations + provenance"));
    const current = [...state.annotations, ...state.localAnnotations].filter((annotation) => annotation.generation_id === record.generation_id);
    if (!current.length) panel.append(node("p", "chart-note", "No annotation recorded for this generation yet."));
    current.forEach((annotation) => {
      const card = node("div", "detail-text-block");
      const tags = node("div", "label-row");
      (annotation.labels || []).forEach((label) => tags.append(labelChip(label)));
      card.append(tags);
      card.append(node("p", "exhibit-commentary", annotation.rationale || "No rationale recorded."));
      card.append(node("p", "chart-note", `${annotation.annotator || "Annotator not recorded"} · ${annotation.provenance?.method || "method not recorded"} · ${annotation.provenance?.created_at || "date not recorded"} · ${annotation.provenance?.status || "review status not recorded"}`));
      if (annotation.evidence?.length) {
        annotation.evidence.forEach((evidence) => card.append(node("blockquote", "exhibit-quote", `“${maskDisplayText(evidence.quote || "") }”`)));
      }
      panel.append(card);
    });
    panel.append(node("h3", "", "Add a manual classification"));
    panel.append(createAnnotationForm(record));
    container.append(panel);
  }

  function createAnnotationForm(record) {
    const form = node("form", "annotation-form");
    const annotatorLabel = node("label", "", "Annotator / reviewer");
    const annotatorInput = node("input");
    annotatorInput.name = "annotator";
    annotatorInput.required = true;
    annotatorInput.placeholder = "Name or pseudonymous ID";
    annotatorLabel.append(annotatorInput);
    const rationaleLabel = node("label", "", "Rationale");
    rationaleLabel.classList.add("full-span");
    const rationaleInput = node("textarea");
    rationaleInput.name = "rationale";
    rationaleInput.required = true;
    rationaleInput.placeholder = "Describe the visible evidence. Avoid attributing cause without a controlled comparison.";
    rationaleLabel.append(rationaleInput);
    const evidenceLabel = node("label", "", "Evidence excerpt (optional)");
    evidenceLabel.classList.add("full-span");
    const evidenceInput = node("textarea");
    evidenceInput.name = "evidence";
    evidenceInput.placeholder = "Exact short quote from the recorded completion";
    evidenceLabel.append(evidenceInput);
    const choices = node("div", "annotation-checks full-span");
    state.taxonomy.forEach((term) => {
      const label = node("label", "annotation-check");
      const input = node("input");
      input.type = "checkbox";
      input.name = "labels";
      input.value = term.id;
      label.append(input, document.createTextNode(term.label));
      choices.append(label);
    });
    const actions = node("div", "annotation-actions full-span");
    const save = node("button", "button button-primary", "Save in this browser ↓");
    save.type = "submit";
    const help = node("p", "annotation-help", "Saved locally with annotator, timestamp, method, and review status. Export before closing this browser.");
    actions.append(save, help);
    form.append(annotatorLabel, rationaleLabel, evidenceLabel, choices, actions);
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const labels = $$('input[name="labels"]:checked', form).map((input) => input.value);
      if (!labels.length) {
        showToast("Choose at least one taxonomy label.");
        return;
      }
      const evidence = evidenceInput.value.trim();
      const annotation = {
        annotation_id: `local-${makeUuid()}`,
        generation_id: record.generation_id,
        labels,
        annotator: annotatorInput.value.trim(),
        rationale: rationaleInput.value.trim(),
        evidence: evidence ? [{ quote: evidence }] : [],
        provenance: {
          method: "manual browser annotation",
          created_at: new Date().toISOString(),
          status: "unreviewed",
          source: "Anomaly Atlas local annotation workbench",
          tool: "browser localStorage",
        },
      };
      state.localAnnotations.push(annotation);
      let persisted = true;
      try {
        localStorage.setItem(LOCAL_KEY, JSON.stringify(state.localAnnotations));
      } catch (error) {
        persisted = false;
        console.warn("Could not persist annotation to localStorage.", error);
      }
      updateLocalAnnotationCount();
      renderGallery();
      const selected = state.activeRecord;
      showToast(persisted ? "Annotation saved locally. Export the bundle to keep it." : "Saved for this page session only; browser storage is unavailable.");
      if (selected) openSpecimen(selected);
    });
    return form;
  }

  function makeUuid() {
    if (window.crypto?.randomUUID) return window.crypto.randomUUID();
    return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
  }

  function updateLocalAnnotationCount() {
    const count = state.localAnnotations.length;
    $("#local-annotation-count").textContent = `${count} local annotation${count === 1 ? "" : "s"}`;
  }

  function exportAnnotations() {
    const payload = {
      schema_version: 1,
      taxonomy_version: "1.0.0",
      annotations: [...state.annotations, ...state.localAnnotations],
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = node("a");
    link.href = url;
    link.download = `annotations-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.append(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1200);
    showToast("Annotation bundle downloaded. Validate it before committing.");
  }

  async function copyText(value) {
    try {
      await navigator.clipboard.writeText(value);
      showToast("Generation ID copied.");
    } catch (_error) {
      showToast(value);
    }
  }

  function renderProbabilityPanel(container, record) {
    const panel = node("section", "detail-panel");
    panel.append(node("h3", "", "Token probability trace"));
    if (!Array.isArray(record.logprobs) || !record.logprobs.length) {
      let message = "No token-level logprob array is available in this public record.";
      if (record.logprobs_suppressed_for_privacy) message = "The source has a logprob sequence, but the public projection suppresses it because structured values were detected in the text.";
      else if (record.sampling?.logprobs !== undefined) message = `The source config records a logprobs request of ${exact(record.sampling.logprobs)}, but no token-level array was retained on this run.`;
      panel.append(node("p", "chart-note", message));
      container.append(panel);
      return;
    }
    const note = node("p", "chart-note", "Each point is the chosen token’s reported log probability at that position. Values are not converted to percentages; alternative bars are a display scale, not normalized probabilities.");
    panel.append(note);
    const chartBox = node("div", "logprob-box");
    const chart = svgNode("svg", { viewBox: "0 0 720 200", class: "logprob-svg", role: "img", "aria-label": "Token-by-token recorded log probability" });
    chartBox.append(chart);
    const readout = node("div", "logprob-token-readout");
    const chosen = node("span");
    const value = node("strong");
    const position = node("span");
    readout.append(chosen, value, position);
    const slider = node("input", "token-slider");
    slider.type = "range";
    slider.min = "0";
    slider.max = String(record.logprobs.length - 1);
    slider.value = "0";
    slider.setAttribute("aria-label", "Select token position");
    const candidates = node("div", "candidate-list");
    chartBox.append(readout, slider, candidates);
    panel.append(chartBox);

    const points = record.logprobs.map((entry, index) => ({ index, value: Number(entry.logprob) })).filter((item) => Number.isFinite(item.value));
    if (!points.length) {
      panel.append(node("p", "chart-note", "The source logprob array contains no numeric values for plotting."));
      container.append(panel);
      return;
    }
    const w = 720;
    const h = 200;
    const left = 43;
    const right = 15;
    const top = 16;
    const bottom = 29;
    const plotW = w - left - right;
    const plotH = h - top - bottom;
    const minimum = Math.min(...points.map((point) => point.value));
    const maximum = Math.max(...points.map((point) => point.value));
    const span = maximum - minimum || 1;
    [0, .5, 1].forEach((fraction) => {
      const y = top + fraction * plotH;
      chart.append(svgNode("line", { x1: left, y1: y, x2: w - right, y2: y, class: "chart-grid-line" }));
      const labelValue = maximum - fraction * span;
      chart.append(svgNode("text", { x: left - 6, y: y + 4, class: "chart-axis-label", "text-anchor": "end" }, labelValue.toFixed(2)));
    });
    const coords = points.map((point) => {
      const x = left + (points.length === 1 ? 0 : (point.index / (record.logprobs.length - 1)) * plotW);
      const y = top + ((maximum - point.value) / span) * plotH;
      return `${x},${y}`;
    }).join(" ");
    chart.append(svgNode("polyline", { points: coords, fill: "none", stroke: "#c1ef75", "stroke-width": 1.35, "stroke-linejoin": "round", "stroke-linecap": "round" }));
    chart.append(svgNode("text", { x: left, y: h - 8, class: "chart-axis-label" }, "token 1"));
    chart.append(svgNode("text", { x: w - right, y: h - 8, class: "chart-axis-label", "text-anchor": "end" }, `token ${record.logprobs.length}`));
    const marker = svgNode("line", { x1: left, y1: top, x2: left, y2: top + plotH, stroke: "#82a9ff", "stroke-width": 1.3, "stroke-dasharray": "3 3" });
    chart.append(marker);
    const pointLayer = svgNode("g");
    points.forEach((point) => {
      const x = left + (points.length === 1 ? 0 : (point.index / (record.logprobs.length - 1)) * plotW);
      const y = top + ((maximum - point.value) / span) * plotH;
      const circle = svgNode("circle", { cx: x, cy: y, r: 2.2, fill: "#82a9ff", opacity: .7 });
      circle.append(svgNode("title", {}, `Token ${point.index + 1}: logprob ${point.value}`));
      pointLayer.append(circle);
    });
    chart.append(pointLayer);

    function updateSelected(index) {
      const entry = record.logprobs[index];
      if (!entry) return;
      const x = left + (record.logprobs.length === 1 ? 0 : (index / (record.logprobs.length - 1)) * plotW);
      marker.setAttribute("x1", String(x));
      marker.setAttribute("x2", String(x));
      chosen.textContent = `Token: “${maskDisplayText(entry.token || "") || "∅"}”`;
      value.textContent = `logprob ${exact(entry.logprob)}`;
      position.textContent = `${index + 1} / ${record.logprobs.length}`;
      candidates.replaceChildren();
      const alternatives = Array.isArray(entry.top) ? entry.top : [];
      if (!alternatives.length) {
        candidates.append(node("p", "chart-note", "No top alternatives recorded at this token position."));
        return;
      }
      alternatives.forEach((candidate) => {
        const row = node("div", "candidate-row");
        row.append(node("span", "", `“${maskDisplayText(candidate.token || "") || "∅"}”`));
        const track = node("div", "candidate-bar-track");
        const bar = node("div", "candidate-bar");
        const valueNumber = Number(candidate.logprob);
        const widthPercent = Number.isFinite(valueNumber) ? Math.max(2, Math.min(100, ((valueNumber - minimum) / span) * 100)) : 2;
        bar.style.width = `${widthPercent}%`;
        track.append(bar);
        row.append(track, node("span", "candidate-logprob", exact(candidate.logprob)));
        candidates.append(row);
      });
    }
    slider.addEventListener("input", () => updateSelected(Number(slider.value)));
    updateSelected(0);
    container.append(panel);
  }

  init();
})();
