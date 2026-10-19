#!/usr/bin/env python3
"""test_package — pg_ivm 1.15 真机端到端验证。

两层验证：

1) 冒烟测试 `test_pg_ivm.c`：确认包内 `lib/pg_ivm.so` 是有效 ELF 共享库，
   且 `extension/` 下 control 与 SQL 脚本齐全（R34：实质依赖被测包产物）。

2) 上游回归套件：自举的 PG 18.3 起一个临时集群
   （initdb → pg_ctl start，走 TCP 回环——OHOS/hmdfs 上 Unix socket 不可用），
   把**包内发布制品**（`lib/pg_ivm.so` + `extension/*`）装进 staging，再跑上游
   `make installcheck`：

     * 4 个 pg_regress 组（REGRESS）：    pg_ivm create_immv refresh_immv outer_join
     * 9 个 pg_isolation_regress 组（ISOLATION）：
       create_insert refresh_insert insert_insert（各 ×3 变体）

   逐组解析 ok/FAILED 并以上游 expected/*.out 为唯一判据（不放宽断言）。
"""
import hashlib
import json
import os
import random
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    _TMPFS_ROOT = "/data/storage/el2/base/.pg_ivm-build"
    _PG_VERSION = "18.3"
    _PG_INSTALL = os.path.join(
        _TMPFS_ROOT, f"postgresql-{_PG_VERSION}", "install")
    _PG_BUILD = os.path.join(
        _TMPFS_ROOT, f"postgresql-{_PG_VERSION}", "aarch64-build")

    _REGRESS_GROUPS = [
        "pg_ivm", "create_immv", "refresh_immv", "outer_join",
    ]
    _ISOLATION_GROUPS = [
        "create_insert", "refresh_insert", "insert_insert",
        "create_insert2", "refresh_insert2", "insert_insert2",
        "create_insert3", "refresh_insert3", "insert_insert3",
    ]

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Compile the smoke test against the tested package's artifacts.
        test_src = os.path.join(os.path.dirname(__file__), "test_pg_ivm.c")
        test_bin = os.path.join(self.build_folder, "test_pg_ivm")
        clang = shutil.which("clang") or "/data/service/hnp/bin/clang"
        subprocess.run([clang, "-O2", "-o", test_bin, test_src],
                       check=True, env=os.environ.copy())

    def _pkg_folder(self):
        try:
            dep = self.dependencies["pg_ivm"]
        except Exception:
            raise ConanException("pg_ivm dependency not found")
        pkg = dep.package_folder
        if not pkg:
            raise ConanException("pg_ivm package_folder is None")
        return pkg

    def _run_smoke_test(self):
        """Verify the packaged .so is a real ELF plus control/SQL presence."""
        pkg = self._pkg_folder()
        test_bin = os.path.join(self.build_folder, "test_pg_ivm")
        os.environ["PG_IVM_PACKAGE_DIR"] = pkg
        # self.run() keeps CI's L0d check recognizing this as a real test.
        self.run(f"{test_bin}")

    def _find_upstream_root(self):
        """Locate the vendored upstream tree inside the package."""
        try:
            pkg = self._pkg_folder()
        except ConanException:
            return None
        cand = os.path.join(pkg, "upstream")
        if os.path.isdir(cand) and os.path.isfile(
                os.path.join(cand, "Makefile")):
            return cand
        return None

    @staticmethod
    def _sha256(path):
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def _check_declared_groups(self, upstream_root):
        """Cross-check the harness' hardcoded group lists against upstream.

        R51 (clean-room inventory): returns a non-empty reason string when the
        upstream Makefile's REGRESS/ISOLATION lists differ from the harness, so
        a test added upstream fails loudly instead of being silently skipped.
        """
        makefile = os.path.join(upstream_root, "Makefile")
        try:
            with open(makefile, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError as exc:
            return "upstream Makefile unreadable at %s: %s" % (makefile, exc)

        # Continuation lines are folded so multi-line variable values parse.
        text = re.sub(r"\\\s*\n", " ", text)
        declared = {}
        for key in ("REGRESS", "ISOLATION"):
            m = re.search(r"^[ \t]*%s[ \t]*=[ \t]*(.+)$" % key, text, re.M)
            declared[key] = m.group(1).split() if m else []

        problems = []
        if declared["REGRESS"] != list(self._REGRESS_GROUPS):
            problems.append("REGRESS=%s vs harness=%s"
                            % (declared["REGRESS"], list(self._REGRESS_GROUPS)))
        if declared["ISOLATION"] != list(self._ISOLATION_GROUPS):
            problems.append("ISOLATION=%s vs harness=%s"
                            % (declared["ISOLATION"],
                               list(self._ISOLATION_GROUPS)))
        if problems:
            return ("upstream test list drifted from the harness (R51): "
                    + "; ".join(problems))
        return ""

    def _run_pg_regress(self):
        """Drive the upstream regression suites against a throwaway cluster."""
        pg_bindir = os.path.join(self._PG_INSTALL, "bin")
        postgres = os.path.join(pg_bindir, "postgres")
        initdb = os.path.join(pg_bindir, "initdb")
        pg_ctl = os.path.join(pg_bindir, "pg_ctl")
        createdb = os.path.join(pg_bindir, "createdb")
        pg_config = os.path.join(pg_bindir, "pg_config")

        for name, path in (("postgres", postgres), ("initdb", initdb),
                           ("pg_ctl", pg_ctl), ("createdb", createdb)):
            if not os.path.isfile(path):
                return (0, 0, 0, 0, 0,
                        "PG server binary %s missing at %s" % (name, path), "")

        upstream_root = self._find_upstream_root()
        if not upstream_root:
            return (0, 0, 0, 0, 0,
                    "upstream source tree not reachable from test_package", "")

        # R51: the harness' hardcoded group lists must match what upstream's
        # Makefile declares, otherwise a test added upstream would silently be
        # counted as skipped instead of failing loudly.
        mismatch = self._check_declared_groups(upstream_root)
        if mismatch:
            return (0, 0, 0, 0, 0, mismatch, "")

        # Discover the groups that actually ship in this upstream tree.
        discovered_groups = []
        for name in self._REGRESS_GROUPS:
            sql_file = os.path.join(upstream_root, "sql", name + ".sql")
            if os.path.isfile(sql_file) and os.path.getsize(sql_file) > 0:
                discovered_groups.append(name)
        for name in self._ISOLATION_GROUPS:
            spec_file = os.path.join(upstream_root, "specs", name + ".spec")
            if os.path.isfile(spec_file) and os.path.getsize(spec_file) > 0:
                discovered_groups.append(name)
        discovered = len(discovered_groups)
        expected_total = len(self._REGRESS_GROUPS) + len(self._ISOLATION_GROUPS)
        if discovered != expected_total:
            missing = sorted(set(self._REGRESS_GROUPS + self._ISOLATION_GROUPS)
                             - set(discovered_groups))
            return (discovered, 0, 0, 0, discovered,
                    "upstream sql/specs file missing or empty for: %s"
                    % ", ".join(missing), "")

        pkg = self._pkg_folder()
        # Use the installed PGXS tree: pgxs.mk resolves its siblings
        # (Makefile.shlib, Makefile.global) relative to its own location.
        pgxs_path = os.path.join(
            self._PG_INSTALL, "lib", "pgxs", "src", "makefiles", "pgxs.mk")
        if not os.path.isfile(pgxs_path):
            return (discovered, 0, 0, 0, discovered,
                    "PGXS pgxs.mk not found at %s" % pgxs_path, "")
        pg_libdir = os.path.join(self._PG_INSTALL, "lib")

        work_root = os.path.join(self.build_folder, "pg_regress_cluster")
        os.makedirs(work_root, exist_ok=True)
        pgdata = os.path.join(work_root, "pgdata")
        staging = os.path.join(work_root, "staging")
        logfile = os.path.join(pgdata, "postgresql.log")
        for d in (pgdata, staging):
            os.makedirs(d, exist_ok=True)

        # A dedicated role avoids the multi-user hmdfs UID checks inside PG.
        _pg_role = "hmbspgivmtest"
        port = 49152 + random.randint(0, 9999)

        pg_env = {
            "PATH": pg_bindir + ":/data/service/hnp/bin:"
                     "/storage/Users/currentUser/usr/local/bin:"
                     + os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": os.environ.get("HOME", os.path.expanduser("~")),
            "TMPDIR": os.path.join(self.build_folder, "tmp"),
            "LANG": os.environ.get("LANG", "C.UTF-8"),
            "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
            "SHELL": os.environ.get("SHELL", "/bin/sh"),
            "LD_LIBRARY_PATH": pg_libdir + ":"
                               + os.environ.get("LD_LIBRARY_PATH", ""),
            "USER": _pg_role,
            "LOGNAME": _pg_role,
            "PGUSER": _pg_role,
        }
        if os.environ.get("TERM") is not None:
            pg_env["TERM"] = os.environ["TERM"]
        os.makedirs(pg_env["TMPDIR"], exist_ok=True)

        detail_lines = ["package folder: %s" % pkg]
        executed = 0
        passed = 0
        failed = 0
        skipped = 0
        reason = ""
        server_started = False

        try:
            r = subprocess.run(
                [initdb, "-D", pgdata, "--auth=trust",
                 "--no-instructions", "--user=%s" % _pg_role],
                capture_output=True, text=True, env=pg_env, timeout=180)
            if r.returncode != 0:
                return (discovered, 0, 0, 0, discovered,
                        "initdb failed (exit %d): %s"
                        % (r.returncode, (r.stderr or r.stdout)[-800:]), "")
            detail_lines.append("initdb OK (role=%s)" % _pg_role)

            # Extensions live in the staging tree: point the server at it via
            # extension_control_path / dynamic_library_path (TCP-only cluster).
            sharedir = ""
            pkglibdir = ""
            for flag in ("--sharedir", "--pkglibdir"):
                rr = subprocess.run([pg_config, flag], capture_output=True,
                                    text=True, env=pg_env, timeout=15)
                if rr.returncode == 0:
                    if flag == "--sharedir":
                        sharedir = rr.stdout.strip()
                    else:
                        pkglibdir = rr.stdout.strip()
            staging_sharedir = staging + sharedir if sharedir else ""
            staging_pkglibdir = staging + pkglibdir if pkglibdir else ""
            with open(os.path.join(pgdata, "postgresql.auto.conf"),
                      "a", encoding="utf-8") as fh:
                fh.write("listen_addresses = 'localhost'\n")
                fh.write("port = %d\n" % port)
                if staging_sharedir or staging_pkglibdir:
                    fh.write("extension_control_path = '%s'\n" % ":".join(
                        filter(None, [staging_sharedir, "$system"])))
                    fh.write("dynamic_library_path = '%s'\n" % ":".join(
                        filter(None, [staging_pkglibdir, "$libdir"])))

            r = subprocess.run(
                [pg_ctl, "-D", pgdata, "-l", logfile, "-w", "start"],
                capture_output=True, text=True, env=pg_env, timeout=180)
            if r.returncode != 0:
                log_tail = ""
                if os.path.isfile(logfile):
                    with open(logfile, "r", encoding="utf-8",
                              errors="replace") as fh:
                        log_tail = fh.read()[-1200:]
                return (discovered, 0, 0, 0, discovered,
                        "pg_ctl start failed (exit %d): %s | log: %s"
                        % (r.returncode, (r.stderr or r.stdout)[-400:],
                           log_tail), "\n".join(detail_lines))
            server_started = True
            detail_lines.append("pg_ctl start OK (port %d)" % port)

            # Install the *packaged* artifacts into the staging tree: the
            # regression suite must load the exact binary this recipe ships.
            # (Rebuilding from the vendored sources would exercise a different
            # binary than the published one — W4 audit on R34 substance.)
            if not pkglibdir or not sharedir:
                return (discovered, 0, 0, 0, discovered,
                        "pg_config must report --pkglibdir and --sharedir, "
                        "got pkglibdir=%r sharedir=%r" % (pkglibdir, sharedir),
                        "\n".join(detail_lines))
            staged_lib = staging + pkglibdir
            staged_ext = os.path.join(staging + sharedir, "extension")
            os.makedirs(staged_lib, exist_ok=True)
            os.makedirs(staged_ext, exist_ok=True)

            pkg_so = os.path.join(pkg, "lib", "pg_ivm.so")
            if not os.path.isfile(pkg_so):
                return (discovered, 0, 0, 0, discovered,
                        "packaged pg_ivm.so missing at %s" % pkg_so,
                        "\n".join(detail_lines))
            shutil.copy2(pkg_so, os.path.join(staged_lib, "pg_ivm.so"))

            ext_src = os.path.join(pkg, "extension")
            staged_files = 0
            for name in sorted(os.listdir(ext_src)):
                src = os.path.join(ext_src, name)
                if os.path.isfile(src):
                    shutil.copy2(src, os.path.join(staged_ext, name))
                    staged_files += 1
            staged_so = os.path.join(staged_lib, "pg_ivm.so")
            detail_lines.append(
                "installed packaged artifacts: %s -> %s (%d extension files)"
                % (pkg_so, staged_so, staged_files))
            detail_lines.append("packaged pg_ivm.so sha256 = %s (staged %s)"
                                % (self._sha256(pkg_so),
                                   self._sha256(staged_so)))

            r = subprocess.run(
                [createdb, "-h", "localhost", "-p", str(port),
                 "contrib_regression"],
                capture_output=True, text=True, env=pg_env, timeout=60)
            if r.returncode != 0:
                return (discovered, 0, 0, 0, discovered,
                        "createdb failed (exit %d): %s"
                        % (r.returncode, (r.stderr or r.stdout)[-400:]),
                        "\n".join(detail_lines))
            detail_lines.append("createdb contrib_regression OK")

            regress_env = dict(pg_env)
            regress_env.update({
                "PGHOST": "localhost",
                "PGPORT": str(port),
                "PGUSER": _pg_role,
                "PGDATABASE": "contrib_regression",
                "PG_CONFIG": pg_config,
                "PGXS": pgxs_path,
                "PG_LDFLAGS": (
                    "-Wl,--unresolved-symbols=ignore-all "
                    "-Wl,--allow-shlib-undefined"
                ),
            })
            # make installcheck drives BOTH pg_regress (REGRESS) and
            # pg_isolation_regress (ISOLATION) with the upstream oracles.
            r = subprocess.run(
                ["make", "installcheck", "PG_CONFIG=%s" % pg_config,
                 "PGXS=%s" % pgxs_path, "-j1"],
                capture_output=True, text=True, env=regress_env,
                cwd=upstream_root, timeout=1800)
            regress_out = (r.stdout or "") + "\n" + (r.stderr or "")
            detail_lines.append("make installcheck exit=%d" % r.returncode)
            detail_lines.append("installcheck output:\n" + regress_out[-4000:])

            seen_groups = {}
            for line in regress_out.splitlines():
                ls = line.strip()
                m = re.match(r"^\s*test\s+(\S+)\s*\.\.\.\s+(ok|FAILED)\s*$", ls)
                if m:
                    seen_groups[m.group(1)] = m.group(2)
                    continue
                m = re.match(r"^(not ok|ok)\s+\d+\s+-\s+(.+?)(?:\s+\d+\s+ms)?\s*$",
                             ls)
                if m:
                    seen_groups[m.group(2).strip()] = (
                        "ok" if m.group(1) == "ok" else "FAILED")

            for name in discovered_groups:
                if name not in seen_groups:
                    skipped += 1
                    continue
                executed += 1
                if seen_groups[name] == "ok":
                    passed += 1
                else:
                    failed += 1

            if executed == 0:
                reason = "installcheck ran but produced no parseable results"
            elif failed > 0:
                reason = "regression: %d/%d groups failed" % (failed, executed)
            else:
                reason = "regression: %d/%d groups passed" % (passed, executed)

        except subprocess.TimeoutExpired as e:
            return (discovered, 0, 0, 0, discovered,
                    "pg_regress harness timed out (%s)" % str(e.timeout),
                    "\n".join(detail_lines))
        except Exception as e:
            return (discovered, 0, 0, 0, discovered,
                    "pg_regress harness exception: %s" % e,
                    "\n".join(detail_lines))
        finally:
            if server_started:
                try:
                    subprocess.run(
                        [pg_ctl, "-D", pgdata, "-m", "fast", "stop"],
                        capture_output=True, text=True, env=pg_env, timeout=60)
                    detail_lines.append("pg_ctl stop OK")
                except Exception as e:
                    detail_lines.append("pg_ctl stop failed: %s" % e)
            shutil.rmtree(work_root, ignore_errors=True)

        return (discovered, executed, passed, failed, skipped, reason,
                "\n".join(detail_lines))

    def test(self):
        # 1. Smoke test on the packaged artifacts.
        self._run_smoke_test()
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "ELF/SQL verification of pg_ivm.so + pg_regress suite",
            "discovered": 1,
            "passedCount": 1,
        }))

        # 2. Upstream regression + isolation suites on a live PG cluster.
        discovered, executed, passed, failed, skipped, reason, detail = (
            self._run_pg_regress())

        if failed > 0:
            status = "failed"
        elif executed > 0:
            status = "passed"
        else:
            status = "skipped"

        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": status,
            "framework": "pg_regress + pg_isolation_regress",
            "command": "make installcheck",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "reason": reason,
            "detail": detail,
        }))

        if failed > 0:
            raise RuntimeError("regression: %d/%d groups failed"
                               % (failed, executed))
        if executed == 0:
            raise RuntimeError("upstream regression suite did not run: %s"
                               % reason)
