/* ArcheoConverter minimal UI.
 *
 * Single-page application that talks exclusively to the JSON API
 * ( /api/v1/* ). No build step, no external dependencies: plain fetch +
 * SVG for graph rendering, so it works on an offline server.
 */
"use strict";

const API = "/api/v1";

// ---------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

async function api(path, options = {}) {
  const opts = { headers: {}, ...options };
  if (opts.body && !(opts.body instanceof FormData)) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(opts.body);
  }
  const res = await fetch(API + path, opts);
  const contentType = res.headers.get("content-type") || "";
  const data = contentType.includes("json") ? await res.json() : await res.text();
  if (!res.ok) {
    const message = data && data.detail ? data.detail : `HTTP ${res.status}`;
    const details = data && data.details ? ` (${data.details.join("; ")})` : "";
    throw new Error(message + details);
  }
  return data;
}

function show(el, text, isError) {
  el.classList.remove("hidden");
  el.textContent = text || "";
  el.classList.toggle("error", !!isError);
}
function hide(el) { el.classList.add("hidden"); }
function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}
function fmtDate(iso) {
  try { return new Date(iso).toLocaleString(); } catch { return iso; }
}
function csvToList(input) {
  return (input || "").split(",").map((s) => s.trim()).filter(Boolean);
}

// ---------------------------------------------------------------------
// Tabs
// ---------------------------------------------------------------------
$$("nav#tabs button").forEach((btn) => {
  btn.addEventListener("click", () => {
    $$("nav#tabs button").forEach((b) => b.classList.remove("active"));
    $$(".tab").forEach((t) => t.classList.remove("active"));
    btn.classList.add("active");
    $(`#tab-${btn.dataset.tab}`).classList.add("active");
    if (btn.dataset.tab === "models") refreshModels();
    if (btn.dataset.tab === "explorer") refreshExplorerModelSelect();
    if (btn.dataset.tab === "convert") refreshConvertSelects();
    if (btn.dataset.tab === "compare") refreshCompareSelects();
    if (btn.dataset.tab === "export") refreshExportSelects();
  });
});

// ---------------------------------------------------------------------
// Meta
// ---------------------------------------------------------------------
let META = null;

async function loadMeta() {
  META = await api("/meta");
  $("#app-version").textContent =
    `v${META.version} · ${META.formalisms.length} formalism(s) · ${META.conversions.length} conversion(s)`;
  const formalismSelect = $("#import-formalism");
  META.formalisms.forEach((f) => {
    const opt = document.createElement("option");
    opt.value = f.formalism;
    opt.textContent = `${f.formalism} ${f.version}`;
    formalismSelect.appendChild(opt);
  });
  refreshConvertSelects();
}

// ---------------------------------------------------------------------
// Models tab
// ---------------------------------------------------------------------
async function refreshModels() {
  const models = await api("/models");
  const tbody = $("#models-table tbody");
  tbody.innerHTML = "";
  models.forEach((m) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${esc(m.name)}</td>
      <td class="muted">${esc(m.model_id)}</td>
      <td>${esc(m.formalism)}</td>
      <td>${esc(m.version || "-")}</td>
      <td>${m.element_count}</td>
      <td>${m.relationship_count}</td>
      <td>${m.folder_count}</td>
      <td class="muted">${fmtDate(m.imported_at)}</td>
      <td>
        <button class="small secondary" data-open="${esc(m.model_id)}">open</button>
        <button class="small secondary" data-del="${esc(m.model_id)}" data-name="${esc(m.name)}">delete</button>
      </td>`;
    tbody.appendChild(tr);
  });
  $$("#models-table [data-del]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm(`Delete model "${btn.dataset.name}"?`)) return;
      try {
        await api(`/models/${btn.dataset.del}`, { method: "DELETE" });
        refreshModels();
      } catch (e) { show($("#import-result"), e.message, true); }
    });
  });
  $$("#models-table [data-open]").forEach((btn) => {
    btn.addEventListener("click", () => {
      $("#ex-model").value = btn.dataset.open;
      document.querySelector('nav#tabs button[data-tab="explorer"]').click();
      runSearch();
      loadFolders();
    });
  });
  refreshExplorerModelSelect();
}

$("#import-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = $("#import-file").files[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  const name = $("#import-name").value.trim();
  const formalism = $("#import-formalism").value;
  const version = $("#import-version").value;
  if (name) form.append("name", name);
  if (formalism) form.append("formalism", formalism);
  if (version) form.append("version", version);
  if ($("#import-overwrite").checked) form.append("overwrite", "true");
  try {
    const result = await api("/models", { method: "POST", body: form });
    const warnings = result.warnings.length ? `\n\nWarnings:\n- ${result.warnings.join("\n- ")}` : "";
    show($("#import-result"),
      `Imported "${result.name}" (${result.formalism} ${result.version})\n` +
      `model_id: ${result.model_id}\n` +
      `${result.element_count} elements, ${result.relationship_count} relationships, ` +
      `${result.folder_count} folders.${warnings}`);
    refreshModels();
  } catch (e) { show($("#import-result"), e.message, true); }
});

// ---------------------------------------------------------------------
// Explorer tab
// ---------------------------------------------------------------------
async function refreshExplorerModelSelect() {
  const select = $("#ex-model");
  const current = select.value;
  select.innerHTML = "";
  const models = await api("/models");
  models.forEach((m) => {
    const opt = document.createElement("option");
    opt.value = m.model_id;
    opt.textContent = `${m.name} [${m.formalism} ${m.version}]`;
    select.appendChild(opt);
  });
  if (current && models.some((m) => m.model_id === current)) select.value = current;
}

$("#ex-model").addEventListener("change", () => { runSearch(); loadFolders(); loadGraphFolders(); });

async function runSearch() {
  const modelId = $("#ex-model").value;
  if (!modelId) return;
  const params = new URLSearchParams();
  const q = $("#ex-q").value.trim();
  if (q) params.set("q", q);
  const types = csvToList($("#ex-type").value);
  types.forEach((t) => params.append("types", t));
  const stereos = csvToList($("#ex-stereo").value);
  stereos.forEach((s) => params.append("stereotypes", s));
  params.set("limit", "200");
  try {
    const page = await api(`/models/${modelId}/elements?${params}`);
    $("#ex-count").textContent = `${page.total} match(es)`;
    $("#ex-results-count").textContent = `(${page.items.length} shown)`;
    const tbody = $("#ex-elements tbody");
    tbody.innerHTML = "";
    page.items.forEach((el) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${esc(el.name)}</td><td>${esc(el.type)}</td>
        <td>${el.stereotypes.map((s) => `<span class="tag">${esc(s)}</span>`).join("")}</td>`;
      tr.addEventListener("click", () => selectElement(modelId, el.id, tr));
      tbody.appendChild(tr);
    });
  } catch (e) { $("#ex-count").textContent = e.message; }
}
$("#ex-search").addEventListener("click", runSearch);
$("#ex-q").addEventListener("keydown", (e) => { if (e.key === "Enter") runSearch(); });
$("#ex-clear").addEventListener("click", () => {
  $("#ex-q").value = ""; $("#ex-type").value = ""; $("#ex-stereo").value = ""; runSearch();
});

async function selectElement(modelId, elementId, row) {
  $$("#ex-elements tbody tr").forEach((tr) => tr.classList.remove("selected"));
  if (row) row.classList.add("selected");
  try {
    const detail = await api(`/models/${modelId}/elements/${elementId}`);
    const el = detail.element;
    const lines = [
      `id:          ${el.id}`,
      `name:        ${el.name}`,
      `type:        ${el.type}`,
      `visibility:  ${el.visibility}`,
      `folder:      ${el.folder_id || "-"}`,
      `stereotypes: ${el.stereotypes.join(", ") || "-"}`,
      `description: ${el.description || "-"}`,
      ``,
      `outbound (${detail.outbound.length}):`,
      ...detail.outbound.map((r) => `  -${r.type}-> ${r.target}${r.aggregation ? " (aggregation)" : ""}`),
      `inbound (${detail.inbound.length}):`,
      ...detail.inbound.map((r) => `  <-${r.type}- ${r.source}`),
    ];
    const props = Object.entries(el.properties || {}).filter(([k]) => !k.startsWith("__"));
    if (props.length) {
      lines.push("", `properties:`);
      props.forEach(([k, v]) => lines.push(`  ${k} = ${JSON.stringify(v)}`));
    }
    $("#ex-detail-title").textContent = el.name;
    show($("#ex-detail"), lines.join("\n"));
  } catch (e) { show($("#ex-detail"), e.message, true); }
}

async function loadFolders() {
  const modelId = $("#ex-model").value;
  if (!modelId) return;
  try {
    const { tree } = await api(`/models/${modelId}/folders`);
    const container = $("#ex-folders");
    if (!tree.length) { container.textContent = "(no folders)"; return; }
    container.innerHTML = `<div class="folder-tree">${tree.map(renderFolder).join("")}</div>`;
    $$("#ex-folders [data-folder]").forEach((el) => {
      el.addEventListener("click", async () => {
        try {
          const detail = await api(`/models/${modelId}/folders/${el.dataset.folder}`);
          const lines = [
            `folder: ${detail.name} [${detail.kind}]`,
            `${detail.elements.length} elements, ${detail.relationships.length} relationships`,
            "",
            ...detail.elements.map((e) => `  - ${e.name} (${e.type})`),
          ];
          show($("#ex-detail"), lines.join("\n"));
          $("#ex-detail-title").textContent = `Folder: ${detail.name}`;
        } catch (e) { show($("#ex-detail"), e.message, true); }
      });
    });
  } catch (e) { $("#ex-folders").textContent = e.message; }
}
function renderFolder(folder) {
  const children = folder.children.map(renderFolder).join("");
  return `<div>
    <span class="fname" data-folder="${esc(folder.id)}" style="cursor:pointer">${esc(folder.name)}</span>
    <span class="fkind"> [${esc(folder.kind)}] (${folder.element_count})</span>
    ${children ? `<div>${children}</div>` : ""}
  </div>`;
}

// --- graph (circular SVG layout) -------------------------------------
async function loadGraphFolders() {
  const modelId = $("#ex-model").value;
  const select = $("#graph-folder");
  if (!modelId) { select.innerHTML = ""; return; }
  const { tree } = await api(`/models/${modelId}/folders`);
  const flat = [];
  (function walk(list, depth) {
    list.forEach((f) => {
      flat.push({ id: f.id, name: f.name, depth });
      walk(f.children, depth + 1);
    });
  })(tree, 0);
  select.innerHTML = flat.map((f) =>
    `<option value="${esc(f.id)}">${"&nbsp;".repeat(f.depth * 3) + esc(f.name)}</option>`).join("");
}

async function renderGraph() {
  const modelId = $("#ex-model").value;
  if (!modelId) return;
  const scope = $("#graph-scope").value;
  const params = new URLSearchParams();
  if (scope === "folder") params.set("folder", $("#graph-folder").value);
  else if (scope === "root") {
    params.set("from", $("#graph-root").value.trim());
    params.set("depth", $("#graph-depth").value || "2");
  }
  try {
    const graph = await api(`/models/${modelId}/graph?${params}`);
    drawGraph(graph);
    $("#graph-info").textContent =
      `${graph.nodes.length} nodes, ${graph.edges.length} edges` +
      (graph.truncated ? " (truncated by node limit)" : "");
  } catch (e) { $("#graph-info").textContent = e.message; }
}
$("#graph-render").addEventListener("click", renderGraph);
$("#graph-scope").addEventListener("change", () => {
  $("#graph-folder").disabled = $("#graph-scope").value !== "folder";
  $("#graph-root").disabled = $("#graph-scope").value !== "root";
  $("#graph-depth").disabled = $("#graph-scope").value !== "root";
});

const TYPE_COLORS = {
  "business-actor": "#f6bd6f", "business-role": "#f6d36f", "business-collaboration": "#e8b4b8",
  "business-service": "#82b366", "business-interaction": "#b8a1e3", "business-process": "#d19c83",
  "business-function": "#86c1b7", "business-event": "#e5989b", "business-communication-path": "#647687",
  "business-location": "#6d8086", "business-resource": "#839496", "business-object": "#f4f4bc",
  "application-component": "#7f9cf5", "application-collaboration": "#6a5acd", "application-service": "#5da5da",
  "application-interaction": "#a074c4", "application-process": "#c474a0", "application-function": "#74b0c4",
  "application-event": "#c47474", "application-protocol": "#7494c4", "security-service": "#e06c75",
  "system-software": "#98c379", "distribution-artifact": "#d19a66", "data-object": "#e5c07b",
  "artifact": "#7ec699", "node": "#61afef", "device": "#56b6c2", "communication-path": "#c678dd",
  "technology-collaboration": "#d16d9e", "technology-service": "#e59866", "technology-interaction": "#b180d7",
  "technology-process": "#d78080", "technology-function": "#80c7b1", "technology-event": "#d780d7",
  "technology-communication-path": "#80a0d7", "technology-resource": "#98971a", "technology-object": "#ab9b6e",
  "physical-device": "#75715e", "physical-node": "#5e81ac", "work-product": "#d08770", "gap": "#be5046",
  "improvement": "#a3be8c", "realization-state": "#b48ead", "driving-factor": "#ef795a",
  "stakeholder": "#e0af68", "driver": "#e06c75", "goal": "#98c379", "outcome": "#61afef",
  "requirement": "#e5c07b", "principle": "#d19a66", "assessment": "#c678dd", "means-of-realization": "#56b6c2",
  "extension": "#abb2bf", "resource": "#50c878",
};

function drawGraph(graph) {
  const container = $("#graph-canvas");
  const width = Math.max(container.clientWidth, 640);
  const height = 380;
  const cx = width / 2;
  const cy = height / 2;
  const radius = Math.min(cx, cy) - 60;
  const n = graph.nodes.length;
  const positions = {};
  graph.nodes.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / Math.max(n, 1) - Math.PI / 2;
    positions[node.id] = [cx + radius * Math.cos(angle), cy + radius * Math.sin(angle)];
  });
  let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">`;
  graph.edges.forEach((edge) => {
    const a = positions[edge.source];
    const b = positions[edge.target];
    if (!a || !b) return;
    svg += `<line x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}"
      ${edge.aggregation ? 'stroke-dasharray="4,3"' : ""} opacity="0.6">
      <title>${esc(edge.type)}</title></line>`;
  });
  graph.nodes.forEach((node) => {
    const [x, y] = positions[node.id];
    const color = TYPE_COLORS[node.type] || "#8298b0";
    const label = node.name.length > 22 ? node.name.slice(0, 21) + "…" : node.name;
    svg += `<g data-node="${esc(node.id)}">
      <circle cx="${x}" cy="${y}" r="9" fill="${color}"><title>${esc(node.name)} [${esc(node.type)}]</title></circle>
      <text x="${x + 12}" y="${y + 3}">${esc(label)}</text>
    </g>`;
  });
  svg += "</svg>";
  container.innerHTML = svg;
  $$("#graph-canvas [data-node]").forEach((g) => {
    g.addEventListener("click", () => selectElement($("#ex-model").value, g.dataset.node, null));
  });
}

// ---------------------------------------------------------------------
// Convert tab
// ---------------------------------------------------------------------
async function refreshConvertSelects() {
  if (!META) return;
  const models = await api("/models");
  const modelSelect = $("#conv-model");
  const current = modelSelect.value;
  modelSelect.innerHTML = models.map((m) =>
    `<option value="${esc(m.model_id)}">${esc(m.name)} [${esc(m.formalism)} ${esc(m.version || "?")}]</option>`).join("");
  if (current && models.some((m) => m.model_id === current)) modelSelect.value = current;

  const targetF = $("#conv-target-f");
  const targetV = $("#conv-target-v");
  const rules = META.conversions.filter((r) =>
    models.some((m) => m.model_id === (modelSelect.value || models[0] && models[0].model_id) &&
      r.source_formalism === m.formalism &&
      (!m.version || r.source_versions.includes(m.version))));
  targetF.innerHTML = "";
  const seen = new Set();
  rules.forEach((r) => {
    if (seen.has(r.target_formalism)) return;
    seen.add(r.target_formalism);
    const opt = document.createElement("option");
    opt.value = r.target_formalism;
    opt.textContent = r.target_formalism;
    targetF.appendChild(opt);
  });
  if (rules.length) targetF.value = rules[0].target_formalism;
  updateConvertVersions();
  const rulesBox = $("#conv-rules");
  rulesBox.innerHTML = rules.length
    ? "Available for the selected source:<div class='rules'>" +
      rules.map((r) => `<div><strong>${esc(r.id)}</strong>: ${esc(r.target_formalism)} ${r.target_versions.join("/")}</div>`).join("") +
      "</div>"
    : "(no conversion available for the selected model)";
  modelSelect.addEventListener("change", () => {
    refreshConvertSelects();
  }, { once: true });
}
function updateConvertVersions() {
  const rules = (META ? META.conversions : []).filter((r) => r.target_formalism === $("#conv-target-f").value);
  const versions = [...new Set(rules.flatMap((r) => r.target_versions))];
  const select = $("#conv-target-v");
  select.innerHTML = versions.map((v) => `<option>${esc(v)}</option>`).join("");
}
$("#conv-target-f").addEventListener("change", updateConvertVersions);

$("#convert-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const result = await api("/convert", {
      method: "POST",
      body: {
        model_id: $("#conv-model").value,
        target_formalism: $("#conv-target-f").value,
        target_version: $("#conv-target-v").value,
        dry_run: $("#conv-dry").checked,
      },
    });
    const report = result.report;
    let text = `rule: ${report.rule_id}\n` +
      `${report.source_formalism} ${report.source_version} -> ${report.target_formalism} ${report.target_version}\n` +
      `elements converted: ${report.elements_converted} (unmapped: ${report.elements_unmapped})\n` +
      `relationships converted: ${report.relationships_converted} (unmapped: ${report.relationships_unmapped})\n` +
      `folders: ${report.folders_converted} · duration: ${report.duration_ms} ms`;
    if (result.model_id) text += `\n\nnew model_id: ${result.model_id}`;
    else text += "\n\n(dry run: no model stored)";
    if (report.unmapped_elements.length) {
      text += `\n\nunmapped elements:\n- ${report.unmapped_elements
        .map((u) => `${u.name} [${u.type}] -> ${u.policy}`).join("\n- ")}`;
    }
    if (report.warnings.length) text += `\n\nwarnings:\n- ${report.warnings.join("\n- ")}`;
    show($("#convert-result"), text);
    refreshModels();
  } catch (e) { show($("#convert-result"), e.message, true); }
});

// ---------------------------------------------------------------------
// Compare tab
// ---------------------------------------------------------------------
async function refreshCompareSelects() {
  const models = await api("/models");
  for (const id of ["cmp-base", "cmp-other"]) {
    const select = $(`#${id}`);
    const current = select.value;
    select.innerHTML = models.map((m) =>
      `<option value="${esc(m.model_id)}">${esc(m.name)} [${esc(m.formalism)} ${esc(m.version || "?")}]</option>`).join("");
    if (current && models.some((m) => m.model_id === current)) select.value = current;
  }
}

async function runCompare() {
  try {
    const result = await api("/compare", {
      method: "POST",
      body: {
        base_id: $("#cmp-base").value,
        other_id: $("#cmp-other").value,
        match_by: $("#cmp-match").value,
      },
    });
    const totals = result.result.totals;
    const cards = [
      ["elements added", totals.elements_added],
      ["elements removed", totals.elements_removed],
      ["elements modified", totals.elements_modified],
      ["relations added", totals.relationships_added],
      ["relations removed", totals.relationships_removed],
      ["relations modified", totals.relationships_modified],
      ["folders added", totals.folders_added],
      ["folders removed", totals.folders_removed],
      ["folders modified", totals.folders_modified],
    ];
    const container = $("#cmp-summary");
    container.classList.remove("hidden");
    container.innerHTML = cards.map(([label, value]) =>
      `<div class="stat"><div class="value">${value}</div><div class="label">${label}</div></div>`).join("");
    renderComparison(result.result);
  } catch (e) { show($("#cmp-detail"), e.message, true); }
}
$("#cmp-run").addEventListener("click", runCompare);

function renderComparison(result) {
  const lines = [];
  lines.push(`comparison ${result.base_id} vs ${result.other_id} (match_by=${result.match_by})`, "");
  const section = (title, sec) => {
    if (!sec.added.length && !sec.removed.length && !sec.modified.length) return;
    lines.push(title);
    sec.added.forEach((r) => lines.push(`  + ${r.name} [${r.id}${r.type ? ", " + r.type : ""}]`));
    sec.removed.forEach((r) => lines.push(`  - ${r.name} [${r.id}${r.type ? ", " + r.type : ""}]`));
    sec.modified.forEach((m) => {
      const fields = Object.entries(m.changes).map(([f, c]) => {
        let old = JSON.stringify(c.old);
        let neo = JSON.stringify(c.new);
        if (old.length > 60) old = old.slice(0, 57) + "...";
        if (neo.length > 60) neo = neo.slice(0, 57) + "...";
        return `${f}: ${old} => ${neo}`;
      });
      lines.push(`  ~ ${m.name || m.base_id}: ${fields.join("; ")}`);
    });
    lines.push("");
  };
  section("elements:", result.elements);
  section("relationships:", result.relationships);
  section("folders:", result.folders);
  if (!lines.length) lines.push("(no differences found)");
  show($("#cmp-detail"), lines.join("\n"));
}

$("#plan-build").addEventListener("click", async () => {
  try {
    const result = await api("/compare/integration-plan", {
      method: "POST",
      body: {
        base_id: $("#cmp-base").value,
        source_id: $("#cmp-other").value,
        include_removals: $("#cmp-removals").checked,
      },
    });
    const plan = result.plan;
    const lines = [
      `integration plan ${result.report_id}`,
      `source -> base: ${plan.source_id} -> ${plan.base_id}`,
      `summary: ${JSON.stringify(plan.summary)}`,
      "",
      ...plan.operations.map((op) =>
        `  ${op.op} ${op.target_id} ${JSON.stringify(op.payload).slice(0, 120)}`),
    ];
    show($("#cmp-detail"), lines.join("\n"));
  } catch (e) { show($("#cmp-detail"), e.message, true); }
});

$("#plan-apply").addEventListener("click", async () => {
  if (!confirm("Apply the integration plan? The BASE model will be modified in memory.")) return;
  try {
    const result = await api("/compare/apply", {
      method: "POST",
      body: {
        base_id: $("#cmp-base").value,
        source_id: $("#cmp-other").value,
        include_removals: $("#cmp-removals").checked,
      },
    });
    const a = result.applied;
    show($("#cmp-detail"),
      `applied ${a.applied}/${a.operations_total} operations (skipped: ${a.skipped})\n` +
      `merged model now has: ${a.element_count} elements, ${a.relationship_count} relationships, ${a.folder_count} folders` +
      (a.warnings.length ? `\n\nwarnings:\n- ${a.warnings.join("\n- ")}` : ""));
    refreshModels();
    refreshExplorerModelSelect();
  } catch (e) { show($("#cmp-detail"), e.message, true); }
});

// ---------------------------------------------------------------------
// Export tab
// ---------------------------------------------------------------------
async function refreshExportSelects() {
  const models = (await api("/models")).filter((m) => m.formalism === "archimate");
  const select = $("#exp-model");
  const current = select.value;
  select.innerHTML = models.map((m) =>
    `<option value="${esc(m.model_id)}">${esc(m.name)} [archimate ${esc(m.version || "?")}]</option>`).join("");
  if (current && models.some((m) => m.model_id === current)) select.value = current;
}

function buildExportBody() {
  return {
    scope: $("#exp-scope").value,
    target_version: $("#exp-version").value || null,
    element_ids: csvToList($("#exp-elem-ids").value),
    relationship_ids: csvToList($("#exp-rel-ids").value),
    folder_ids: csvToList($("#exp-folder-ids").value),
    element_types: csvToList($("#exp-types").value),
    name_regex: $("#exp-regex").value.trim() || null,
    stereotypes: csvToList($("#exp-stereos").value),
  };
}

$("#export-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const modelId = $("#exp-model").value;
  if (!modelId) return;
  const body = buildExportBody();
  const res = await fetch(`${API}/models/${modelId}/export?format=xml`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).catch((e) => { show($("#export-result"), e.message, true); return null; });
  if (!res) return;
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    show($("#export-result"), data.detail || `HTTP ${res.status}`, true);
    return;
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${$("#exp-model").selectedOptions[0]?.text.replace(/\s+/g, "_") || modelId}.archimate`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
  const report = res.headers.get("X-Export-Report");
  show($("#export-result"), `Downloaded ${blob.size} bytes.\n${report ? JSON.stringify(JSON.parse(report), null, 2) : ""}`);
});

$("#export-json").addEventListener("click", async () => {
  const modelId = $("#exp-model").value;
  if (!modelId) return;
  try {
    const result = await fetch(`${API}/models/${modelId}/export?format=json`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildExportBody()),
    }).then(async (r) => {
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
      return data;
    });
    show($("#export-result"), `report: ${JSON.stringify(result.report, null, 2)}\n\n${result.xml}`);
  } catch (e) { show($("#export-result"), e.message, true); }
});

// ---------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------
loadMeta().catch((e) => {
  document.body.innerHTML = `<p class="error" style="padding:2rem">Unable to reach the API: ${esc(e.message)}</p>`;
});
refreshModels().catch(() => {});
