"""Six focused tests for the end-of-line correction and existing boundary."""
from pathlib import Path
import os
import re
import unittest
import manuel


class LineBoundaryTests(unittest.TestCase):
    def check_region(self, end):
        text = 'BEGIN block\nbody\nEND block\ntail\n'
        document = manuel.Document(text)
        [region] = document.find_regions(re.compile(r'^BEGIN.*$', re.M), re.compile(end, re.M))
        self.assertEqual(region.source, 'BEGIN block\nbody\nEND block\n', 'MANUEL_REGION_CONTENT_LOSS: end-marker line suffix truncated')
        document.claim_region(region)
        self.assertEqual(''.join(item.source for item in document), text, 'MANUEL_REGION_CONTENT_LOSS: claim_region changed document text')

    def test_prefix_end_preserves_suffix(self):
        self.check_region(r'^END')

    def test_full_line_end_control(self):
        self.check_region(r'^END.*$')

    def test_exact_end_control(self):
        self.check_region(r'^END block$')

    def test_end_consuming_newline_does_not_consume_next_line(self):
        self.check_region(r'^END block\n')

    def test_empty_remainder(self):
        self.assertEqual(manuel.find_end_of_line(''), 0)

    def test_immediate_newline(self):
        self.assertEqual(manuel.find_end_of_line('\nnext'), 0)


if __name__ == '__main__':
    expected_package = os.environ.get('MANUEL_EXPECT_PACKAGE')
    if expected_package:
        assert Path(manuel.__file__).resolve().is_relative_to(Path(expected_package).resolve()), manuel.__file__
    unittest.main()
