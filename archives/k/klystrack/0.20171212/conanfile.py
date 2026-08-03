#!/usr/bin/env python3
"""Conan recipe for klystrack 0.20171212 — C chiptune tracker (Makefile build).

klystrack 是 C 写的 chiptune tracker（C64/NES/Amiga 风音乐），用 Makefile 构建
（非 configure autotools），依赖 SDL2 + SDL2_image 图形库。
上游无自动化测试套件（chiptune tracker 纯音频应用）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class KlystrackConan(ConanFile):
    name = "klystrack"
    version = "0.20171212"
    description = "Chiptune tracker for making C64/NES/Amiga-style music"
    license = "MIT"
    homepage = "https://kometbomb.github.io/klystrack/"
    url = "https://github.com/kometbomb/klystrack"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    # aireview P2: 接入 Conan 2.x 交叉编译工具链机制（VirtualBuildEnv + env=conanbuild）
    # 避依赖 CI 环境 PATH 巧合性正确（release worker 可能解析到错误架构编译器）
    generators = "VirtualBuildEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # SDL2 制品仓已就绪 (resolve-deps ✅)，包名小写 sdl2
        self.requires("sdl2/2.30.10")
        # SDL2_image/2.8.0 未发布到制品仓（L0i: NOT in registry, R36），
        # 不能声明依赖否则 conan create 解析失败（同 groonga rapidjson 处理）。
        # 上游 Makefile 对 SDL2_image 为可选（Windows DLL 预打包用），Linux 构建不强制

    def layout(self):
        basic_layout(self)
        # Conan 2.x basic_layout 默认 source_folder = build folder，但 Makefile 在解包后源码根
        # 显式指定 source folder = 解包根（含 Makefile）
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # Makefile-based build, no toolchain needed; keep for Conan 2.x G1 gate
        pass

    def _find_make_dir(self):
        """定位含 Makefile 的源码根目录（build() 与 package() 共用，保持一致）。

        源码经 strip_root=True 解包到 source_folder，Makefile 在
        source_folder/klystrack/ 子目录（上游 tarball 内还有一层 klystrack）。
        遍历到第一个含 Makefile 的目录即返回（避免 and/or 优先级陷阱）。
        """
        if os.path.isfile(os.path.join(self.source_folder, "Makefile")):
            return self.source_folder
        # 源码在 source_folder，os.walk 扫 source_folder 而非 build_folder
        for root, dirs, files in os.walk(self.source_folder):
            if "Makefile" in files:
                return root
        raise ConanException(f"Makefile not found under {self.source_folder}")

    def build(self):
        # SDL2 头路径通过 CPPFLAGS 注入（Conan 包 package_folder）
        # SDL2_image/2.8.0 未发布到制品仓未声明依赖，不注入其路径
        # CI 报 'SDL.h' file not found: SDL2 包头在 include/SDL2/SDL.h（非根 include），
        # klystrack 源码用 #include "SDL.h"，需注入 SDL2 子目录让根 include 下也能找到
        # CI 报 'macros.h' file not found: klystrack 源码内部头在 src/ 下，需注入源码根
        sdl2_inc = os.path.join(self.dependencies["sdl2"].package_folder, "include")
        sdl2_inc_sub = os.path.join(sdl2_inc, "SDL2")
        sdl2_lib = os.path.join(self.dependencies["sdl2"].package_folder, "lib")
        src_inc = os.path.join(self.source_folder, "src")
        cppflags = f"-I{sdl2_inc} -I{sdl2_inc_sub} -I{src_inc}"
        ldflags = f"-L{sdl2_lib}"
        make_dir = self._find_make_dir()
        # CI 根因: make[1]: *** ../klystron: No such file or directory. Stop.
        # Makefile build target 依赖 ../klystron 目录但上游 archive 快照缺该子项目
        # 建 ../klystron symlink 指向源码根（klystrack 自身含 klystron 所需源文件）
        klystron_link = os.path.join(os.path.dirname(make_dir), "klystron")
        # aireview Medium: os.path.exists 跟随符号链接致断开符号链接返 False 重入分支残留
        # 改 os.path.lexists 检测断开符号链接（lexists 不跟随，断开链接返 True）
        if not os.path.lexists(klystron_link):
            try:
                os.symlink(make_dir, klystron_link)
            except FileExistsError:
                # 符号链接已存在，单独 pass（aireview P3: 避静默失败）
                pass
            except OSError as e:
                # aireview Medium: symlink 失败改 raise ConanException 非继续执行（避 make 模糊失败排查成本）
                raise ConanException(
                    f"Failed to create symlink {klystron_link} -> {make_dir}: {e}. "
                    f"The Makefile build target requires ../klystron to exist."
                ) from e
        # aireview P2: 删 CC Python 侧解析和命令行注入，依赖 conanbuild 环境自动提供正确交叉编译器
        # （os.environ.get("CC") 读宿主机环境非 conanbuild 子进程，覆盖 conanbuild 设的完整路径）
        # CI 根因: omake[247]: mkdir: Resource temporarily unavailable → Error 127 → 247 层递归 make Error 2
        # klystrack Makefile build target 行 129/130 递归调 make -C klystron + make all 致进程/句柄耗尽（EAGAIN）
        # 非并发问题（-j1 无效），真根因是递归本身 → 改 build() 不调 'make build' 避递归
        # 分步执行 Makefile build target 等价步骤：① touch src/version ② make -C klystron ③ make all
        prefix = os.path.join(self.build_folder, "staging")
        common_flags = f'CFG=release CFLAGS+="{cppflags}" LDFLAGS+="{ldflags}" PREFIX={prefix}'
        # ① touch src/version（build target 第一步，行 128）
        self.run('touch src/version', cwd=make_dir, env="conanbuild")
        # ② make -C klystron CFG=release（行 129 等价，单独跑避递归 build target）
        klystron_dir = os.path.join(os.path.dirname(make_dir), "klystron")
        self.run(f'make -C "{klystron_dir}" {common_flags}', cwd=make_dir, env="conanbuild")
        # ③ make all CFG=release（行 130 等价，单独跑避递归 build target）
        self.run(f'make -j1 all {common_flags}', cwd=make_dir, env="conanbuild")

    def package(self):
        # make install 安装到 staging（复用 _find_make_dir 定位源码根）
        make_dir = self._find_make_dir()
        self.run(
            f'make install CFG=release '
            f'PREFIX={os.path.join(self.build_folder, "staging")}',
            cwd=make_dir, env="conanbuild"
        )
        # copy staging 到 package_folder
        copy(self, "*", src=os.path.join(self.build_folder, "staging"),
             dst=self.package_folder)

    def package_info(self):
        # klystrack 是 CLI 二进制（bin/klystrack），非链接型 lib
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
