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
    }

    ASPECT_RATIOS = {
        "1:1 (Square)": (1, 1),
        "16:9 (Widescreen)": (16, 9),
        "9:16 (Vertical)": (9, 16),
        "4:3 (Classic)": (4, 3),
        "3:4 (Portrait)": (3, 4),
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

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "resolution": (list(cls.RESOLUTIONS.keys()), {"default": "720p"}),
                "aspect_ratio": (list(cls.ASPECT_RATIOS.keys()), {"default": "16:9 (Widescreen)"}),
                "scale": (list(cls.SCALE_FACTORS.keys()), {"default": "1x"}),
                "divisible_by": ([8, 16, 32, 64], {"default": 32}),
                "add_one": ("BOOLEAN", {"default": True}),
                "swap": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "custom_width": ("INT", {"default": 1280, "min": 64, "max": 16384, "step": 8}),
                "custom_height": ("INT", {"default": 720, "min": 64, "max": 16384, "step": 8}),
            }
        }

    RETURN_TYPES = ("INT", "INT", "STRING")
    RETURN_NAMES = ("width", "height", "resolution_str")
    OUTPUT_TOOLTIPS = (
        "Width in pixels",
        "Height in pixels",
        "Resolution as string (e.g. 1281x721)",
    )
    FUNCTION = "get_resolution"
    CATEGORY = "video"

    DESCRIPTION = "Video resolution selector with presets for 480p-8K. Supports LTX format (divisible_by + 1)."
    SEARCH_ALIASES = ["video size", "ltx resolution", "video dimensions", "cogvideo", "hunyuan", "ltx2"]

    def get_resolution(self, resolution, aspect_ratio, scale, divisible_by, add_one, swap,
                       custom_width=1280, custom_height=720):

        scale_factor = self.SCALE_FACTORS[scale]

        if resolution == "Custom":
            width = custom_width
            height = custom_height
        else:
            base_height = self.RESOLUTIONS[resolution]
            w_ratio, h_ratio = self.ASPECT_RATIOS[aspect_ratio]

            if w_ratio == h_ratio:
                width = base_height
                height = base_height
            elif w_ratio > h_ratio:
                height = base_height
                width = int(base_height * w_ratio / h_ratio)
            else:
                width = base_height
                height = int(base_height * h_ratio / w_ratio)

        # Apply scale
        width = int(width * scale_factor)
        height = int(height * scale_factor)

        # Round to nearest multiple of divisible_by
        width = (width // divisible_by) * divisible_by
        height = (height // divisible_by) * divisible_by

        # Ensure minimum size
        width = max(width, divisible_by)
        height = max(height, divisible_by)

        # Add 1 for LTX-style models (divisible_by + 1)
        if add_one:
            width += 1
            height += 1

        # Swap if requested
        if swap:
            width, height = height, width

        resolution_str = f"{width}x{height}"

        return (width, height, resolution_str)
