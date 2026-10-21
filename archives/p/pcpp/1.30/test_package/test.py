#!/usr/bin/env python3
"""Exercise the installed preprocessor and CLI with real source fragments."""
import io
import pathlib
import subprocess
import sys
import tempfile
import unittest

installed = pathlib.Path(sys.argv.pop(1)).resolve()
package = pathlib.Path(sys.argv.pop(1)).resolve()
sys.path.insert(0, str(installed))
import pcpp
from pcpp import Preprocessor


def preprocess(text):
    parser = Preprocessor()
    parser.parse(text)
    output = io.StringIO()
    parser.write(output)
    return output.getvalue(), parser.return_code


class Consumer(unittest.TestCase):
    def test_installed(self):
        self.assertTrue(pathlib.Path(pcpp.__file__).resolve().is_relative_to(installed))

    def test_macro(self):
        output, code = preprocess('#define VALUE 42\nVALUE\n')
        self.assertEqual(output.strip(), '42')
        self.assertEqual(code, 0)

    def test_function_macro(self):
        self.assertEqual(preprocess('#define ADD(a,b) ((a)+(b))\nADD(2,3)\n')[0].strip(), '((2)+(3))')

    def test_condition(self):
        self.assertEqual(preprocess('#if 3*4 == 12\nyes\n#else\nno\n#endif\n')[0].strip(), 'yes')

    def test_undef(self):
        self.assertEqual(preprocess('#define X 1\n#undef X\nX\n')[0].strip(), 'X')

    def test_include(self):
        with tempfile.TemporaryDirectory() as folder:
            pathlib.Path(folder, 'value.h').write_text('#define V 123\n')
            parser = Preprocessor()
            parser.add_path(folder)
            parser.parse('#include "value.h"\nV\n')
            stream = io.StringIO()
            parser.write(stream)
            self.assertIn('123', stream.getvalue())
            self.assertEqual(parser.return_code, 0)

    def test_cli(self):
        result = subprocess.run([sys.executable, str(package / 'bin/pcpp'), '-D', 'N=19', '-'], input='N\n', text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), '#line 1 "<stdin>"\n19')

    def test_cli_error(self):
        result = subprocess.run([sys.executable, str(package / 'bin/pcpp'), '-'], input='#error deliberate-test\n', text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('deliberate-test', result.stderr)


unittest.main(verbosity=2)
