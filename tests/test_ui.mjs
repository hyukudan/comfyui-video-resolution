import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import test from "node:test";
import vm from "node:vm";

const schema = JSON.parse(execFileSync(process.env.PYTHON ?? "python", ["-c",
  "import json; from video_resolution_node import VideoResolutionNode; print(json.dumps(VideoResolutionNode.INPUT_TYPES()))"],
  { cwd: fileURLToPath(new URL("..", import.meta.url)), encoding: "utf8" }));
const inputs = { ...schema.required, ...schema.optional };
const source = readFileSync(new URL("../web/video_resolution_ui.js", import.meta.url), "utf8")
  .replace(/^import .*;$/gm, "");

async function setup(fetchApi = async () => ({ ok: true, json: async () =>
  ({ width: 1280, height: 704, megapixels: .90112, multiple: 64, add_one: false }) })) {
  let extension;
  let timerId = 0;
  const timers = new Map();
  const requests = [];
  const app = { registerExtension(value) { extension = value; } };
  const api = { fetchApi(path, options) { requests.push({ path, ...options }); return fetchApi(path, options); } };
  const document = { createElement: () => ({ style: {}, children: [], textContent: "",
    setAttribute() {}, append(...children) { this.children.push(...children); } }) };
  vm.runInNewContext(source, { app, api, document, queueMicrotask, AbortController,
    setTimeout(fn) { timers.set(++timerId, fn); return timerId; }, clearTimeout(id) { timers.delete(id); } });
  class Node {
    constructor() {
      this.inputs = [];
      this.size = [280, 480];
      this.widgets = Object.entries(inputs).map(([name, definition]) => ({ name, value: definition[1].default,
        type: Array.isArray(definition[0]) ? "combo" : definition[0].toLowerCase(),
        options: {}, inputEl: {}, element: { style: {} } }));
    }
    setDirtyCanvas() {}
    computeSize() { return [280, 80 + this.widgets.filter(w => !w.hidden).reduce((height, w) => height + (w.computeSize?.(280)[1] ?? 20) + 4, 0)]; }
    setSize(size) { this.size = size; }
    addDOMWidget(name, type, element, options) {
      const widget = { name, type, element, options }; this.widgets.push(widget); return widget;
    }
  }
  await extension.beforeRegisterNodeDef(Node, { name: "VideoResolutionNode", input: schema });
  const node = new Node();
  const widget = name => node.widgets.find(w => w.name === name);
  const change = (name, value) => { widget(name).value = value; widget(name).callback(); };
  const flush = async () => { await new Promise(queueMicrotask); const pending = [...timers.values()]; timers.clear(); await Promise.all(pending.map(fn => fn())); };
  node.onNodeCreated();
  return { node, widget, change, flush, timers, requests,
    size: widget("resolution_preview").element.children[0], detail: widget("resolution_preview").element.children[1] };
}

test("custom controls and effective profile rules survive callbacks and workflow restore", async () => {
  const { node, widget, change, flush, size, detail } = await setup();
  assert.equal(widget("custom_width").disabled, true);
  assert.equal(widget("custom_megapixels").disabled, true);
  assert.equal(widget("divisible_by").disabled, true);
  change("resolution", "Custom");
  assert.equal(widget("aspect_ratio").disabled, true);
  assert.equal(widget("custom_width").disabled, false);
  change("custom_mode", "from_width");
  assert.equal(widget("aspect_ratio").disabled, false);
  assert.equal(widget("custom_height").disabled, true);
  change("custom_mode", "from_height");
  assert.equal(widget("custom_width").disabled, true);
  assert.equal(widget("custom_height").disabled, false);
  change("model_profile", "Custom");
  assert.equal(widget("add_one").disabled, false);
  change("resolution", "Custom MP");
  assert.equal(widget("custom_megapixels").disabled, false);
  widget("resolution").value = "720p";
  node.onConfigure();
  await flush();
  assert.equal(widget("custom_height").inputEl.disabled, true);
  assert.equal(widget("custom_megapixels").disabled, true);
  assert.equal(size.textContent, "1280 × 704");
  assert.equal(detail.textContent, "0.901 MP · multiple of 64");
});

test("only relevant rows appear and the node resizes without changing width or stored values", async () => {
  const { node, widget, change, flush } = await setup();
  const visible = () => node.widgets.filter(w => !w.hidden).map(w => w.name);
  const common = ["resolution", "aspect_ratio", "scale", "model_profile", "rounding_mode", "swap", "resolution_preview"];
  assert.deepEqual(visible(), common);
  const presetHeight = node.size[1];
  node.size[1] = 480;
  node.onConfigure();
  await flush();
  assert.equal(node.size[1], presetHeight);
  node.size[0] = 360;
  change("resolution", "Custom");
  assert.deepEqual(visible(), ["resolution", "scale", "model_profile", "custom_mode", "custom_width", "custom_height", "rounding_mode", "swap", "resolution_preview"]);
  assert.ok(node.size[1] > presetHeight);
  change("custom_width", 1536);
  change("custom_height", 864);
  change("custom_mode", "from_width");
  assert.equal(widget("aspect_ratio").hidden, false);
  assert.equal(widget("custom_height").hidden, true);
  change("custom_mode", "from_height");
  assert.equal(widget("custom_width").hidden, true);
  assert.equal(widget("custom_height").hidden, false);
  change("resolution", "Custom MP");
  assert.deepEqual(visible(), [...common.slice(0, -1), "custom_megapixels", "resolution_preview"]);
  change("custom_megapixels", .4);
  change("model_profile", "Custom");
  assert.equal(widget("divisible_by").hidden, false);
  assert.equal(widget("add_one").hidden, false);
  change("model_profile", "MiniMax H3");
  change("resolution", "720p");
  assert.deepEqual(visible(), common);
  assert.deepEqual(Array.from(node.size), [360, presetHeight]);
  assert.equal(widget("custom_width").value, 1536);
  assert.equal(widget("custom_height").value, 864);
  assert.equal(widget("custom_megapixels").value, .4);
  node.size[1] += 90;
  change("scale", "0.5x");
  assert.equal(node.size[1], presetHeight + 90);
  widget("resolution").value = "Custom MP";
  node.onConfigure();
  await flush();
  assert.equal(widget("custom_megapixels").hidden, false);
  assert.equal(widget("custom_megapixels").options.hidden, false);
  assert.equal(node.size[1], presetHeight + 24);
  assert.equal(node.size[0], 360);
});

test("connected selectors reveal dependent controls and unused connected rows stay accessible", async () => {
  const { node, widget, change, flush } = await setup();
  node.inputs = [{ name: "resolution", link: 0 }, { name: "custom_mode", link: 1 }, { name: "model_profile", link: 2 }];
  node.onConnectionsChange();
  await flush();
  for (const name of Object.keys(inputs)) assert.equal(widget(name).hidden ?? false, false, name);
  node.inputs = [{ name: "custom_width", link: 0 }];
  node.onConnectionsChange();
  await flush();
  assert.equal(widget("custom_width").hidden, false);
  assert.equal(widget("custom_width").disabled, true);
  assert.equal(widget("custom_height").hidden, true);
  node.inputs = [{ name: "custom_mode", link: 0 }];
  change("resolution", "Custom");
  assert.equal(widget("aspect_ratio").hidden, false);
  assert.equal(widget("custom_width").hidden, false);
  assert.equal(widget("custom_height").hidden, false);
});

test("visibility leaves widget types, sizing, serialization and converted inputs intact", async () => {
  const { node, widget, change, flush } = await setup();
  const width = widget("custom_width");
  const computeSize = () => [0, -4];
  const serializeValue = () => 1536;
  Object.assign(width, { type: "converted-widget", hidden: true, computeSize, serializeValue });
  const original = node.widgets.map(w => [w, w.type, w.value, w.computeSize, w.serializeValue]);
  change("resolution", "Custom");
  change("resolution", "720p");
  node.onConfigure();
  await flush();
  assert.equal(width.hidden, true);
  original.forEach(([w, type, value, compute, serialize], index) => {
    assert.equal(node.widgets[index], w);
    assert.equal(w.type, type);
    assert.equal(w.value, value);
    assert.equal(w.computeSize, compute);
    assert.equal(w.serializeValue, serialize);
  });
});

test("preview sends current values to Python without serializing the panel", async () => {
  const { node, widget, change, flush, requests } = await setup();
  change("resolution", "Custom MP");
  change("custom_megapixels", .4);
  change("rounding_mode", "nearest");
  await flush();
  assert.equal(requests.length, 1);
  assert.equal(requests[0].path, "/video_resolution/preview");
  assert.equal(JSON.parse(requests[0].body).custom_megapixels, .4);
  const preview = widget("resolution_preview");
  assert.equal(preview.serialize, false);
  assert.equal(preview.options.serialize, false);
  assert.equal(preview.serializeValue(), undefined);
  assert.deepEqual(node.widgets.filter(w => w.serialize !== false).map(w => w.name), Object.keys(inputs));
  assert.equal(node.widgets[11].name, "custom_megapixels");
});

test("connected values clear the preview instead of reporting local widget values", async () => {
  const { node, flush, requests, size, detail } = await setup();
  await flush();
  node.inputs = [{ name: "scale", link: 0 }];
  node.onConnectionsChange();
  await flush();
  assert.equal(requests.length, 1);
  assert.equal(size.textContent, "Connected inputs");
  assert.match(detail.textContent, /during execution/);
  node.inputs[0].link = null;
  node.onConnectionsChange();
  await flush();
  assert.equal(requests.length, 2);
  assert.equal(size.textContent, "1280 × 704");
});

test("stale asynchronous results cannot overwrite newer settings", async () => {
  let deliver;
  const { change, flush, size, requests } = await setup(() => new Promise(resolve => { deliver = resolve; }));
  const pending = flush();
  await new Promise(queueMicrotask);
  change("resolution", "Custom MP");
  assert.equal(requests[0].signal.aborted, true);
  deliver({ ok: true, json: async () => ({ width: 1, height: 1, megapixels: 1, multiple: 1 }) });
  await pending;
  assert.equal(size.textContent, "Calculating…");
});

test("removing a node cancels pending timers and active requests", async () => {
  const { node, timers, requests, flush } = await setup();
  node.onRemoved();
  await flush();
  assert.equal(timers.size, 0);
  assert.equal(requests.length, 0);
  let deliver;
  const active = await setup(() => new Promise(resolve => { deliver = resolve; }));
  const pending = active.flush();
  await new Promise(queueMicrotask);
  active.node.onRemoved();
  assert.equal(active.requests[0].signal.aborted, true);
  deliver({ ok: true, json: async () => ({}) });
  await pending;
});

test("missing backend route asks for restart and does not keep a stale size", async () => {
  const { flush, size, detail } = await setup(async () => ({ ok: false, status: 404 }));
  await flush();
  assert.equal(size.textContent, "Preview unavailable");
  assert.match(detail.textContent, /Restart ComfyUI/);
});

test("legacy add_one is explicitly labelled as an offset from the grid", async () => {
  const { flush, detail } = await setup(async () => ({ ok: true, json: async () =>
    ({ width: 1281, height: 705, megapixels: .903105, multiple: 32, add_one: true }) }));
  await flush();
  assert.equal(detail.textContent, "0.903 MP · grid 32 + 1 (legacy)");
});
