import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

const previews = new WeakMap();

function findWidget(node, name) {
  return node.widgets?.find((widget) => widget.name === name);
}

function isConnected(node, name) {
  return node.inputs?.some((input) => input.name === name && input.link != null);
}

function updateCustomWidgets(node, resize = false) {
  const resolution = findWidget(node, "resolution")?.value;
  const resolutionConnected = isConnected(node, "resolution");
  const isCustomResolution = resolutionConnected || resolution === "Custom";
  const mode = findWidget(node, "custom_mode")?.value;
  const modeConnected = isConnected(node, "custom_mode");
  const isCustomProfile = isConnected(node, "model_profile") || findWidget(node, "model_profile")?.value === "Custom";
  const visible = {
    aspect_ratio: resolutionConnected || resolution !== "Custom" || modeConnected || mode !== "manual",
    custom_mode: isCustomResolution,
    custom_width: isCustomResolution && (modeConnected || mode !== "from_height"),
    custom_height: isCustomResolution && (modeConnected || mode !== "from_width"),
    divisible_by: isCustomProfile,
    add_one: isCustomProfile,
    custom_megapixels: resolutionConnected || resolution === "Custom MP",
  };

  for (const [name, relevant] of Object.entries(visible)) {
    const widget = findWidget(node, name);
    if (!widget) continue;
    // Older frontends own the presentation of converted input widgets.
    if (widget.type?.startsWith("converted-widget")) continue;
    const hidden = !relevant && !isConnected(node, name);
    resize ||= widget.hidden !== hidden;
    widget.hidden = hidden;
    widget.options ??= {};
    widget.options.hidden = hidden;
    widget.disabled = !relevant;
    if (widget.inputEl) widget.inputEl.disabled = !relevant;
  }

  if (resize) node.setSize([node.size[0], node.computeSize()[1]]);
  node.setDirtyCanvas(true, true);
}

function schedulePreview(node, inputs) {
  const state = previews.get(node);
  if (!state) return;
  clearTimeout(state.timer);
  state.request?.abort();
  const revision = ++state.revision;
  if (node.inputs?.some((input) => Object.hasOwn(inputs, input.name) && input.link != null)) {
    state.size.textContent = "Connected inputs";
    state.detail.textContent = "Dimensions are resolved during execution.";
    return;
  }
  state.size.textContent = "Calculating…";
  state.detail.textContent = "Final size after scale and alignment";
  state.timer = setTimeout(async () => {
    const values = Object.fromEntries(Object.entries(inputs).map(([name, definition]) =>
      [name, findWidget(node, name)?.value ?? definition[1].default]));
    const request = new AbortController();
    state.request = request;
    try {
      const response = await api.fetchApi("/video_resolution/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
        signal: request.signal,
      });
      if (response.status === 404) throw new Error("Restart ComfyUI and refresh the browser.");
      if (!response.ok) throw new Error("Check the resolution settings.");
      const result = await response.json();
      if (previews.get(node) !== state || state.revision !== revision) return;
      state.size.textContent = `${result.width} × ${result.height}`;
      const alignment = result.add_one ? `grid ${result.multiple} + 1 (legacy)` : `multiple of ${result.multiple}`;
      state.detail.textContent = `${result.megapixels.toFixed(3)} MP · ${alignment}`;
    } catch (error) {
      if (request.signal.aborted || previews.get(node) !== state || state.revision !== revision) return;
      state.size.textContent = "Preview unavailable";
      state.detail.textContent = error.message || "Could not reach ComfyUI.";
    }
  }, 150);
}

function addPreview(node) {
  const root = document.createElement("div");
  root.style.cssText = "box-sizing:border-box;padding:8px 12px;border-radius:6px;background:var(--comfy-input-bg,#222);color:var(--input-text,#ddd);font:12px sans-serif;display:flex;flex-direction:column;justify-content:center;gap:4px;overflow:hidden;";
  root.setAttribute("role", "status");
  root.setAttribute("aria-live", "polite");
  const size = document.createElement("strong");
  size.style.fontSize = "16px";
  const detail = document.createElement("span");
  detail.style.cssText = "opacity:0.8;overflow-wrap:anywhere;";
  root.append(size, detail);
  const widget = node.addDOMWidget("resolution_preview", "videoResolutionPreview", root, {
    serialize: false, hideOnZoom: false,
    getMinHeight: () => 66, getMaxHeight: () => 66,
  });
  widget.serialize = false;
  widget.serializeValue = () => undefined;
  widget.computeSize = (width) => [width, 66];
  previews.set(node, { size, detail, revision: 0 });
}

app.registerExtension({
  name: "comfyui-video-resolution.ui",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "VideoResolutionNode") {
      return;
    }
    const inputs = { ...nodeData.input.required, ...nodeData.input.optional };
    const update = (node, resize = false) => {
      updateCustomWidgets(node, resize);
      schedulePreview(node, inputs);
    };

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const result = onNodeCreated?.apply(this, arguments);

      addPreview(this);
      for (const name of Object.keys(inputs)) {
        const widget = findWidget(this, name);
        if (!widget) continue;
        const originalCallback = widget.callback;
        widget.callback = (...args) => {
          const callbackResult = originalCallback?.apply(widget, args);
          update(this);
          return callbackResult;
        };
      }

      update(this);
      return result;
    };

    const onConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function () {
      const result = onConfigure?.apply(this, arguments);
      queueMicrotask(() => update(this, true));
      return result;
    };

    const onConnectionsChange = nodeType.prototype.onConnectionsChange;
    nodeType.prototype.onConnectionsChange = function () {
      const result = onConnectionsChange?.apply(this, arguments);
      queueMicrotask(() => update(this));
      return result;
    };

    const onRemoved = nodeType.prototype.onRemoved;
    nodeType.prototype.onRemoved = function () {
      const state = previews.get(this);
      if (state) {
        clearTimeout(state.timer);
        state.request?.abort();
        previews.delete(this);
      }
      return onRemoved?.apply(this, arguments);
    };
  },
});
