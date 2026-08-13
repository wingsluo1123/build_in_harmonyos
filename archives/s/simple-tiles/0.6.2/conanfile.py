#!/usr/bin/env python3
"""Conan recipe — simple-tiles 0.6.2 (waf, HarmonyOS PC / os=OHOS arch=armv8)

simple-tiles 是地图瓦片生成 C 库（propublica），waf 构建，依赖
GDAL（仓库已有 gdal 3.9.2.1 配方）与 pangocairo（本机系统库）。

构建要点：
- waf 2.0.17 与 Python 3.12 不兼容：缺 imp 模块 + posix_spawn 在 OHOS
  上不做 PATH 查找。补丁 0001 在 waf 顶部禁用 posix_spawn 并注入 imp
  shim 路径（waflib/imp.py）。
- gdal 检查改用 pkg-config（补丁 0002）：conan gdal 包的 gdal.pc 提供
  -I/-L；gdal-config 脚本的 -L 指向不存在的 build 目录。
- pangocairo 来自本机系统库（/usr/local/lib），pkg-config 已具备。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SimpleTilesConan(ConanFile):
    name = "simple-tiles"
    version = "0.6.2"
    description = "Simple tile generation for maps (C library)"
    license = "LGPL-2.1"
    homepage = "https://github.com/propublica/simple-tiles"
    url = "https://github.com/propublica/simple-tiles"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gdal/3.9.2.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Python 3.12 imp shim（waf 2.0.17 仍 import imp）
        shim = os.path.join(self.source_folder, "imp.py")
        with open(shim, "w") as f:
            f.write(
                '"""Minimal imp shim for Python 3.12+ (waf 2.0.17)."""\n'
                "import types\n"
                "def new_module(name):\n"
                "    return types.ModuleType(name)\n"
            )
        waflib_dir = os.path.join(self.source_folder, "waflib")
        if os.path.isdir(waflib_dir):
            copy(self, "imp.py", src=self.source_folder, dst=waflib_dir)
        else:
            # waf 首次运行才解压 waflib 到 .waf3-*；源码树无 waflib 时，
            # 由 build() 在解压后注入（见 _prepare_waflib）。
            self._waflib_needs_inject = True

    def _prepare_waflib(self):
        """waf 运行后把 imp.py 注入解压出的 waflib 目录（若源码树无）。"""
        for d in os.listdir(self.source_folder):
            if d.startswith(".waf3-"):
                waflib = os.path.join(self.source_folder, d, "waflib")
                shim = os.path.join(self.source_folder, "imp.py")
                if os.path.isdir(waflib) and os.path.isfile(shim):
                    copy(self, "imp.py", src=self.source_folder, dst=waflib)

    def _env(self):
        gdal_pkg = self.dependencies["gdal"].package_folder
        # self.run() 的 env 参数只接受 env-file 名列表；直接写入 os.environ
        #（参照 openblas 0.3.28 先例）。
        pkg_paths = [
            "/storage/Users/currentUser/usr/local/lib/pkgconfig",  # pangocairo 系统库
            os.path.join(gdal_pkg, "lib", "pkgconfig"),
        ]
        os.environ["PKG_CONFIG_PATH"] = os.pathsep.join(
            p for p in pkg_paths if p)
        os.environ["PATH"] = os.pathsep.join(
            [os.path.join(gdal_pkg, "bin")] + os.environ.get("PATH", "").split(os.pathsep))
        os.environ["CFLAGS"] = "-I" + os.path.join(gdal_pkg, "include")
        os.environ["CPPFLAGS"] = os.environ["CFLAGS"]
        os.environ["LDFLAGS"] = "-L/lib -L" + os.path.join(gdal_pkg, "lib")

    def build(self):
        apply_conandata_patches(self)
        self._env()
        waf = os.path.join(self.source_folder, "waf")
        if not os.path.isfile(waf):
            raise ConanException("waf script not found in source")
        self.run('python3 "%s" configure' % waf, cwd=self.source_folder)
        self._prepare_waflib()
        self.run('python3 "%s" build' % waf, cwd=self.source_folder)

    def package(self):
        # waf install 到 staging；直接收集产物
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        for f in ("libsimple-tiles.so", "libsimple-tiles.a"):
            src = os.path.join(self.source_folder, "build", f)
            if os.path.isfile(src):
                copy(self, f, src=os.path.dirname(src),
                     dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include", "simple-tiles"))

    def package_info(self):
        self.cpp_info.libs = ["simple-tiles"]
        self.cpp_info.includedirs = [os.path.join("include", "simple-tiles")]
        self.cpp_info.system_libs = ["m"]
        # simple-tiles 头文件（types.h）直接 #include <ogr_api.h>/<gdal.h>，
        # 消费者编译需 GDAL 的 include 传递（无 components 包用 pkg::pkg 引用，
        # 同 coin-osi 引用 coin-utils 先例）。
        self.cpp_info.requires = ["gdal::gdal"]
        # 头文件还传递依赖系统 pangocairo 栈（cairo/pango/glib/harfbuzz）。
        # 用 pkg-config 动态解析全部 -I 路径，避免逐个硬编码系统目录。
        try:
            import subprocess
            env = dict(os.environ)
            env["PKG_CONFIG_PATH"] = os.pathsep.join(
                p for p in ("/storage/Users/currentUser/usr/local/lib/pkgconfig",
                            env.get("PKG_CONFIG_PATH", "")) if p)
            pkgconfig = "/data/service/hnp/bin/pkg-config"
            if not os.path.isfile(pkgconfig):
                pkgconfig = "pkg-config"
            out = subprocess.run(
                [pkgconfig, "--cflags", "pangocairo"],
                capture_output=True, text=True, env=env, timeout=30).stdout
            for flag in out.split():
                if flag.startswith("-I"):
                    inc = flag[2:]
                    if os.path.isdir(inc):
                        self.cpp_info.includedirs.append(inc)
        except Exception:
            pass
        self.cpp_info.system_libs.extend(
            ["pangocairo-1.0", "pango-1.0", "cairo", "gobject-2.0", "glib-2.0"])
        # 系统 pangocairo 栈库位于 /usr/local/lib，需加入链接搜索路径
        sys_lib = "/storage/Users/currentUser/usr/local/lib"
        if os.path.isdir(sys_lib):
            self.cpp_info.libdirs.append(sys_lib)
        # 运行时也需系统 pangocairo 栈库（libsimple-tiles.so 动态符号解析）
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", sys_lib)
