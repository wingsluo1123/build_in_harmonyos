#!/usr/bin/env python3
"""Exercise purl from the installed Conan package, outside its source tree."""

import os
from pathlib import Path
import pickle
import unittest

import purl
from purl import Template, URL, expand


class PurlConsumerTest(unittest.TestCase):
    def test_import_is_from_package(self):
        root = Path(os.environ["PURL_PACKAGE_ROOT"]).resolve()
        self.assertTrue(Path(purl.__file__).resolve().is_relative_to(root))
        self.assertEqual(purl.__version__, "1.6")

    def test_parse_components(self):
        url = URL("https://alice:secret@example.com:8443/a?q=42#frag")
        self.assertEqual(url.scheme(), "https")
        self.assertEqual(url.host(), "example.com")
        self.assertEqual(url.port(), 8443)
        self.assertEqual(url.username(), "alice")
        self.assertEqual(url.password(), "secret")
        self.assertEqual(url.path(), "/a")
        self.assertEqual(url.query_param("q"), "42")
        self.assertEqual(url.fragment(), "frag")

    def test_mutation_preserves_original(self):
        original = URL("https://example.com/a")
        changed = original.add_path_segment("b").query_param("q", "hello world")
        self.assertEqual(original.as_string(), "https://example.com/a")
        self.assertEqual(changed.as_string(), "https://example.com/a/b?q=hello+world")

    def test_repeated_query_values(self):
        url = URL("https://example.com/?tag=a").append_query_param("tag", "b")
        self.assertEqual(url.query_param("tag", as_list=True), ["a", "b"])
        self.assertEqual(url.remove_query_param("tag", "a").query_param("tag"), "b")

    def test_unicode_path(self):
        url = URL("https://example.com/").add_path_segment("中文")
        self.assertEqual(url.as_string(), "https://example.com/%E4%B8%AD%E6%96%87")

    def test_password_with_at_sign(self):
        url = URL("https://alice:a@b@example.com/")
        self.assertEqual(url.password(), "a@b")
        self.assertEqual(url.host(), "example.com")

    def test_pickle_roundtrip(self):
        url = URL("https://example.com/a?q=1")
        self.assertEqual(pickle.loads(pickle.dumps(url)), url)

    def test_reserved_template_expansion(self):
        self.assertEqual(expand("{+path}/here", {"path": "/foo/bar"}), "/foo/bar/here")

    def test_template_returns_url(self):
        url = Template("https://example.com{/name}").expand({"name": "hello world"})
        self.assertIsInstance(url, URL)
        self.assertEqual(url.as_string(), "https://example.com/hello%20world")

    def test_missing_template_variable(self):
        url = Template("https://example.com/items{/name}").expand()
        self.assertEqual(url.as_string(), "https://example.com/items")


if __name__ == "__main__":
    unittest.main(verbosity=2)
