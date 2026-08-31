import unittest

from video_resolution_node import VideoResolutionNode, preview_resolution


def resolve(**changes):
    inputs = VideoResolutionNode.INPUT_TYPES()["required"]
    values = {name: spec[1]["default"] for name, spec in inputs.items()}
    values.update(changes)
    return VideoResolutionNode().get_resolution(**values)


class VideoResolutionTests(unittest.TestCase):
    def test_existing_default_and_custom_outputs(self):
        self.assertEqual(resolve(), (1280, 704, "1280x704"))
        self.assertEqual(resolve(model_profile="Custom"), (1281, 705, "1281x705"))
        self.assertEqual(resolve(resolution="Custom", custom_mode="from_width",
                                 custom_width=1280, model_profile="MiniMax H3"),
                         (1280, 704, "1280x704"))

    def test_h3_native_orientation_and_square(self):
        for aspect, expected in [("16:9 (Widescreen)", (1344, 768)),
                                 ("9:16 (Vertical)", (768, 1344)),
                                 ("1:1 (Square)", (768, 768)),
                                 ("4:3 (Classic)", (1024, 768))]:
            with self.subTest(aspect=aspect):
                self.assertEqual(resolve(resolution="H3 Native (768p)", aspect_ratio=aspect,
                                         model_profile="MiniMax H3")[:2], expected)
        self.assertEqual(resolve(resolution="H3 Native (768p)", model_profile="MiniMax H3",
                                 swap=True)[:2], (768, 1344))

    def test_h3_native_ultrawide_uses_area_cap_before_alignment(self):
        width, height, _ = resolve(resolution="H3 Native (768p)",
                                   aspect_ratio="21:9 (Ultrawide)", model_profile="MiniMax H3")
        self.assertEqual((width, height), (1536, 672))

    def test_megapixel_rounding_uses_fractional_dimensions(self):
        expected = {"floor": (704, 384), "nearest": (736, 416), "ceil": (736, 416)}
        for mode, size in expected.items():
            self.assertEqual(resolve(resolution="0.3 MP", model_profile="MiniMax H3",
                                     rounding_mode=mode)[:2], size)
        self.assertEqual(VideoResolutionNode._quantize(32.1, 32, "ceil"), 64)

    def test_all_profiles_and_presets_obey_alignment(self):
        for profile, rules in VideoResolutionNode.MODEL_PROFILES.items():
            if profile == "Custom":
                continue
            for preset in VideoResolutionNode.RESOLUTIONS:
                for aspect in VideoResolutionNode.ASPECT_RATIOS:
                    with self.subTest(profile=profile, preset=preset, aspect=aspect):
                        width, height, label = resolve(resolution=preset, model_profile=profile,
                                                       aspect_ratio=aspect, add_one=True, divisible_by=8)
                        self.assertEqual(width % rules["divisible_by"], 0)
                        self.assertEqual(height % rules["divisible_by"], 0)
                        self.assertGreater(min(width, height), 0)
                        self.assertEqual(label, f"{width}x{height}")

    def test_scale_is_linear_and_minimum_size_is_valid(self):
        self.assertEqual(resolve(resolution="H3 Native (768p)", model_profile="MiniMax H3",
                                 scale="0.5x")[:2], (672, 384))
        self.assertEqual(resolve(resolution="Custom", custom_width=64, custom_height=64,
                                 model_profile="MiniMax H3", scale="0.25x")[:2], (32, 32))

    def test_custom_mp_matches_presets_and_preserves_old_calls(self):
        for name, budget in VideoResolutionNode.MEGAPIXELS.items():
            for mode in VideoResolutionNode.ROUNDING_MODES:
                self.assertEqual(resolve(resolution="Custom MP", custom_megapixels=budget,
                                         model_profile="MiniMax H3", rounding_mode=mode),
                                 resolve(resolution=name, model_profile="MiniMax H3", rounding_mode=mode))
        self.assertEqual(resolve(resolution="Custom MP", custom_megapixels=0.4,
                                 model_profile="MiniMax H3", rounding_mode="nearest")[:2], (832, 480))
        old_args = [definition[1]["default"] for definition in VideoResolutionNode.INPUT_TYPES()["required"].values()]
        self.assertEqual(VideoResolutionNode().get_resolution(*old_args), (1280, 704, "1280x704"))

    def test_custom_mp_rejects_invalid_budgets_only_when_used(self):
        for value in (0, -1, 0.001, 16.01, float("nan"), float("inf"), "0.5", True, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                resolve(resolution="Custom MP", custom_megapixels=value)
        for value in (0.01, 16):
            width, height, _ = resolve(resolution="Custom MP", custom_megapixels=value,
                                       model_profile="MiniMax H3", scale="2x")
            self.assertGreater(min(width, height), 0)
            self.assertEqual(width % 32, 0)
            self.assertEqual(height % 32, 0)
        self.assertEqual(resolve(custom_megapixels=float("nan")), resolve())

    def test_preview_reports_effective_rules_and_exact_execution_outputs(self):
        for profile in VideoResolutionNode.MODEL_PROFILES:
            for preset in VideoResolutionNode.RESOLUTIONS:
                values = dict(resolution=preset, model_profile=profile, custom_megapixels=0.4)
                result = preview_resolution(values)
                self.assertEqual((result["width"], result["height"], result["resolution_str"]), resolve(**values))
                self.assertEqual(result["megapixels"], result["width"] * result["height"] / 1_000_000)
        self.assertEqual(preview_resolution({})["multiple"], 64)
        self.assertFalse(preview_resolution({})["add_one"])
        self.assertTrue(preview_resolution({"model_profile": "Custom"})["add_one"])

    def test_preview_validates_values_before_calculating(self):
        for payload in ([], None, {"unknown": 1}, {"resolution": "unknown"},
                        {"custom_width": True}, {"custom_width": -1}, {"custom_height": 1.5},
                        {"custom_megapixels": float("nan")}, {"custom_megapixels": 17},
                        {"swap": "false"}, {"model_profile": None}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                preview_resolution(payload)


if __name__ == "__main__":
    unittest.main()
