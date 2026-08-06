import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import predownload_sources


class PredownloadSourcesTests(unittest.TestCase):
    def test_source_nodes_preserve_hyphenated_urls(self):
        document = yaml.safe_load(
            """
sources:
  url:
    - https://gh-proxy.com/https://github.com/coin-or/Osi/source.tar.gz
    - https://github.com/coin-or/Osi/source.tar.gz
  sha256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
test_sources:
  data-sample:
    url: https://github.com/coin-or-tools/Data-Sample/sample.tar.gz
    sha256: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
"""
        )

        nodes = list(predownload_sources.source_nodes(document))

        self.assertEqual(len(nodes), 2)
        self.assertIn("coin-or", nodes[0]["url"][0])
        self.assertIn("Data-Sample", nodes[1]["url"])

    def test_valid_cached_source_is_rewritten_to_file_url(self):
        payload = b"verified source archive"
        expected = hashlib.sha256(payload).hexdigest()
        document = {
            "sources": {
                "url": "https://github.com/coin-or/Osi/source.tar.gz",
                "sha256": expected,
            }
        }

        with tempfile.TemporaryDirectory() as directory:
            cache_dir = Path(directory)
            urls = predownload_sources.candidate_urls(document["sources"]["url"])
            cached = predownload_sources.cache_path(cache_dir, urls, expected)
            cached.write_bytes(payload)

            rewritten = predownload_sources.predownload(document, cache_dir)

        self.assertEqual(rewritten, 1)
        self.assertTrue(document["sources"]["url"].startswith("file://"))

    def test_bad_download_is_not_rewritten(self):
        expected = "a" * 64
        original = "https://github.com/coin-or/Osi/source.tar.gz"
        document = {"sources": {"url": original, "sha256": expected}}

        def fake_download(_url, destination):
            destination.write_bytes(b"not the expected archive")
            return True, "200", ""

        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.object(predownload_sources, "download", fake_download):
                rewritten = predownload_sources.predownload(
                    document, Path(directory)
                )

        self.assertEqual(rewritten, 0)
        self.assertEqual(document["sources"]["url"], original)

    def test_source_without_sha256_is_left_unchanged(self):
        original = "https://example.com/source-with-hyphen.tar.gz"
        document = {"sources": {"url": original}}

        with tempfile.TemporaryDirectory() as directory:
            rewritten = predownload_sources.predownload(
                document, Path(directory)
            )

        self.assertEqual(rewritten, 0)
        self.assertEqual(document["sources"]["url"], original)


if __name__ == "__main__":
    unittest.main()
