# ComfyUI Video Resolution

A simple ComfyUI node for selecting video resolutions. Outputs `width` and `height` for video generation models like **LTX**, **CogVideo**, **Hunyuan**, and others.

## Installation

### Option 1: ComfyUI Manager
Search for "Video Resolution" in ComfyUI Manager and install.

### Option 2: Manual
```bash
cd ComfyUI/custom_nodes
git clone https://github.com/hyukudan/comfyui-video-resolution.git
```

Restart ComfyUI after installation.

## Usage

Search for **"Video Resolution"** in the node menu (or use aliases: "video size", "ltx resolution", "ltx2").

### Inputs

| Parameter | Description |
|-----------|-------------|
| **resolution** | Preset: 480p, 720p, 1080p, 1440p (2K), 2160p (4K), 4320p (8K), or Custom |
| **aspect_ratio** | 1:1, 16:9, 19:9, 2.39:1, 9:16, 4:3, 5:4, 3:4, 4:5, 21:9, 9:21, 3:2, 2:3 |
| **scale** | Multiply resolution: 0.25x, 0.5x, 0.75x, 1x, 1.25x, 1.5x, 2x |
| **model_profile** | Applies recommended sizing rules for common video models. `Custom` leaves `divisible_by` and `add_one` untouched |
| **custom_mode** | In `Custom`: `manual` uses width+height as-is, `from_width` recalculates height from `aspect_ratio`, `from_height` recalculates width |
| **custom_width** | Custom width reference value |
| **custom_height** | Custom height reference value |
| **divisible_by** | Ensure dimensions are divisible by: 8, 16, 32, or 64 |
| **rounding_mode** | Quantization mode for divisibility: `floor`, `nearest`, or `ceil` |
| **add_one** | Add +1 to dimensions when the target model really requires it |
| **swap** | Swap width and height |

### Outputs

| Output | Type | Description |
|--------|------|-------------|
| **width** | INT | Width in pixels |
| **height** | INT | Height in pixels |
| **resolution_str** | STRING | Resolution as text (e.g., "1281x721") |

## Resolution Examples (with add_one=True)

| Preset | 1:1 | 16:9 | 9:16 |
|--------|-----|------|------|
| 480p | 481x481 | 833x481 | 481x833 |
| 720p | 705x705 | 1281x705 | 705x1249 |
| 1080p | 1057x1057 | 1921x1057 | 1057x1889 |
| 4K | 2145x2145 | 3841x2145 | 2145x3809 |

*Values shown with divisible_by=32, add_one=True (legacy LTX-style sizing).*

## Custom Mode Notes

- `resolution = Custom` + `custom_mode = manual`: the node uses `custom_width` and `custom_height` directly.
- `resolution = Custom` + `custom_mode = from_width`: changing `aspect_ratio` now updates the height.
- `resolution = Custom` + `custom_mode = from_height`: changing `aspect_ratio` now updates the width.
- If `resolution` is not `Custom`, `custom_width` and `custom_height` are ignored.
- If you want the closest valid size instead of always rounding down, use `rounding_mode = nearest`.

## Model Profiles

- `LTX Video / LTX2`: forces `divisible_by = 64` and `add_one = False` for compatibility with the `ComfyUI-LTXVideo` workflows in this repo
- `CogVideoX`: forces `divisible_by = 16` and `add_one = False`
- `Hunyuan Video`: forces `divisible_by = 16` and `add_one = False`
- `Mochi`: forces `divisible_by = 64` and `add_one = False`
- `Wan 2.x`: forces `divisible_by = 16` and `add_one = False`
- `Custom`: respects the values you set manually

## Model Recommendations

| Model | divisible_by | add_one |
|-------|-------------|---------|
| **LTX Video / LTX2** | 64 | False |
| CogVideoX | 16 | False |
| Hunyuan Video | 16 | False |
| Mochi | 64 | False |
| Wan 2.x | 16 | False |

## License

MIT License
