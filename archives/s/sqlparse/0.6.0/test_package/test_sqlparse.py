import os
from pathlib import Path
import subprocess
import sys
import unittest

MODULE_DIR = Path(sys.argv.pop(1)).resolve()
sys.path.insert(0, str(MODULE_DIR))
import sqlparse


class PackagedSqlparseTests(unittest.TestCase):
    def test_package_origin(self):
        self.assertEqual(Path(sqlparse.__file__).resolve().parent, MODULE_DIR / "sqlparse")
        self.assertEqual(sqlparse.__version__, "0.6.0")

    def test_parse(self):
        statements = sqlparse.parse("select name from users where id = 3;")
        self.assertEqual(len(statements), 1)
        self.assertEqual(statements[0].get_type(), "SELECT")

    def test_split(self):
        self.assertEqual(sqlparse.split("select 'a;b'; select 2;"),
                         ["select 'a;b';", "select 2;"])

    def test_format(self):
        self.assertEqual(sqlparse.format("select a from t", keyword_case="upper"),
                         "SELECT a FROM t")

    def test_cli(self):
        env = dict(os.environ, PYTHONPATH=str(MODULE_DIR),
                   PYTHONDONTWRITEBYTECODE="1")
        result = subprocess.run([sys.executable, "-m", "sqlparse", "-k", "upper", "-"],
                                input="select 1;", text=True, capture_output=True,
                                env=env, check=True)
        self.assertEqual(result.stdout.strip(), "SELECT 1;")


if __name__ == "__main__":
    unittest.main(verbosity=2)
