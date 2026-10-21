#!/usr/bin/env python3
"""Conan test_package for gupnp-igd 1.6.0 — Conan L1 official test.

Consumer verification (real-world usage of a pkg-config library):
  1. build(): pkg-config probes the package (gupnp-igd-1.6 --modversion /
     --variable / --cflags / --libs) — exactly how a downstream
     autotools/meson consumer discovers the library — then compiles and
     links test_gupnp_igd.c with the probed flags (cpp_info fallback when
     pkg-config is unavailable). Static-glib tokens coming from the
     transitive .pc closure are stripped (single GObject copy doctrine).
  2. test(): runs the binary (wrapped in bash because the OHOS mksh cannot
     exec ELF binaries directly) with an explicitly assembled
     LD_LIBRARY_PATH. Same family approach as gssdp 1.6.6 / gupnp 1.6.10.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import cross_building

# glib static-lib tokens that must NEVER reach the test link command line
# (single-copy GObject doctrine — see the recipe and gssdp 1.6.6 notes).
GLIB_STATIC_TOKENS = {
    "-lglib-2.0", "-lgobject-2.0", "-lgio-2.0", "-lgmodule-2.0",
    "-lgthread-2.0", "-lffi", "-lintl",
}


class GupnpIgdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # 显式列出 generators 会替换 conan 默认集，必须带上 VirtualRunEnv /
    # VirtualBuildEnv：漏了它们 test() 里 env="conanrun" 就拿不到 conanrun
    # 环境的 LD_LIBRARY_PATH（gssdp/libsoup3/gupnp 同款实撞）。
    # PkgConfigDeps 为下面的 pkg-config 探测生成 .pc 文件。
    generators = "PkgConfigDeps", "VirtualRunEnv", "VirtualBuildEnv"

    # pkg-config 模块名（上游 filebase，与 libgupnp-igd/meson.build 一致；
    # 注意不是旧系列的 gupnp-igd-1.0）
    PC_NAME = "gupnp-igd-1.6"

    def requirements(self):
        # 传递依赖必须显式声明：pkg-config Requires 闭包里的模块（soup/
        # gssdp/gupnp/xml2/glib）需要各自的 .pc，且运行时 NEEDED 链需要各
        # package_folder 拼 LD_LIBRARY_PATH。gupnp-igd 公共头 include
        # glib/gobject 头；典型消费者还会编译 gupnp/gssdp 头。
        self.requires(self.tested_reference_str)
        self.requires("glib2/2.88.0")
        self.requires("libsoup3/3.6.5-r1")
        self.requires("gssdp/1.6.6")
        self.requires("gupnp/1.6.10")
        self.requires("libxml2/2.15.3.1")

    # ------------------------------------------------------------------ #

    def _pkgconfig_exe(self):
        exe = shutil.which("pkg-config",
                           path=os.environ.get("PATH", os.defpath))
        if not exe:
            for cand in ("/data/service/hnp/bin/pkg-config",
                         "/usr/bin/pkg-config",
                         "/storage/Users/currentUser/.harmonybrew/bin/pkg-config"):
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    exe = cand
                    break
        return exe

    def _pkgconfig(self, what):
        """跑 pkg-config（PKG_CONFIG_PATH 指向 generators 目录）。取不到
        返回空串，由调用方回退 cpp_info 拼装。"""
        exe = self._pkgconfig_exe()
        if not exe:
            return ""
        env = dict(os.environ)
        env["PKG_CONFIG_PATH"] = os.pathsep.join(
            [self.generators_folder] +
            [p for p in env.get("PKG_CONFIG_PATH", "").split(os.pathsep)
             if p])
        try:
            out = subprocess.run([exe, what, self.PC_NAME],
                                 capture_output=True, text=True, env=env,
                                 timeout=60)
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
        return ""

    def _collect_include_dirs(self):
        """被测包 + 全部传递依赖的头目录（绝对路径、去重、只留存在项）。

        被测包 recipe 的 package_info 已把 glib2/gupnp/gssdp/soup/libxml2
        的 include 目录 append 进 cpp_info.includedirs（conan 2.29 的
        CMakeDeps 对传递依赖生成空数据的补偿），所以遍历被测包视图即可
        拿到完整头路径（含 glib-2.0 嵌套目录与 lib/glib-2.0/include）。
        """
        seen, out = set(), []
        for _r, _d in self.dependencies.items():
            base = getattr(_d, "package_folder", None)
            if not base:
                continue
            for inc in (_d.cpp_info.includedirs or []):
                p = inc if os.path.isabs(inc) else os.path.join(base, inc)
                if p and os.path.isdir(p) and p not in seen:
                    seen.add(p)
                    out.append(p)
        return out

    def _collect_lib_dirs(self):
        """全部依赖的 lib 目录（-L 与 rpath 用，绝对路径、去重、只留存在项）。"""
        seen, out = set(), []
        for _r, _d in self.dependencies.items():
            base = getattr(_d, "package_folder", None)
            for libdir in (_d.cpp_info.libdirs or []):
                p = libdir if os.path.isabs(libdir) else \
                    (os.path.join(base, libdir) if base else None)
                if p and os.path.isdir(p) and p not in seen:
                    seen.add(p)
                    out.append(p)
        return out

    # ------------------------------------------------------------------ #

    def build(self):
        # ── 阶段 1：pkg-config 探测（真实下游消费方姿势）──────────────
        modversion = self._pkgconfig("--modversion")
        if modversion:
            self.output.info(
                "pkg-config probe OK: {} --modversion = {}".format(
                    self.PC_NAME, modversion))
        else:
            self.output.warning(
                "pkg-config --modversion probe failed for {} "
                "(no pkg-config or .pc missing); cpp_info fallback".format(
                    self.PC_NAME))
        prefix = self._pkgconfig("--variable=prefix")
        if prefix:
            self.output.info(
                "pkg-config probe OK: {} --variable=prefix = {}".format(
                    self.PC_NAME, prefix))

        # ── 阶段 2：编译 + 链接 ────────────────────────────────────────
        # cflags：pkg-config 优先（被测包 .pc 的 Cflags），被测包/传递依赖
        # cpp_info 的 include 目录兜底合并（glib 头不在被测包 .pc 的闭包里，
        # brial 先例：.pc 未必声明上游 include 时防漏）。
        cflags = []
        pc_cflags = self._pkgconfig("--cflags")
        if pc_cflags:
            cflags.extend(pc_cflags.split())
        for p in self._collect_include_dirs():
            flag = "-I{}".format(p)
            if flag not in cflags:
                cflags.append(flag)

        # libs：pkg-config 优先（Requires 闭包带出 soup/gssdp/gupnp/xml2
        # 的 -l），静态 glib token 一律剔除（单 GObject 副本）；取不到则
        # 只链被测库本体——g_* 符号经 libgupnp-igd-1.6.so 的 NEEDED 链
        # （gupnp→soup）解析，绝不能显式链静态 glib。
        pc_libs = self._pkgconfig("--libs")
        if pc_libs:
            libs = [t for t in pc_libs.split()
                    if t not in GLIB_STATIC_TOKENS]
        else:
            libs = ["-lgupnp-igd-1.6"]

        libdirs = self._collect_lib_dirs()
        # musl dynlink 只认 legacy DT_RPATH，不认 lld 默认的 DT_RUNPATH：
        # --disable-new-dtags 强制 DT_RPATH，测试二进制免 LD_LIBRARY_PATH
        # 也能跑（gupnp/gssdp 先例同款）。
        link = ["-L{}".format(p) for p in libdirs] + libs + \
               ["-Wl,--disable-new-dtags"] + \
               ["-Wl,-rpath,{}".format(p) for p in libdirs]

        # 编译器：profile conf 优先（R33：不裸依赖 shell 环境），CC 环境变量
        # （VirtualBuildEnv 注入）次之，clang 兜底。
        cc = None
        try:
            compilers = self.conf.get("tools.build:compiler_executables",
                                      check_type=dict)
            cc = (compilers or {}).get("c")
        except Exception:
            cc = None
        cc = cc or os.environ.get("CC") or "clang"

        src = os.path.join(self.source_folder, "test_gupnp_igd.c")
        cmd = "{} {} {} -o test_gupnp_igd {}".format(
            cc, " ".join(cflags), src, " ".join(link))
        self.output.info("compile: {}".format(cmd))
        self.run(cmd)

    def test(self):
        if cross_building(self):
            self.output.info(
                "cross-building: compile+link only (OHOS binaries are not "
                "runnable on the build host)")
            return
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries; wrap with bash.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or \
            "/data/service/hnp/bin/bash"
        # 显式拼 LD_LIBRARY_PATH（不能只依赖 conanrun）：覆盖被测包与全部
        # 传递依赖的 lib 目录（gssdp/gupnp 先例——conanrunenv 的 libdirs
        # 对部分包为空）。
        ldpath = os.pathsep.join(self._collect_lib_dirs())
        self.run(
            "{} -c 'export LD_LIBRARY_PATH=\"{}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; ./test_gupnp_igd'"
            .format(bash, ldpath),
            cwd=self.build_folder, env="conanrun")
