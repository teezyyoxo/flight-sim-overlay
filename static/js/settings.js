(() => {
  "use strict";

  const metricNames = {
    airspeed: "Airspeed", groundSpeed: "Groundspeed", altitude: "Altitude",
    verticalSpeed: "Vertical speed", distance: "Next waypoint distance",
    latitude: "Latitude", longitude: "Longitude", ete: "Time enroute", eta: "ETA",
  };
  let catalog;
  let draft;
  let dirty = false;
  let toastTimer;
  const frame = document.getElementById("previewFrame");
  const saveBar = document.getElementById("saveBar");

  function clone(value) { return JSON.parse(JSON.stringify(value)); }
  function pathGet(object, path) { return path.split(".").reduce((value, key) => value?.[key], object); }
  function pathSet(object, path, value) {
    const keys = path.split(".");
    const last = keys.pop();
    const target = keys.reduce((value, key) => value[key], object);
    target[last] = value;
  }
  function activeTheme() { return catalog.themes.find((theme) => theme.id === draft.appearance.theme); }

  function markDirty() {
    dirty = true;
    saveBar.classList.add("visible");
    sendPreview();
  }

  function sendPreview() {
    frame.contentWindow?.postMessage({
      type: "overlay-settings-preview",
      settings: draft,
      theme: activeTheme(),
    }, window.location.origin);
  }

  function showToast(message, error = false) {
    const toast = document.getElementById("toast");
    toast.textContent = message;
    toast.style.borderColor = error ? "#633636" : "";
    toast.style.color = error ? "#ffcaca" : "";
    toast.classList.add("visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("visible"), 2600);
  }

  function renderThemes() {
    const grid = document.getElementById("themeGrid");
    grid.replaceChildren(...catalog.themes.map((theme) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `theme-card${theme.id === draft.appearance.theme ? " selected" : ""}`;
      button.innerHTML = `<b>${theme.name}</b><small>${theme.description}</small>
        <span class="swatches"><i style="background:${theme.panel}"></i><i style="background:${theme.accent}"></i><i style="background:${theme.accentAlt}"></i></span>`;
      button.addEventListener("click", () => {
        draft.appearance.theme = theme.id;
        renderThemes();
        markDirty();
      });
      return button;
    }));
  }

  function renderAircraft() {
    const grid = document.getElementById("aircraftGrid");
    grid.replaceChildren(...catalog.aircraftIcons.map((aircraft) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `aircraft-option${aircraft.id === draft.appearance.aircraftIcon ? " selected" : ""}`;
      button.innerHTML = `<img src="/static/images/aircraft/${aircraft.id}.svg" alt=""><span>${aircraft.name}</span>`;
      button.addEventListener("click", () => {
        draft.appearance.aircraftIcon = aircraft.id;
        renderAircraft();
        markDirty();
      });
      return button;
    }));
  }

  function moveMetric(bank, index, action) {
    const sourceKey = bank === "primary" ? "primaryMetrics" : "secondaryMetrics";
    const otherKey = bank === "primary" ? "secondaryMetrics" : "primaryMetrics";
    const list = draft.layout[sourceKey];
    if (action === "up" && index > 0) [list[index - 1], list[index]] = [list[index], list[index - 1]];
    if (action === "down" && index < list.length - 1) [list[index + 1], list[index]] = [list[index], list[index + 1]];
    if (action === "other" && list.length > 1) draft.layout[otherKey].push(list.splice(index, 1)[0]);
    renderMetricLists();
    markDirty();
  }

  function metricRow(metric, bank, index) {
    const row = document.createElement("div");
    row.className = "metric-row";
    row.innerHTML = `<span class="grip">⠿</span><b>${metricNames[metric]}</b><span class="metric-actions">
      <button type="button" data-action="up" title="Move up">↑</button>
      <button type="button" data-action="down" title="Move down">↓</button>
      <button type="button" data-action="other" title="Move to other bank">⇄</button></span>`;
    row.querySelectorAll("button").forEach((button) => button.addEventListener("click",
      () => moveMetric(bank, index, button.dataset.action)));
    return row;
  }

  function renderMetricLists() {
    document.getElementById("primaryMetricList").replaceChildren(
      ...draft.layout.primaryMetrics.map((metric, index) => metricRow(metric, "primary", index))
    );
    document.getElementById("secondaryMetricList").replaceChildren(
      ...draft.layout.secondaryMetrics.map((metric, index) => metricRow(metric, "secondary", index))
    );
  }

  function syncInputs() {
    document.querySelectorAll("[data-path]").forEach((input) => {
      const current = pathGet(draft, input.dataset.path);
      if (input.type === "checkbox") input.checked = Boolean(current);
      else input.value = current;
    });
  }

  function renderAll() {
    syncInputs();
    renderThemes();
    renderAircraft();
    renderMetricLists();
    sendPreview();
  }

  function coerce(input) {
    if (input.type === "checkbox") return input.checked;
    if (input.type === "number" || input.type === "range" || input.tagName === "SELECT" && input.querySelector("option")?.value.match(/^\d/)) {
      return Number(input.value);
    }
    return input.value;
  }

  function bindInputs() {
    document.querySelectorAll("[data-path]").forEach((input) => {
      const eventName = input.type === "range" ? "input" : "change";
      input.addEventListener(eventName, () => {
        pathSet(draft, input.dataset.path, coerce(input));
        document.querySelectorAll(`[data-path="${input.dataset.path}"]`).forEach((peer) => {
          if (peer !== input) {
            if (peer.type === "checkbox") peer.checked = Boolean(pathGet(draft, input.dataset.path));
            else peer.value = pathGet(draft, input.dataset.path);
          }
        });
        markDirty();
      });
      if (input.type === "text" || input.type === "number") {
        input.addEventListener("input", () => {
          if (input.validity.valid) {
            pathSet(draft, input.dataset.path, coerce(input));
            markDirty();
          }
        });
      }
    });
  }

  async function save() {
    try {
      const response = await fetch("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draft),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      catalog = await response.json();
      draft = clone(catalog.settings);
      dirty = false;
      saveBar.classList.remove("visible");
      renderAll();
      localStorage.setItem("flight-overlay-settings-updated", String(Date.now()));
      showToast("Settings saved");
    } catch (error) {
      showToast(`Save failed: ${error.message}`, true);
    }
  }

  async function reset() {
    try {
      const response = await fetch("/api/settings/reset", { method: "POST" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      catalog = await response.json();
      draft = clone(catalog.settings);
      dirty = false;
      saveBar.classList.remove("visible");
      renderAll();
      localStorage.setItem("flight-overlay-settings-updated", String(Date.now()));
      showToast("Defaults restored");
    } catch (error) {
      showToast(`Reset failed: ${error.message}`, true);
    }
  }

  async function refreshStatus() {
    try {
      const [healthResponse, dataResponse] = await Promise.all([
        fetch("/healthz", { cache: "no-store" }),
        fetch("/api/data", { cache: "no-store" }),
      ]);
      const health = await healthResponse.json();
      const data = await dataResponse.json();
      const header = document.getElementById("headerSimStatus");
      header.dataset.state = health.simconnect?.state || "disconnected";
      header.lastChild.textContent = ` ${health.simconnect?.label || "SimConnect"}`;
      for (const [key, id] of Object.entries({
        simbrief: "simbriefState", vatsim: "vatsimState", sayintentions: "sayintentionsState",
      })) {
        const node = document.getElementById(id);
        node.dataset.state = data.integrations?.[key]?.state || "";
        node.textContent = data.integrations?.[key]?.label || "Unavailable";
      }
    } catch (_) { /* The next poll will recover. */ }
  }

  async function init() {
    const response = await fetch("/api/settings", { cache: "no-store" });
    catalog = await response.json();
    draft = clone(catalog.settings);
    bindInputs();
    renderAll();
    frame.addEventListener("load", sendPreview);

    document.getElementById("randomTheme").addEventListener("click", () => {
      const choices = catalog.themes.filter((theme) => theme.id !== draft.appearance.theme);
      draft.appearance.theme = choices[Math.floor(Math.random() * choices.length)].id;
      renderThemes();
      markDirty();
    });
    document.getElementById("saveButton").addEventListener("click", save);
    document.getElementById("saveButtonBottom").addEventListener("click", save);
    document.getElementById("resetButton").addEventListener("click", () => document.getElementById("resetDialog").showModal());
    document.getElementById("confirmReset").addEventListener("click", reset);
    document.getElementById("refreshSimbrief").addEventListener("click", async () => {
      if (dirty) await save();
      await fetch("/api/simbrief/refresh", { method: "POST" });
      showToast("SimBrief refresh queued");
      setTimeout(refreshStatus, 1500);
    });
    document.getElementById("previewSize").addEventListener("click", () => document.querySelector(".preview-pane").classList.toggle("expanded"));
    window.addEventListener("beforeunload", (event) => {
      if (!dirty) return;
      event.preventDefault();
      event.returnValue = "";
    });
    document.querySelectorAll(".section-nav a").forEach((link) => link.addEventListener("click", () => {
      document.querySelectorAll(".section-nav a").forEach((item) => item.classList.remove("active"));
      link.classList.add("active");
    }));
    refreshStatus();
    setInterval(refreshStatus, 5000);
  }

  init().catch((error) => showToast(`Settings failed to load: ${error.message}`, true));
})();
