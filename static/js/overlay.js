(() => {
  "use strict";

  const preview = Boolean(window.OVERLAY_PREVIEW);
  const byId = (id) => document.getElementById(id);
  const elements = {
    overlay: byId("flightOverlay"),
    statusRail: byId("statusRail"),
    primary: byId("primaryMetrics"),
    secondary: byId("secondaryMetrics"),
    heading: byId("headingInstrument"),
    headingValue: byId("headingValue"),
    headingTicks: byId("headingTicks"),
    progress: byId("flightProgress"),
    fill: byId("routeFill"),
    marker: byId("aircraftMarker"),
    progressText: byId("progressText"),
    timeline: byId("phaseTimeline"),
    phasePill: byId("phasePill"),
    offline: byId("offlineNotice"),
  };

  const metrics = {
    airspeed: { label: "Airspeed", format: (v) => number(v, 0, "kt") },
    groundSpeed: { label: "Groundspeed", format: (v) => number(v, 0, "kt") },
    altitude: { label: "Altitude", format: (v) => number(v, 0, "ft") },
    verticalSpeed: { label: "Vertical speed", format: (v) => signed(v, 0, "fpm") },
    distance: { label: "Next waypoint", format: (v) => number(v, 1, "nm") },
    latitude: { label: "Latitude", format: (v) => coordinate(v, "N", "S") },
    longitude: { label: "Longitude", format: (v) => coordinate(v, "E", "W") },
    ete: { label: "Time enroute", format: duration },
    eta: { label: "ETA", format: (v) => value(v) },
  };

  let catalog = null;
  let currentSettings = null;
  let targetHeading = 0;
  let displayedHeading = 0;
  let targetProgress = 0;
  let displayedProgress = 0;
  let pollTimer = null;
  let lastTickBase = null;

  function value(raw) {
    return raw === null || raw === undefined || raw === "" ? null : String(raw);
  }

  function number(raw, digits, unit) {
    if (raw === null || raw === undefined || !Number.isFinite(Number(raw))) return null;
    return `${Number(raw).toLocaleString(undefined, {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    })}<small>${unit}</small>`;
  }

  function signed(raw, digits, unit) {
    if (raw === null || raw === undefined || !Number.isFinite(Number(raw))) return null;
    const numeric = Number(raw);
    const prefix = numeric > 0 ? "+" : "";
    return `${prefix}${numeric.toLocaleString(undefined, {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    })}<small>${unit}</small>`;
  }

  function coordinate(raw, positive, negative) {
    if (raw === null || raw === undefined || !Number.isFinite(Number(raw))) return null;
    const numeric = Number(raw);
    return `${Math.abs(numeric).toFixed(4)}°<small>${numeric >= 0 ? positive : negative}</small>`;
  }

  function duration(raw) {
    if (raw === null || raw === undefined || !Number.isFinite(Number(raw))) return null;
    const seconds = Math.max(0, Math.round(Number(raw)));
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}<small>h</small> ${String(minutes).padStart(2, "0")}<small>m</small>`;
  }

  function hexRgb(hex) {
    const clean = hex.replace("#", "");
    const value = Number.parseInt(clean.length === 3
      ? clean.split("").map((char) => char + char).join("")
      : clean, 16);
    return `${(value >> 16) & 255}, ${(value >> 8) & 255}, ${value & 255}`;
  }

  function createMetric(metricId) {
    const spec = metrics[metricId];
    const wrapper = document.createElement("div");
    wrapper.className = "metric";
    wrapper.dataset.metric = metricId;
    wrapper.innerHTML = `<span class="metric-label">${spec.label}</span>
      <span class="metric-value inop" data-value="${metricId}">INOP</span>`;
    return wrapper;
  }

  function applySettings(settings, theme) {
    currentSettings = settings;
    const appearance = settings.appearance;
    const activeTheme = theme || catalog?.themes?.find((item) => item.id === appearance.theme);
    if (activeTheme) {
      const root = document.documentElement.style;
      for (const [key, cssName] of Object.entries({
        panel: "--panel", panelAlt: "--panel-alt", text: "--text", muted: "--muted",
        accent: "--accent", accentAlt: "--accent-alt", good: "--good", warning: "--warning",
      })) root.setProperty(cssName, activeTheme[key]);
      root.setProperty("--panel-rgb", hexRgb(activeTheme.panel));
    }
    const root = document.documentElement.style;
    root.setProperty("--panel-alpha", Math.max(0, (100 - appearance.transparency) / 100));
    root.setProperty("--overlay-scale", appearance.scale / 100);
    root.setProperty("--overlay-width", `${appearance.width}vw`);
    root.setProperty("--overlay-x", `${appearance.offsetX}px`);
    root.setProperty("--overlay-y", `${appearance.offsetY}px`);
    root.setProperty("--motion-duration", `${80 + appearance.motionSmoothing * 5}ms`);
    elements.overlay.classList.toggle("position-bottom", appearance.position === "bottom");
    elements.statusRail.classList.toggle("is-hidden", !appearance.showStatusRail);
    elements.heading.classList.toggle("is-hidden", !settings.layout.showHeading);
    elements.progress.classList.toggle("is-hidden", !settings.layout.showProgress);
    elements.timeline.classList.toggle("is-hidden", !settings.layout.showPhaseTimeline);
    elements.marker.src = `/static/images/aircraft/${appearance.aircraftIcon}.svg`;

    elements.primary.replaceChildren(...settings.layout.primaryMetrics
      .filter((id) => appearance.showCoordinates || !["latitude", "longitude"].includes(id))
      .map(createMetric));
    elements.secondary.replaceChildren(...settings.layout.secondaryMetrics
      .filter((id) => appearance.showCoordinates || !["latitude", "longitude"].includes(id))
      .map(createMetric));
  }

  function statusBadge(id, state, title) {
    const badge = byId(id);
    badge.dataset.state = state || "disconnected";
    if (title) badge.title = title;
  }

  function setMetric(id, formatted) {
    const target = document.querySelector(`[data-value="${id}"]`);
    if (!target) return;
    target.classList.toggle("inop", formatted === null);
    target.innerHTML = formatted === null ? "INOP" : formatted;
  }

  function updateTimeline(phase) {
    if (!phase?.timeline) return;
    elements.timeline.replaceChildren(...phase.timeline.map((item, index) => {
      const node = document.createElement("span");
      node.className = `timeline-phase${index < phase.index ? " complete" : ""}${index === phase.index ? " current" : ""}`;
      node.textContent = item.short;
      return node;
    }));
  }

  function renderData(payload) {
    const t = payload.telemetry || {};
    setMetric("airspeed", metrics.airspeed.format(t.airspeed));
    setMetric("groundSpeed", metrics.groundSpeed.format(t.ground_speed));
    setMetric("altitude", metrics.altitude.format(t.altitude));
    setMetric("verticalSpeed", metrics.verticalSpeed.format(t.vertical_speed));
    setMetric("distance", metrics.distance.format(t.distance));
    setMetric("latitude", metrics.latitude.format(t.latitude));
    setMetric("longitude", metrics.longitude.format(t.longitude));
    setMetric("ete", metrics.ete.format(t.gps_ete));
    setMetric("eta", metrics.eta.format(t.gps_eta_formatted));

    if (Number.isFinite(Number(t.heading))) targetHeading = ((Number(t.heading) % 360) + 360) % 360;
    const progressAvailable = Number.isFinite(Number(payload.progress))
      && payload.progress !== null;
    if (progressAvailable) {
      targetProgress = Math.max(0, Math.min(100, Number(payload.progress)));
    }
    elements.progress.classList.toggle("progress-unavailable", !progressAvailable);
    elements.marker.classList.toggle("is-hidden", !progressAvailable);
    const phase = payload.phase || {};
    elements.phasePill.textContent = phase.label || "Awaiting flight";
    updateTimeline(phase);

    const plan = payload.flightPlan || payload.integrations?.simbrief?.flightPlan;
    const siFlight = payload.integrations?.sayintentions?.flight;
    const origin = plan?.origin || siFlight?.origin || "DEP";
    const destination = plan?.destination || siFlight?.destination || "ARR";
    byId("originCode").textContent = origin;
    byId("originName").textContent = plan?.originName || "Departure";
    byId("destinationCode").textContent = destination;
    byId("destinationName").textContent = plan?.destinationName || "Arrival";
    byId("callsign").textContent = plan?.callsign || siFlight?.callsign || "FLIGHT SIM OVERLAY";
    byId("routeLabel").textContent = origin !== "DEP" || destination !== "ARR"
      ? `${origin}  →  ${destination}`
      : "Awaiting flight plan";

    statusBadge("simconnectStatus", payload.connection?.state, payload.connection?.label);
    statusBadge("simbriefStatus", payload.integrations?.simbrief?.state, payload.integrations?.simbrief?.label);
    statusBadge("sayintentionsStatus", payload.integrations?.sayintentions?.state, payload.integrations?.sayintentions?.label);
    statusBadge("vatsimStatus", payload.integrations?.vatsim?.state, payload.integrations?.vatsim?.label);
    const unavailable = !["connected", "demo"].includes(payload.connection?.state);
    elements.offline.classList.toggle("visible", unavailable && !preview);
  }

  function sampleData() {
    const seconds = Date.now() / 1000;
    const progress = 42 + Math.sin(seconds / 9) * 2;
    return {
      telemetry: {
        airspeed: 286, ground_speed: 301, altitude: 18420, vertical_speed: 1650,
        distance: 74.2, latitude: 36.2481, longitude: -114.6842,
        gps_ete: 4120, gps_eta_formatted: "21:46Z", heading: (82 + seconds / 3) % 360,
      },
      connection: { state: "demo", label: "Preview" },
      progress,
      phase: {
        id: "climb", label: "Climb", index: 3,
        timeline: [
          ["at_gate", "Gate"], ["taxiing_departure", "Taxi"], ["departure", "Depart"],
          ["climb", "Climb"], ["cruise", "Cruise"], ["descent", "Descend"],
          ["approach", "Approach"], ["arrival", "Land"], ["taxiing_arrival", "Taxi"],
          ["at_gate_arrival", "Gate"],
        ].map(([id, short]) => ({ id, short })),
      },
      flightPlan: {
        origin: "KGCN", destination: "KLAS", originName: "Grand Canyon",
        destinationName: "Harry Reid Intl", callsign: "N825G",
      },
      integrations: {
        simbrief: { state: "connected", label: "KGCN → KLAS" },
        sayintentions: { state: "connected", label: "N825G" },
        vatsim: { state: "online", label: "Network online" },
      },
    };
  }

  function headingLabel(degrees) {
    const normalized = ((degrees % 360) + 360) % 360;
    const cardinal = { 0: "N", 90: "E", 180: "S", 270: "W" };
    return cardinal[normalized] || String(normalized).padStart(3, "0");
  }

  function renderHeading() {
    const rounded = Math.round(displayedHeading);
    elements.headingValue.textContent = String((rounded + 360) % 360).padStart(3, "0");
    const base = Math.round(displayedHeading / 10) * 10;
    if (base !== lastTickBase) {
      lastTickBase = base;
      const nodes = [];
      for (let delta = -100; delta <= 100; delta += 10) {
        const tick = document.createElement("i");
        const heading = ((base + delta) % 360 + 360) % 360;
        tick.className = `heading-tick${heading % 30 === 0 ? " major" : ""}`;
        tick.dataset.heading = heading;
        if (heading % 30 === 0) tick.innerHTML = `<span>${headingLabel(heading)}</span>`;
        nodes.push(tick);
      }
      elements.headingTicks.replaceChildren(...nodes);
    }
    elements.headingTicks.querySelectorAll(".heading-tick").forEach((tick) => {
      let delta = Number(tick.dataset.heading) - displayedHeading;
      delta = ((delta + 540) % 360) - 180;
      tick.style.left = `${50 + delta * 0.52}%`;
    });
  }

  function animate() {
    const smoothing = currentSettings?.appearance?.motionSmoothing ?? 72;
    const factor = 0.04 + (100 - smoothing) * 0.0018;
    let headingDelta = ((targetHeading - displayedHeading + 540) % 360) - 180;
    displayedHeading = (displayedHeading + headingDelta * factor + 360) % 360;
    displayedProgress += (targetProgress - displayedProgress) * factor;
    document.documentElement.style.setProperty("--progress", displayedProgress.toFixed(3));
    elements.progressText.textContent = elements.progress.classList.contains("progress-unavailable")
      ? "ROUTE UNAVAILABLE"
      : `${Math.round(displayedProgress)}%`;
    renderHeading();
    requestAnimationFrame(animate);
  }

  async function poll() {
    try {
      const response = await fetch("/api/data", { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      renderData(preview && !["connected", "demo"].includes(data.connection?.state) ? sampleData() : data);
    } catch (error) {
      if (preview) renderData(sampleData());
      else elements.offline.classList.add("visible");
    }
  }

  function schedulePolling() {
    if (pollTimer) clearInterval(pollTimer);
    const interval = currentSettings?.telemetry?.pollIntervalMs || 500;
    pollTimer = setInterval(poll, interval);
  }

  async function init() {
    try {
      const response = await fetch("/api/settings", { cache: "no-store" });
      catalog = await response.json();
      applySettings(catalog.settings, catalog.theme);
    } catch (error) {
      console.error("Unable to load overlay settings", error);
    }
    if (preview) renderData(sampleData());
    await poll();
    schedulePolling();
    requestAnimationFrame(animate);
  }

  window.addEventListener("message", (event) => {
    if (!preview || event.data?.type !== "overlay-settings-preview") return;
    applySettings(event.data.settings, event.data.theme);
  });
  window.addEventListener("storage", (event) => {
    if (event.key === "flight-overlay-settings-updated") init();
  });
  init();
})();
