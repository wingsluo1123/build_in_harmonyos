#!/usr/bin/env python3
"""Exercise the installed parser extension, Python APIs and pgpp entry point."""

import json
import os
from pathlib import Path
import subprocess
import unittest

import pglast
from pglast import ast, parse_plpgsql, parse_sql, prettify
from pglast.parser import ParseError, fingerprint, parse_sql_json, scan, split
from pglast.visitors import referenced_relations


class InstalledPglastTests(unittest.TestCase):
    def test_installed_origin_and_version(self):
        root = Path(os.environ["PGLAST_PACKAGE_ROOT"]).resolve()
        self.assertTrue(Path(pglast.__file__).resolve().is_relative_to(root))
        self.assertEqual(pglast.__version__, "v8.2")
        self.assertTrue(Path(pglast.parser.__file__).resolve().is_relative_to(root))

    def test_sql_ast(self):
        statement = parse_sql("SELECT 42")[0]
        self.assertIsInstance(statement, ast.RawStmt)
        self.assertIsInstance(statement.stmt, ast.SelectStmt)
        self.assertEqual(statement.stmt.targetList[0].val.val.ival, 42)

    def test_empty_and_invalid_sql(self):
        self.assertEqual(parse_sql(""), ())
        with self.assertRaises(ParseError):
            parse_sql("SELECT FROM")

    def test_json_parser(self):
        result = json.loads(parse_sql_json("SELECT 1"))
        self.assertEqual(len(result["stmts"]), 1)
        self.assertIn("SelectStmt", result["stmts"][0]["stmt"])

    def test_plpgsql_parser(self):
        result = parse_plpgsql("""CREATE FUNCTION add(a integer, b integer)
            RETURNS integer AS $$ BEGIN RETURN a + b; END; $$ LANGUAGE plpgsql""")
        self.assertEqual(len(result), 1)
        self.assertIn("PLpgSQL_function", result[0])

    def test_fingerprint_and_scanner(self):
        self.assertEqual(fingerprint("SELECT 1"), fingerprint("SELECT 2"))
        self.assertEqual(len(scan("SELECT 1")), 2)

    def test_split_prettify_and_relations(self):
        self.assertEqual(split("SELECT 1; SELECT 2"), ("SELECT 1", "SELECT 2"))
        self.assertEqual(prettify("select 1"), "SELECT 1")
        self.assertEqual(referenced_relations("SELECT * FROM users"), {"users"})

    def test_installed_cli(self):
        root = Path(os.environ["PGLAST_PACKAGE_ROOT"])
        command = root.parents[2] / "bin" / "pgpp"
        result = subprocess.run([str(command)], input="select 1", text=True,
                                capture_output=True, check=True)
        self.assertEqual(result.stdout, "SELECT 1\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
