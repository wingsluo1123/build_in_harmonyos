import hashlib
import tempfile
import unittest
from pathlib import Path

from prepare_hap_resources import stage_resources, verify_font_bytes


class PrepareHapResourcesTests(unittest.TestCase):
    def test_verifies_size_and_sha256(self):
        font = b"font-resource"
        digest = hashlib.sha256(font).hexdigest()
        self.assertEqual(
            verify_font_bytes(font, expected_size=len(font), expected_sha256=digest), digest
        )

    def test_rejects_wrong_font_hash(self):
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            verify_font_bytes(b"font-resource", expected_size=13, expected_sha256="0" * 64)

    def test_rejects_wrong_font_size(self):
        with self.assertRaisesRegex(ValueError, "byte length mismatch"):
            verify_font_bytes(b"short", expected_size=12, expected_sha256="0" * 64)

    def test_stages_font_with_identical_content_and_run_id(self):
        font = b"verified-font-payload"
        digest = hashlib.sha256(font).hexdigest()
        temporary_root = Path(__file__).resolve().parents[6] / ".tmp" / "wqy-harmony-tests"
        temporary_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary_root) as temporary:
            root = Path(temporary)
            source = root / "source.ttc"
            source.write_bytes(font)
            app = root / "app"
            # The stage API pins production bytes; test its verifier separately above, then
            # use a test-local patched contract to avoid allocating the 16 MiB upstream font.
            import prepare_hap_resources as staging

            original_size = staging.EXPECTED_FONT_SIZE
            original_hash = staging.EXPECTED_FONT_SHA256
            try:
                staging.EXPECTED_FONT_SIZE = len(font)
                staging.EXPECTED_FONT_SHA256 = digest
                result = stage_resources(source, app)
            finally:
                staging.EXPECTED_FONT_SIZE = original_size
                staging.EXPECTED_FONT_SHA256 = original_hash

            rawfile = app / "entry/src/main/resources/rawfile"
            self.assertEqual((rawfile / "wqy-zenhei.ttc").read_bytes(), font)
            self.assertRegex(result["run_id"], r"^[0-9a-f]{32}$")
            self.assertEqual((rawfile / "wqy-test-run-id.txt").read_text().strip(), result["run_id"])
            self.assertEqual(result["sha256"], digest)
            self.assertTrue((app / "AppScope/resources/base/media/app_icon.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))


    def test_prefers_existing_svg_icons_over_png_duplicates(self):
        font = b"test-font"
        digest = hashlib.sha256(font).hexdigest()
        temporary_root = Path(__file__).resolve().parents[6] / ".tmp" / "wqy-harmony-tests"
        temporary_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary_root) as temporary:
            root = Path(temporary)
            source = root / "source.ttc"
            source.write_bytes(font)
            app = root / "app"
            icon_paths = (
                Path("AppScope/resources/base/media/app_icon.png"),
                Path("entry/src/main/resources/base/media/app_icon.png"),
            )
            svg = '<svg xmlns="http://www.w3.org/2000/svg" />'
            for relative in icon_paths:
                svg_path = (app / relative).with_suffix(".svg")
                svg_path.parent.mkdir(parents=True, exist_ok=True)
                svg_path.write_text(svg, encoding="utf-8")
                (app / relative).write_bytes(b"stale generated PNG")

            import prepare_hap_resources as staging

            original_size = staging.EXPECTED_FONT_SIZE
            original_hash = staging.EXPECTED_FONT_SHA256
            try:
                staging.EXPECTED_FONT_SIZE = len(font)
                staging.EXPECTED_FONT_SHA256 = digest
                stage_resources(source, app)
            finally:
                staging.EXPECTED_FONT_SIZE = original_size
                staging.EXPECTED_FONT_SHA256 = original_hash

            for relative in icon_paths:
                svg_path = (app / relative).with_suffix(".svg")
                self.assertEqual(svg_path.read_text(encoding="utf-8"), svg)
                self.assertFalse((app / relative).exists())

if __name__ == "__main__":
    unittest.main()
