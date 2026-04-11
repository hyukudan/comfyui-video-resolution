import { app } from "/scripts/app.js";

const CUSTOM_ONLY_WIDGETS = ["custom_mode", "custom_width", "custom_height"];

function findWidget(node, name) {
  return node.widgets?.find((widget) => widget.name === name);
}

function setWidgetDisabled(widget, disabled) {
  if (!widget) {
    return;
  }

  widget.disabled = disabled;

  if (widget.inputEl) {
    widget.inputEl.disabled = disabled;
  }

  if (widget.element) {
    widget.element.disabled = disabled;
    widget.element.style.opacity = disabled ? "0.55" : "";
    widget.element.style.pointerEvents = disabled ? "none" : "";
  }
}

function updateCustomWidgets(node) {
  const resolutionWidget = findWidget(node, "resolution");
  const isCustomResolution = resolutionWidget?.value === "Custom";

  for (const widgetName of CUSTOM_ONLY_WIDGETS) {
    setWidgetDisabled(findWidget(node, widgetName), !isCustomResolution);
  }

  node.setDirtyCanvas(true, true);
}

app.registerExtension({
  name: "comfyui-video-resolution.ui",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "VideoResolutionNode") {
      return;
    }

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const result = onNodeCreated?.apply(this, arguments);

      const resolutionWidget = findWidget(this, "resolution");
      if (resolutionWidget) {
        const originalCallback = resolutionWidget.callback;
        resolutionWidget.callback = (...args) => {
          const callbackResult = originalCallback?.apply(resolutionWidget, args);
          updateCustomWidgets(this);
          return callbackResult;
        };
      }

      updateCustomWidgets(this);
      return result;
    };

    const onConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function () {
      const result = onConfigure?.apply(this, arguments);
      queueMicrotask(() => updateCustomWidgets(this));
      return result;
    };
  },
});
