#!/usr/bin/env python3
"""Conan recipe — Dune 3.17.0 (OCaml build system)

Dune uses its own bootstrap mechanism:
  1. ocaml boot/bootstrap.ml  → builds _boot/dune.exe
  2. make release             → builds @install with --profile dune-bootstrap

Patches:
  - boot/duneboot.ml: prefer bytecode over .opt native binaries (OHOS security)
  - src/dune_rules/which.ml: don't prefer .opt variants in compiler detection
  - vendor/spawn/src/spawn_stubs.c: guard pthread_setcancelstate for OHOS
  - dune-project: add (version 3.17.0)
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class DuneConan(ConanFile):
    name = "dune"
    version = "3.17.0"
    description = "Fast, portable, and opinionated build system for OCaml"
    license = "MIT"
    homepage = "https://github.com/ocaml/dune"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # OCaml 4.14.1.1 已在制品仓（PR #3767 合入），dune 自举需要 ocaml 编译器
        self.tool_requires("ocaml/4.14.1.1.2")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R8 合规：功能探测 pthread_setcancelstate（替代平台宏 __OHOS__）。
        # vendor/spawn 的 spawn_stubs.c 用 HAVE_PTHREAD_SETCANCELSTATE 宏守卫，
        # 编译小测试程序检测该函数是否可用（OHOS 未实现则不定义宏）。
        probe = os.path.join(self.source_folder, "_spawn_probe.c")
        with open(probe, "w") as f:
            f.write("#include <pthread.h>\nint main(void){int s;pthread_setcancelstate(PTHREAD_CANCEL_DISABLE,&s);return 0;}\n")
        probe_obj = os.path.join(self.source_folder, "_spawn_probe.o")
        cc = "clang"
        # -Werror=implicit-function-declaration：OHOS 上 pthread_setcancelstate 未声明，
        # 隐式声明会使编译失败（正确判定 NOT available），而非仅 warning 误判可用
        probe_cmd = f"{cc} -Werror=implicit-function-declaration -c {probe} -o {probe_obj}"
        self.run(probe_cmd, cwd=self.source_folder, env="conanbuild", ignore_errors=True)
        have_pthread = os.path.isfile(probe_obj)
        os.remove(probe) if os.path.isfile(probe) else None
        os.remove(probe_obj) if os.path.isfile(probe_obj) else None
        if have_pthread:
            self.output.info("pthread_setcancelstate available - enabling HAVE_PTHREAD_SETCANCELSTATE")
            os.environ["CFLAGS"] = os.environ.get("CFLAGS", "") + " -DHAVE_PTHREAD_SETCANCELSTATE"
        else:
            self.output.info("pthread_setcancelstate NOT available (OHOS) - feature macro disabled")
        # OCaml 来自 tool_requires（制品仓），但其配方未声明 bindirs，
        # conanbuild 环境不会自动注入 bin——显式注入 ocaml bin 到 PATH
        # （ocaml 是 build 依赖 tool_requires，须用 dependencies.build 访问）
        ocaml_dep = self.dependencies.build["ocaml"]
        ocaml_bin = os.path.join(ocaml_dep.package_folder, "bin")
        os.environ["PATH"] = ocaml_bin + os.pathsep + os.environ.get("PATH", "")
        self.output.info(f"ocaml bin 注入 PATH: {ocaml_bin}")
        # Step 1: Bootstrap - build _boot/dune.exe
        # env="conanbuild" 注入 tool_requires（ocaml）的 bin 到 PATH，bootstrap 才能找到 ocaml
        # 制品仓 ocaml 包可能缺 `ocaml` toplevel 命令（CI 构建环境差异），
        # 缺失时改用 ocamlc 编译 bootstrap.ml 为字节码 + ocamlrun 运行（不依赖 toplevel）
        if os.path.isfile(os.path.join(ocaml_bin, "ocaml")):
            self.run("ocaml boot/bootstrap.ml", cwd=self.source_folder, env="conanbuild")
        else:
            self.output.info("ocaml toplevel 缺失，改用 ocamlc 编译 bootstrap + ocamlrun 运行")
            self.run("ocamlc -o boot/bootstrap.exe boot/bootstrap.ml", cwd=self.source_folder, env="conanbuild")
            self.run("ocamlrun boot/bootstrap.exe", cwd=self.source_folder, env="conanbuild")
        # Step 2: Release build
        self.run("make release", cwd=self.source_folder, env="conanbuild")

    def package(self):
        # Copy the built binary and install artifacts
        copy(self, "dune.exe",
             src=os.path.join(self.source_folder, "_build", "default", "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        # Copy install tree (doc, lib, man, share)
        copy(self, "*",
             src=os.path.join(self.source_folder, "_build", "install", "default"),
             dst=self.package_folder, keep_path=True, excludes=["bin/*"])
        # Ensure bin/dune is the actual binary (not a symlink)
        bin_dune = os.path.join(self.package_folder, "bin", "dune")
        bin_dune_exe = os.path.join(self.package_folder, "bin", "dune.exe")
        if os.path.islink(bin_dune):
            os.unlink(bin_dune)
        if os.path.exists(bin_dune_exe):
            os.rename(bin_dune_exe, bin_dune)

    def package_info(self):
        self.cpp_info.libs = []
        # Dune is a build tool, expose it via bindirs
        self.cpp_info.bindirs = ["bin"]
