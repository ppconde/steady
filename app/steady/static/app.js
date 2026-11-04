"use strict";
const $ = (id) => document.getElementById(id);
const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const RANK = { easy: 1, moderate: 2, hard: 3 };

function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) k === "class" ? (el.className = v) : el.setAttribute(k, v);
  for (const k of kids) if (k != null) el.append(k);
  return el;
}
const parse = (s) => { const [y, m, d] = s.split("-").map(Number); return new Date(y, m - 1, d); };
const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const addDays = (d, n) => new Date(d.getFullYear(), d.getMonth(), d.getDate() + n);
const monday = (d) => addDays(d, -((d.getDay() + 6) % 7));
const short = (d) => `${d.getDate()} ${MONTHS[d.getMonth()]}`;
const pace = (s) => { s = Math.round(s); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };
const today = () => { const n = new Date(); return new Date(n.getFullYear(), n.getMonth(), n.getDate()); };

function isoWeek(d) {
  const t = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  t.setUTCDate(t.getUTCDate() + 4 - (t.getUTCDay() || 7));
  return Math.ceil(((t - Date.UTC(t.getUTCFullYear(), 0, 1)) / 864e5 + 1) / 7);
}
function ago(date) {
  const hrs = (Date.now() - date) / 36e5;
  if (hrs < 1) return "just now";
  if (hrs < 48) return `${Math.round(hrs)} h ago`;
  return `${Math.round(hrs / 24)} days ago`;
}
function when(s) {
  const d = new Date(s);
  return `${DAYS[(d.getDay() + 6) % 7]} ${short(d)}, ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

let weekStart = monday(today());

async function load() {
  const end = addDays(weekStart, 6);
  history.replaceState(null, "", weekStart.getTime() === monday(today()).getTime() ? "/" : `/?end=${iso(end)}`);
  const res = await fetch(`/api/week?end=${iso(end)}`);
  if (!res.ok) { $("take-text").textContent = "Couldn't load this week. Is the app running?"; return; }
  render(await res.json(), end);
}

// Sparkline of [isoDate, value] points; `up` draws bigger values higher.
function spark(svg, points, up) {
  svg.replaceChildren();
  if (points.length < 2) return;
  const vals = points.map((p) => p[1]), lo = Math.min(...vals), hi = Math.max(...vals);
  const t0 = parse(points[0][0]), span = Math.max(1, parse(points.at(-1)[0]) - t0);
  const y = (v) => (hi === lo ? 25 : up ? 44 - ((v - lo) / (hi - lo)) * 38 : 6 + ((v - lo) / (hi - lo)) * 38);
  const line = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
  Object.entries({ points: points.map(([d, v]) => `${((parse(d) - t0) / span) * 196 + 2},${y(v)}`).join(" "),
    fill: "none", stroke: "#151515", "stroke-width": 5, "stroke-linecap": "round", "stroke-linejoin": "round",
    "vector-effect": "non-scaling-stroke" }).forEach(([k, val]) => line.setAttribute(k, val));
  svg.append(line);
}

function render({ report: r, review, last_sync }, end) {
  const current = weekStart.getTime() === monday(today()).getTime();
  $("weekno").textContent = `Week ${isoWeek(weekStart)}`;
  $("dates").textContent = `${short(weekStart)} – ${short(end)}`;
  $("next").disabled = current;
  $("week-opt").textContent = current ? "This week" : `Week ${isoWeek(weekStart)}`;

  const sync = $("sync");
  if (last_sync) {
    const d = new Date(last_sync), stale = Date.now() - d > 864e5;
    sync.textContent = `Last sync ${ago(d)}${stale ? " · check the Garmin login" : ""}`;
    sync.classList.toggle("stale", stale);
  } else { sync.textContent = "No sync yet"; sync.classList.add("stale"); }

  // verdict
  const V = { yes: "Yes ↗", no: "No ↘", mixed: "Mixed", not_enough_data: "Building your baseline" };
  $("verdict").textContent = V[r.verdict];
  $("verdict").style.fontSize = r.verdict === "not_enough_data" ? "44px" : "";
  document.querySelector(".verdict").dataset.v = r.verdict;
  const word = { up: "improving", down: "slipping", flat: "holding steady" };
  $("verdict-line").textContent = "Each signal compared with the period before";
  const MARK = { up: "M3 13 L9 19 L21 5", down: "M5 5 L19 19 M19 5 L5 19", flat: "M2 12 C6 7 9 17 13 12 C16 8 19 13 22 11" };
  const W = r.weight;
  const sig = [
    ["Running", r.running.direction, r.running.change == null ? "not enough runs"
      : `${Math.abs(Math.round(r.running.change))} s/km ${r.running.change < 0 ? "faster" : "slower"}`],
    ["Strength", r.strength.direction, r.strength.total ? `${r.strength.up} of ${r.strength.total} exercises up` : "not enough data"],
    ["Weight", W.direction, W.status == null ? (W.target == null && W.avg != null ? "no Garmin goal set" : "not enough weigh-ins")
      : W.status === "on_track" ? "on target" : `${Math.abs(W.avg - W.target).toFixed(1)} kg from target`],
  ];
  const svg = (d) => { const s = document.createElementNS("http://www.w3.org/2000/svg", "svg"); s.setAttribute("viewBox", "0 0 24 24");
    s.setAttribute("aria-hidden", "true"); const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
    p.setAttribute("d", d); s.append(p); return s; };
  $("signals").replaceChildren(...sig.map(([name, dir, note]) => h("li", { class: `sig ${dir || "none"}` },
    dir ? svg(MARK[dir]) : svg("M12 3 A9 9 0 1 1 11.9 3"), h("b", {}, name),
    h("span", {}, ` ${dir ? word[dir] : "no call yet"} · ${note}`))));

  // gauge
  const G = { fresh: ["No · fresh", 150], normal: ["No · normal", 90], strained: ["Strained", 30], building_baseline: ["Building baseline", null] };
  const [gw, angle] = G[r.gauge];
  $("gauge-word").textContent = gw;
  document.querySelector(".gauge").dataset.g = r.gauge;
  const needle = $("needle");
  needle.style.display = angle == null ? "none" : "";
  if (angle != null) {
    const a = (angle * Math.PI) / 180;
    needle.setAttribute("x2", 100 + 65 * Math.cos(a));
    needle.setAttribute("y2", 100 - 65 * Math.sin(a));
  }
  const n = r.latest, bits = [];
  if (n && n.hrv != null) bits.push(`HRV ${Math.round(n.hrv)}`);
  if (n && n.rhr != null) bits.push(`RHR ${Math.round(n.rhr)}`);
  if (r.missing_nights === 3) bits.push("no recovery data lately");
  else if (r.gauge === "building_baseline") bits.push("2 more weeks of sleep");
  else bits.push(r.off_signals.length ? `off: ${r.off_signals.join(", ")}` : "normal range");
  $("gauge-line").textContent = bits.join(" · ");

  // running
  const run = r.running;
  $("pace").replaceChildren(run.current ? pace(run.current) : "–", run.current ? h("small", {}, "/km") : null);
  $("pace-line").textContent = run.change == null ? (run.points.length ? "Need 4 runs for a trend" : "No comparable runs")
    : `${Math.abs(Math.round(run.change))} s/km ${run.change < 0 ? "faster" : "slower"} over the period`;
  spark($("trend"), run.points, false);
  $("trend").classList.toggle("good", run.change != null && run.change < 0);

  // weight
  const wt = r.weight, kg = (x) => x.toFixed(1);
  const shown = wt.avg ?? wt.latest;
  $("kg").replaceChildren(shown != null ? kg(shown) : "–", shown != null ? h("small", {}, " kg") : null);
  const S = { closer: "moving toward target", further: "moving away from target", on_track: "on target", steady: "holding" };
  $("kg-line").textContent = shown == null ? "No weigh-ins yet"
    : wt.target == null ? "Set a weight goal in Garmin Connect"
    : `${kg(Math.abs(shown - wt.target))} kg ${shown > wt.target ? "above" : "below"} ${kg(wt.target)} kg · ${S[wt.status] ?? "need more weigh-ins"}`;
  spark($("wtrend"), wt.points, true);
  $("wtrend").classList.toggle("good", wt.status === "closer" || wt.status === "on_track");

  // sleep
  const hm = (s) => { const m = Math.round(s / 60); return `${Math.floor(m / 60)}h ${String(m % 60).padStart(2, "0")}m`; };
  const sl = r.sleep, last = sl.last;
  $("slept").textContent = last ? hm(last.sleep_s) : "–";
  $("sleep-score").textContent = last ? [last.score != null ? `Sleep score ${Math.round(last.score)}` : null,
    `night ending ${short(parse(last.day))}`].filter(Boolean).join(" · ") : "No sleep data yet";
  const stages = last ? [["deep", "Deep", last.deep_s], ["rem", "REM", last.rem_s], ["light", "Light", last.light_s],
    ["awake", "Awake", last.awake_s]].filter((x) => x[2]) : [];
  $("stages").replaceChildren(...stages.map(([k, , v]) => h("i", { class: `s-${k}`, style: `flex-grow:${v}` })));
  $("stage-key").replaceChildren(...stages.map(([k, n, v]) => h("li", { class: `s-${k}` }, `${n} ${hm(v)}`)));
  const tday = iso(today());
  $("nights").replaceChildren(...r.week.map((c, i) => h("li", { class: c.day === tday ? "today" : "" },
    h("span", { class: c.sleep_s ? "nb" : "nb empty", style: `height:${Math.round(Math.min(1, (c.sleep_s || 0) / 36000) * 80)}px` }),
    h("span", { class: "v" }, c.sleep_s ? hm(c.sleep_s).replace("h ", ":").replace("m", "") : "–"),
    h("span", { class: "d" }, DAYS[i]))));
  let line = sl.avg_s == null ? "Need 3 nights for an average" : `${sl.recent_days}-night average ${hm(sl.avg_s)}`;
  if (sl.avg_s != null && sl.before_s != null) {
    const d = Math.round((sl.avg_s - sl.before_s) / 60);
    line += Math.abs(d) < 10 ? " · about the same as the 4 weeks before" : ` · ${Math.abs(d)} min ${d > 0 ? "more" : "less"} than the 4 weeks before`;
  }
  $("sleep-line").textContent = line;

  // strength
  const st = r.strength;
  $("str-n").replaceChildren(st.total ? String(st.up) : "–", st.total ? h("span", {}, `/${st.total}`) : null);
  const pretty = (e) => { const s = e.split("/").pop().replaceAll("_", " ").toLowerCase(); return s[0].toUpperCase() + s.slice(1); };
  $("str-rows").replaceChildren(...(st.changes.length ? st.changes.map((c) => {
    const d = c.after - c.before, cls = d > 0 ? "up" : d < 0 ? "down" : "";
    return h("tr", {}, h("td", {}, pretty(c.exercise)),
      h("td", { class: `r ${cls}` }, h("span", {}, `${c.before} → ${c.after} ${c.unit} ${d > 0 ? "↑" : d < 0 ? "↓" : "="}`)));
  }) : [h("tr", {}, h("td", {}, "Not enough exercise data yet."))]));

  // week row
  const past = r.week.filter((c) => !c.future);
  const hard = past.filter((c) => c.effort === "hard").length, rest = past.filter((c) => c.effort === "rest").length;
  $("week-sum").textContent = `${current ? "This week" : "That week"} · ${hard} hard, ${past.length - hard - rest} easier, ${rest} rest`;
  const pairs = [];
  for (let d = 0; d < 6; d++) if (r.week[d].effort === "hard" && r.week[d + 1].effort === "hard") {
    const usual = r.usual_pairs.some(([a, b]) => a === d && b === d + 1), name = `${DAYS[d]} → ${DAYS[d + 1]}`;
    pairs.push(usual ? `${name} is your usual hard pair · ${r.gauge === "strained" ? "recovery is lagging" : "recovery handled it"}`
      : `${name}: two hard days in a row`);
  }
  $("pair").hidden = !pairs.length;
  $("pair").textContent = pairs.join(" / ");
  const t = iso(today());
  $("days").replaceChildren(...r.week.map((c, i) => {
    const kind = (s) => (s.sport.includes("running") ? "run" : /strength|hiit/.test(s.sport) ? "strength" : "other");
    const blocks = c.future ? [h("div", { class: "blk future" })]
      : c.sessions.length ? c.sessions.map((s) => h("div", { class: `blk ${kind(s)}` }, h("span", {}, s.label)))
      : [h("div", { class: "blk rest" }, h("span", {}, "Rest"))];
    const lvl = c.future ? 0 : RANK[c.effort] || 0;
    const label = c.future ? "" : c.effort === "rest" ? "Rest" : c.effort[0].toUpperCase() + c.effort.slice(1) + (c.sessions.length > 1 ? ` · ${c.sessions.length} sessions` : "");
    return h("li", { class: `day${c.future ? " future" : ""}${c.day === t ? " today" : ""}` },
      h("span", { class: "d" }, DAYS[i]), h("span", { class: "dt" }, short(parse(c.day))),
      h("div", { class: "blocks" }, ...blocks),
      h("div", { class: "eff", "aria-hidden": "true" }, ...[1, 2, 3].map((k) => h("i", { class: k <= lvl ? "on" : "" }))),
      h("span", { class: "lv" }, label));
  }));

  // claude's take
  $("take-text").textContent = review ? review.text : "No review for this week yet. Press Review to write one.";
  $("take-meta").textContent = review ? `Written ${when(review.created_at)}${review.source === "template" ? " · template (Claude was unavailable)" : ""}` : "";
}

async function loadPast(openId) {
  const res = await fetch("/api/reviews");
  if (!res.ok) return;
  const list = await res.json();
  $("past").hidden = !list.length;
  $("past-list").replaceChildren(...list.map((rv) => {
    const det = h("details", {}, h("summary", {}, `${short(parse(rv.start))} – ${short(parse(rv.end))} · written ${when(rv.created_at)}${rv.source === "template" ? " · template" : ""}`),
      h("p", {}, rv.text));
    if (rv.id === openId) det.open = true;
    return det;
  }));
}

// review panel
$("review-btn").addEventListener("click", () => {
  const p = $("review-panel"), open = p.hidden;
  p.hidden = !open;
  $("review-btn").setAttribute("aria-expanded", String(open));
});
const tday = iso(today());
$("from").value = iso(addDays(today(), -27)); $("to").value = tday; $("from").max = $("to").max = tday;

let polling = false;
$("review-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (polling) return;
  const status = $("review-status"), range = new FormData(e.target).get("range");
  let start, end;
  if (range === "week") { start = iso(weekStart); const s = addDays(weekStart, 6); end = s > today() ? tday : iso(s); }
  else if (range === "4w") { start = iso(addDays(today(), -27)); end = tday; }
  else { start = $("from").value; end = $("to").value; }
  const res = await fetch("/api/review", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ start, end }) });
  if (res.status === 409) { status.textContent = "A review is already being written."; return; }
  if (!res.ok) { status.textContent = (await res.json()).error || "That range didn't work."; return; }
  const { job_id } = await res.json();
  polling = true;
  status.textContent = "Writing your review…";
  let misses = 0;
  const tick = async () => {
    let j;
    try { j = await (await fetch(`/api/review/${job_id}`)).json(); }
    catch { if (++misses < 20) return setTimeout(tick, 3000); j = { status: "done", review: null }; }
    if (j.status === "running") return setTimeout(tick, 3000);
    polling = false;
    if (!j.review) { status.textContent = "That review was interrupted. Press Write it to try again."; return; }
    status.textContent = j.review.kind === "week" ? "Done. It's in Claude's take below." : "Done. It's under Past reviews.";
    if (j.review.kind === "week") await load(); else await loadPast(j.review.id);
  };
  setTimeout(tick, 3000);
});

$("prev").addEventListener("click", () => { weekStart = addDays(weekStart, -7); load(); });
$("next").addEventListener("click", () => { weekStart = addDays(weekStart, 7); load(); });
const qs = new URLSearchParams(location.search).get("end");
if (qs && /^\d{4}-\d{2}-\d{2}$/.test(qs)) weekStart = monday(parse(qs));
load();
loadPast();
