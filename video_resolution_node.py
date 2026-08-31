import math


class VideoResolutionNode:
    """
    Simple video resolution node that outputs width and height.
    Designed for video generation models like LTX, CogVideo, Hunyuan, etc.
    """

    RESOLUTIONS = {
        "480p": 480,
        "720p": 720,
        "1080p": 1080,
        "1440p (2K)": 1440,
        "2160p (4K)": 2160,
        "4320p (8K)": 4320,
        "Custom": 0,
        "540p": 540,
        "768p": 768,
        "H3 Native (768p)": 768,
        "0.3 MP": 0,
        "0.5 MP": 0,
        "0.7 MP": 0,
        "1.0 MP": 0,
        "Custom MP": 0,
    }

    MEGAPIXELS = {"0.3 MP": 0.3, "0.5 MP": 0.5, "0.7 MP": 0.7, "1.0 MP": 1.0}

    ASPECT_RATIOS = {
        "1:1 (Square)": (1, 1),
        "16:9 (Widescreen)": (16, 9),
        "19:9 (Cinematic Mobile)": (19, 9),
        "2.39:1 (CinemaScope)": (239, 100),
        "9:16 (Vertical)": (9, 16),
        "4:3 (Classic)": (4, 3),
        "5:4 (Classic Photo)": (5, 4),
        "3:4 (Portrait)": (3, 4),
        "4:5 (Social Portrait)": (4, 5),
        "21:9 (Ultrawide)": (21, 9),
        "9:21 (Tall)": (9, 21),
        "3:2 (Photo)": (3, 2),
        "2:3 (Photo Portrait)": (2, 3),
    }

    SCALE_FACTORS = {
        "0.25x": 0.25,
        "0.5x": 0.5,
        "0.75x": 0.75,
        "1x": 1.0,
        "1.25x": 1.25,
        "1.5x": 1.5,
        "2x": 2.0,
    }

    CUSTOM_MODES = [
        "manual",
        "from_width",
        "from_height",
    ]

    ROUNDING_MODES = [
        "floor",
        "nearest",
        "ceil",
    ]

    MODEL_PROFILES = {
        "Custom": {"divisible_by": None, "add_one": None},
        # ComfyUI-LTXVideo workflows in this repo expect exact multiples of 64.
        # Using add_one here creates a mismatch because LTX latent creation uses
        # integer division by 32 and silently drops the extra pixel.
        "LTX Video / LTX2": {"divisible_by": 64, "add_one": False},
        "CogVideoX": {"divisible_by": 16, "add_one": False},
        "Hunyuan Video": {"divisible_by": 16, "add_one": False},
        "Mochi": {"divisible_by": 64, "add_one": False},
        "Wan 2.x": {"divisible_by": 16, "add_one": False},
        "MiniMax H3": {"divisible_by": 32, "add_one": False},
        "Wan 2.2 TI2V 5B": {"divisible_by": 32, "add_one": False},
        "Hunyuan Video 1.5": {"divisible_by": 16, "add_one": False},
        "LTX 2.3": {"divisible_by": 64, "add_one": False},
    }

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "resolution": (list(cls.RESOLUTIONS.keys()), {"default": "720p", "tooltip": "p presets use the short edge. MP presets use 1 MP = 1,000,000 pixels. H3 Native uses a 768 short edge and 1344x768 area cap before alignment."}),
                "aspect_ratio": (list(cls.ASPECT_RATIOS.keys()), {"default": "16:9 (Widescreen)"}),
                "scale": (list(cls.SCALE_FACTORS.keys()), {"default": "1x"}),
                "model_profile": (list(cls.MODEL_PROFILES.keys()), {"default": "LTX Video / LTX2", "tooltip": "Select MiniMax H3 for 32-pixel alignment. Wan 2.2 TI2V 5B needs 32; Wan 2.x retains 16 for the other variants. Profiles override divisible_by and add_one."}),
                "custom_mode": (cls.CUSTOM_MODES, {"default": "manual"}),
                "custom_width": ("INT", {"default": 1280, "min": 64, "max": 16384, "step": 8}),
                "custom_height": ("INT", {"default": 720, "min": 64, "max": 16384, "step": 8}),
                "divisible_by": ([8, 16, 32, 64], {"default": 32}),
                "rounding_mode": (cls.ROUNDING_MODES, {"default": "floor"}),
                "add_one": ("BOOLEAN", {"default": True}),
                "swap": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "custom_megapixels": ("FLOAT", {"default": 0.5, "min": 0.01, "max": 16.0, "step": 0.01,
                    "tooltip": "Used only with Custom MP. 1 MP = 1,000,000 pixels before scale and alignment; not a VRAM limit."}),
            }
        }

    RETURN_TYPES = ("INT", "INT", "STRING")
    RETURN_NAMES = ("width", "height", "resolution_str")
    OUTPUT_TOOLTIPS = (
        "Width in pixels",
        "Height in pixels",
        "Resolution as string (e.g. 1344x768)",
    )
    FUNCTION = "get_resolution"
    CATEGORY = "video"

    DESCRIPTION = "Video resolution selector with presets, model profiles, and custom sizing modes."
    SEARCH_ALIASES = ["video size", "ltx resolution", "video dimensions", "cogvideo", "hunyuan", "ltx2", "h3", "minimax", "wan 2.2", "ltx 2.3", "megapixels"]

    @staticmethod
    def _quantize(value, divisible_by, rounding_mode):
        if rounding_mode == "nearest":
            return int(round(value / divisible_by) * divisible_by)
        if rounding_mode == "ceil":
            return math.ceil(value / divisible_by) * divisible_by
        return int((value // divisible_by) * divisible_by)

    def _get_preset_resolution(self, resolution, aspect_ratio, custom_megapixels=0.5):
        base_height = self.RESOLUTIONS[resolution]
        w_ratio, h_ratio = self.ASPECT_RATIOS[aspect_ratio]

        if resolution in self.MEGAPIXELS or resolution == "Custom MP":
            megapixels = self.MEGAPIXELS.get(resolution, custom_megapixels)
            if not isinstance(megapixels, (int, float)) or isinstance(megapixels, bool) or not math.isfinite(megapixels) or not 0.01 <= megapixels <= 16:
                raise ValueError("Custom MP must be a finite number between 0.01 and 16.")
            height = math.sqrt(megapixels * 1_000_000 * h_ratio / w_ratio)
            return height * w_ratio / h_ratio, height

        if resolution == "H3 Native (768p)":
            width, height = base_height * w_ratio / min(w_ratio, h_ratio), base_height * h_ratio / min(w_ratio, h_ratio)
            factor = min(1.0, math.sqrt((1344 * 768) / (width * height)))
            return max(32, round(width * factor / 32) * 32), max(32, round(height * factor / 32) * 32)

        if w_ratio == h_ratio:
            return base_height, base_height

        if w_ratio > h_ratio:
            return round(base_height * w_ratio / h_ratio), base_height

        return base_height, round(base_height * h_ratio / w_ratio)

    def _get_custom_resolution(self, aspect_ratio, custom_mode, custom_width, custom_height):
        if custom_mode == "manual":
            return custom_width, custom_height

        w_ratio, h_ratio = self.ASPECT_RATIOS[aspect_ratio]

        if custom_mode == "from_width":
            return custom_width, round(custom_width * h_ratio / w_ratio)

        return round(custom_height * w_ratio / h_ratio), custom_height

    def _resolve_model_rules(self, model_profile, divisible_by, add_one):
        profile = self.MODEL_PROFILES[model_profile]
        resolved_divisible_by = profile["divisible_by"] if profile["divisible_by"] is not None else divisible_by
        resolved_add_one = profile["add_one"] if profile["add_one"] is not None else add_one
        return resolved_divisible_by, resolved_add_one

    def get_resolution(self, resolution, aspect_ratio, scale, model_profile, custom_mode, custom_width,
                       custom_height, divisible_by, rounding_mode, add_one, swap, custom_megapixels=0.5):

        scale_factor = self.SCALE_FACTORS[scale]
        divisible_by, add_one = self._resolve_model_rules(model_profile, divisible_by, add_one)

        if resolution == "Custom":
            width, height = self._get_custom_resolution(
                aspect_ratio, custom_mode, custom_width, custom_height
            )
        else:
            width, height = self._get_preset_resolution(resolution, aspect_ratio, custom_megapixels)

        # Apply scale
        width *= scale_factor
        height *= scale_factor
        # Preserve legacy preset/custom rounding; MP dimensions stay fractional
        # so floor/nearest/ceil operate on the requested pixel budget.
        if resolution not in self.MEGAPIXELS and resolution != "Custom MP":
            width, height = int(width), int(height)

        # Quantize dimensions to model requirements.
        width = self._quantize(width, divisible_by, rounding_mode)
        height = self._quantize(height, divisible_by, rounding_mode)

        # Ensure minimum size
        width = max(width, divisible_by)
        height = max(height, divisible_by)

        # Legacy custom sizing only; built-in model profiles never add a pixel.
        if add_one:
            width += 1
            height += 1

        # Swap if requested
        if swap:
            width, height = height, width

        resolution_str = f"{width}x{height}"

        return (width, height, resolution_str)


def preview_resolution(payload):
    """Validate local UI values, then use the node's execution calculation."""
    schema = VideoResolutionNode.INPUT_TYPES()
    inputs = {**schema["required"], **schema["optional"]}
    if not isinstance(payload, dict) or payload.keys() - inputs.keys():
        raise ValueError("Expected resolution inputs only.")
    values = {}
    for name, (kind, options) in inputs.items():
        value = payload.get(name, options["default"])
        if isinstance(kind, list):
            valid = value in kind
        elif kind == "BOOLEAN":
            valid = type(value) is bool
        else:
            valid = type(value) in ((int,) if kind == "INT" else (int, float))
            valid = valid and math.isfinite(value) and options["min"] <= value <= options["max"]
        if not valid:
            raise ValueError(f"Invalid {name}.")
        values[name] = value
    node = VideoResolutionNode()
    width, height, label = node.get_resolution(**values)
    multiple, add_one = node._resolve_model_rules(values["model_profile"], values["divisible_by"], values["add_one"])
    return {"width": width, "height": height, "resolution_str": label,
            "megapixels": width * height / 1_000_000, "multiple": multiple, "add_one": add_one}
