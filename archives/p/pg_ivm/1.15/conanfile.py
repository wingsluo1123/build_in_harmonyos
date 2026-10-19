#!/usr/bin/env python3
"""Conan recipe — pg_ivm 1.15 (Incremental View Maintenance for PostgreSQL).

pg_ivm 提供 IMMV（Incremental Materialized View）：对物化视图做增量维护，
基表发生 INSERT/UPDATE/DELETE 时不再全量刷新，只更新受影响的元组。
上游产物是一个 PGXS 扩展：

  * pg_ivm.so                    —— 扩展共享库（加载进 postgres 进程）
  * pg_ivm.control               —— 扩展控制文件（default_version = 1.15）
  * pg_ivm--*.sql                —— 基线脚本 pg_ivm--1.10.sql + 1.10→1.15 更新链

为什么配方要自举 PostgreSQL 源码（而不是 requires 已发布的 postgresql 包）
------------------------------------------------------------------------
扩展必须用 PGXS + **服务端头文件**编译，而制品仓里已发布的 postgresql/18.3
包只交付客户端面（bin/psql、lib/libpq 等）：实测该包内 include/server 与
lib/pgxs 均为空、也没有 pg_regress，无法用于编译或驱动扩展回归。因此本配方
与 archives/p/postgresql-topn/2.7.0 同源，在 tmpfs 里自举一份完整 PG 18.3
（官方源码 + HarmonyOS 适配补丁 + configure/make/make install），用它提供
pg_config/PGXS/服务端头/postgres/initdb/pg_ctl/pg_regress，供编译与真机回归。

HarmonyOS 相关要点
------------------
* PG 源码需先打 patches/0001-postgresql-harmony.patch（SysV shm 跳过、
  hmdfs 权限放宽、Unix socket 关闭），否则 postgres 在 OHOS 上起不来。
* 走 subprocess 而非 self.run()：conanbuild.sh 重新注入的 CC/CFLAGS 会污染
  PGXS 的编译探测（先例配方同因）。
* 扩展的 PG 服务端符号在 CREATE EXTENSION 时由 postgres 进程提供，链接期用
  PG_LDFLAGS 的 --unresolved-symbols=ignore-all 放行。
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, export_conandata_patches, get, patch


class PgIvmConan(ConanFile):
    name = "pg_ivm"
    version = "1.15"
    description = (
        "pg_ivm — incremental view maintenance on PostgreSQL "
        "(IMMV: materialized views refreshed incrementally)"
    )
    license = "PostgreSQL"
    homepage = "https://github.com/sraoss/pg_ivm"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    _TMPFS_ROOT = "/data/storage/el2/base/.pg_ivm-build"
    _PG_VERSION = "18.3"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _bootstrap_pgxs(self):
        """Build a full PostgreSQL server from the official source tarball.

        The full build provides pg_config + PGXS + server headers for the
        extension build, and postgres/initdb/pg_ctl/createdb/pg_regress for
        test_package to drive the upstream regression suite on the device.
        """
        pg_meta = self.conan_data["postgresql"]
        tmpfs_root = self._TMPFS_ROOT
        pg_src = os.path.join(tmpfs_root, f"postgresql-{self._PG_VERSION}")
        pg_build = os.path.join(pg_src, "aarch64-build")
        pg_install = os.path.join(pg_src, "install")
        bootstrapped_pg_config = os.path.join(
            pg_build, "src", "bin", "pg_config", "pg_config")
        bootstrapped_postgres = os.path.join(pg_install, "bin", "postgres")

        # Idempotent: the tmpfs tree persists across local rounds.
        if (os.path.isfile(bootstrapped_pg_config)
                and os.path.isfile(bootstrapped_postgres)):
            return pg_src

        os.makedirs(tmpfs_root, exist_ok=True)
        os.makedirs(pg_src, exist_ok=True)
        get(self, **pg_meta, strip_root=True, destination=pg_src)

        # Relax umask 077 -> 067 in configure wrappers: hmdfs denies the
        # 0700/077 permissions PG's generated configure scripts would create.
        # (Same in-tree rewrite as archives/a/address-standardizer/3.7.0; a
        # patches/ variant would rewrite a generated file via the patch
        # pipeline, so the rewrite stays here next to its rationale.)
        umask_fixed = 0
        configure_seen = 0
        for root, _dirs, files in os.walk(pg_src):
            for name in files:
                if name == "configure":
                    configure_seen += 1
                    cfg_path = os.path.join(root, name)
                    try:
                        with open(cfg_path, "r", encoding="utf-8",
                                  errors="surrogateescape") as fh:
                            text = fh.read()
                        new_text = text.replace("umask 077", "umask 067")
                        if new_text != text:
                            with open(cfg_path, "w", encoding="utf-8",
                                      errors="surrogateescape") as fh:
                                fh.write(new_text)
                            umask_fixed += 1
                    except OSError as exc:
                        self.output.warning(
                            f"umask rewrite skipped for {cfg_path}: {exc}")
        if configure_seen and not umask_fixed:
            self.output.warning(
                "no `umask 077` occurrence found in the PostgreSQL configure "
                "wrappers — if the upstream template changed, hmdfs may deny "
                "the generated 0700 permissions and the bootstrap will fail")
        self.output.info(
            f"umask 077->067 rewritten in {umask_fixed}/{configure_seen} "
            "configure wrappers")

        os.makedirs(pg_build, exist_ok=True)
        os.makedirs(pg_install, exist_ok=True)

        tmpfs_tmp = os.path.join(tmpfs_root, "tmp")
        os.makedirs(tmpfs_tmp, exist_ok=True)
        cc, cxx = self._compiler_executables()
        clean_env = {
            # Device toolchain paths first: the OHOS clang in
            # /data/service/hnp/bin is the toolchain this platform ships.
            "PATH": (
                os.path.dirname(cc) + ":"
                "/data/service/hnp/bin:"
                "/storage/Users/currentUser/usr/local/bin:"
                + os.environ.get("PATH", "/usr/bin:/bin")
            ),
            "HOME": os.environ.get("HOME", os.path.expanduser("~")),
            "TMPDIR": tmpfs_tmp,
            "TEMP": tmpfs_tmp,
            "TMP": tmpfs_tmp,
            "LANG": os.environ.get("LANG", "C.UTF-8"),
            "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
            "SHELL": os.environ.get("SHELL", "/bin/sh"),
            "CC": cc,
            "CXX": cxx,
        }
        for k in ("USER", "LOGNAME", "TERM"):
            v = os.environ.get(k)
            if v is not None:
                clean_env[k] = v

        patch_path = os.path.join(self.source_folder, "patches",
                                  "0001-postgresql-harmony.patch")
        if not os.path.isfile(patch_path):
            raise ConanException(
                f"HarmonyOS patch missing: {patch_path}. PostgreSQL cannot be "
                "bootstrapped without it (SysV shm / hmdfs permissions / "
                "username handling), so fail fast instead of building a "
                "server that cannot start on OHOS.")
        patch(self, base_path=pg_src, patch_file=patch_path,
              strip=1, fuzz=False)

        # Minimal, historically verified feature set: keeps the bootstrap
        # cheap and avoids pulling optional third-party libraries.
        configure_cmd = [
            os.path.join(pg_src, "configure"),
            f"--prefix={pg_install}",
            "--without-icu", "--without-readline",
            "--without-zlib", "--without-openssl",
        ]
        subprocess.run(configure_cmd, cwd=pg_build, env=clean_env, check=True)
        subprocess.run(["make", "-j1"], cwd=pg_build, env=clean_env, check=True)
        subprocess.run(["make", "install", "-j1"], cwd=pg_build,
                       env=clean_env, check=True)

        # Server headers (PGXS compiles the extension against them).
        makefile_global = os.path.join(pg_build, "src", "Makefile.global")
        install_stamp = os.path.join(pg_build, ".pgxs-headers-installed")
        if os.path.isfile(makefile_global) and not os.path.isfile(install_stamp):
            subprocess.run(
                ["make", f"-C{os.path.join('src', 'include')}",
                 "install", "-j1"],
                cwd=pg_build, env=dict(clean_env), check=True,
            )
            with open(install_stamp, "w", encoding="utf-8") as fh:
                fh.write("installed\n")

        # pgxs.mk + Makefile.shlib + config/ into the build tree: pgxs.mk
        # references $(top_builddir)/config/install-sh, which the in-tree
        # build tree expects next to the generated Makefile.global.
        self._ensure_pgxs_layout(pg_build, pg_src)
        return pg_src

    def _compiler_executables(self):
        """Compiler binaries from the Conan profile, device default as fallback.

        R33: the profile pins ``tools.build:compiler_executables`` (OHOS clang);
        reading it keeps the recipe from hardcoding a device path, while the
        platform's own toolchain location stays the fallback when the conf is
        absent (bare ``conan create`` without the ohos profile).
        """
        exes = {}
        try:
            exes = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:
            exes = {}
        cc = exes.get("c") or "/data/service/hnp/bin/clang"
        cxx = exes.get("cpp") or exes.get("cxx") or "/data/service/hnp/bin/clang++"
        return cc, cxx

    def _find_pg_config(self):
        """Locate the bootstrapped pg_config binary."""
        bootstrapped = os.path.join(
            self._TMPFS_ROOT, f"postgresql-{self._PG_VERSION}", "aarch64-build",
            "src", "bin", "pg_config", "pg_config")
        if os.path.isfile(bootstrapped):
            return bootstrapped

        found = shutil.which("pg_config")
        if found:
            return found
        for prefix in (
            os.environ.get("PG_HOME", ""),
            "/usr/local/pgsql",
            "/usr/lib/postgresql",
        ):
            if prefix:
                cand = os.path.join(prefix, "bin", "pg_config")
                if cand and os.path.isfile(cand):
                    return cand

        raise ConanException(
            "pg_config not found: the recipe bootstraps PostgreSQL "
            f"{self._PG_VERSION} from source but found no pg_config.")

    def _find_pgxs(self, pg_build, pg_src):
        """Locate pgxs.mk — prefer the *installed* PGXS tree.

        pgxs.mk resolves its siblings as ``$(dir $(PGXS))/../..``, so it must
        sit in the installed layout (``<install>/lib/pgxs/src/makefiles/``),
        next to the ``Makefile.shlib`` that every ``MODULE_big`` extension
        needs. Pointing at a build-tree copy makes that resolution land in
        ``<build>/src/``, where ``Makefile.shlib`` does not exist — observed
        on device as: "No rule to make target .../src/Makefile.shlib".
        """
        installed = os.path.join(
            self._TMPFS_ROOT, f"postgresql-{self._PG_VERSION}", "install",
            "lib", "pgxs", "src", "makefiles", "pgxs.mk")
        if os.path.isfile(installed):
            return installed

        # Fallback: assemble a usable layout inside the build tree.
        self._ensure_pgxs_layout(pg_build, pg_src)
        return os.path.join(pg_build, "src", "makefiles", "pgxs.mk")

    def _ensure_pgxs_layout(self, pg_build, pg_src):
        """Assemble the PGXS layout inside the build tree (fallback path).

        ``pgxs.mk`` is looked up relative to its own directory, so the sibling
        ``Makefile.shlib`` has to exist at ``<build>/src/Makefile.shlib`` —
        the directory ``makefiles/../..`` resolves to.
        """
        pgxs_dst = os.path.join(pg_build, "src", "makefiles")
        os.makedirs(pgxs_dst, exist_ok=True)

        # Makefile.shlib sits one level above makefiles/ in the build tree.
        shlib_dst = os.path.join(pg_build, "src", "Makefile.shlib")
        if not os.path.isfile(shlib_dst):
            shlib_src = os.path.join(pg_src, "src", "Makefile.shlib")
            if os.path.isfile(shlib_src):
                shutil.copy2(shlib_src, shlib_dst)

        for src_name in ("pgxs.mk", "Makefile.shlib"):
            _dst = os.path.join(pgxs_dst, src_name)
            if os.path.isfile(_dst):
                continue
            for _src in (
                os.path.join(pg_src, "src", "makefiles", src_name),
                os.path.join(pg_src, "install", "lib", "pgxs", "src",
                             "makefiles", src_name),
            ):
                if os.path.isfile(_src):
                    shutil.copy2(_src, _dst)
                    break

        config_dst = os.path.join(pg_build, "config")
        config_src = os.path.join(pg_src, "config")
        if os.path.isdir(config_src):
            os.makedirs(config_dst, exist_ok=True)
            for cf in os.listdir(config_src):
                _cs = os.path.join(config_src, cf)
                _cd = os.path.join(config_dst, cf)
                if os.path.isfile(_cs) and not os.path.isfile(_cd):
                    shutil.copy2(_cs, _cd)

    def generate(self):
        pass

    def build(self):
        # NOTE: the HarmonyOS patch targets the vendored PostgreSQL tree, not
        # the pg_ivm sources, so apply_conandata_patches() is deliberately not
        # called here — _bootstrap_pgxs() applies it to the PG source tree.
        pg_src = self._bootstrap_pgxs()
        pg_config = self._find_pg_config()

        pg_build = os.path.join(
            self._TMPFS_ROOT, f"postgresql-{self._PG_VERSION}", "aarch64-build")
        pgxs_path = self._find_pgxs(pg_build, pg_src)

        # Bypass Conan's self.run(): conanbuild.sh would re-inject CC/CFLAGS
        # that break PGXS's own compiler probes.
        make_env = os.environ.copy()
        cc, cxx = self._compiler_executables()
        make_env.update({
            "PATH": (
                os.path.dirname(cc) + ":"
                "/data/service/hnp/bin:"
                "/storage/Users/currentUser/usr/local/bin:"
                + os.environ.get("PATH", "/usr/bin:/bin")
            ),
            "PG_CONFIG": pg_config,
            "PGXS": pgxs_path,
            # PG server symbols stay undefined until postgres dlopen()s the
            # extension at CREATE EXTENSION time.
            "PG_LDFLAGS": (
                "-Wl,--unresolved-symbols=ignore-all "
                "-Wl,--allow-shlib-undefined"
            ),
        })
        for k in ("HOME", "LANG", "LC_ALL", "SHELL", "TMPDIR", "TEMP", "TMP"):
            v = os.environ.get(k)
            if v is not None:
                make_env[k] = v
        for k in ("USER", "LOGNAME", "TERM"):
            v = os.environ.get(k)
            if v is not None:
                make_env[k] = v

        subprocess.run(
            ["make", f"PG_CONFIG={pg_config}", f"PGXS={pgxs_path}", "-j1"],
            cwd=self.build_folder, env=make_env, check=True,
        )

    def package(self):
        # pg_ivm.so — the extension shared library.
        copy(self, "*.so", self.build_folder,
             os.path.join(self.package_folder, "lib"))

        # Control file + the SQL scripts (baseline 1.10 + 1.10→1.15 chain).
        copy(self, "pg_ivm.control", self.source_folder,
             os.path.join(self.package_folder, "extension"))
        copy(self, "pg_ivm--*.sql", self.source_folder,
             os.path.join(self.package_folder, "extension"))

        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        # Vendor the upstream tree so test_package can drive pg_regress /
        # pg_isolation_regress with the upstream oracles untouched.
        upstream_dst = os.path.join(self.package_folder, "upstream")
        for item in ("Makefile", "pg_ivm.c", "pg_ivm.h", "pg_ivm.control",
                     "createas.c", "matview.c", "ruleutils.c", "subselect.c",
                     "sql", "expected", "specs", "scripts"):
            src = os.path.join(self.source_folder, item)
            if os.path.isdir(src):
                copy(self, "*", src, os.path.join(upstream_dst, item))
            elif os.path.isfile(src):
                copy(self, item, self.source_folder, upstream_dst)

        # The upstream Makefile's DATA list and `make install` need the SQL
        # scripts present in the vendored tree (baseline 1.10 + update chain).
        copy(self, "pg_ivm--*.sql", self.source_folder, upstream_dst)

    def package_info(self):
        self.cpp_info.libs = ["pg_ivm"]
        self.cpp_info.libdirs = ["lib"]
