#!/usr/bin/env python3
"""Conan recipe for profiled 1.0.13 — Sailfish/Nemo profile settings daemon (OHOS aarch64).

Upstream: https://github.com/sailfishos/profiled (tag 1.0.13 -> d3d2b21a5)
Build:    手写 Makefile（非 autotools/cmake），pkg-config 取 dbus-1 + glib-2.0

产物：
  lib/  libprofile.so.0 + libprofile.so + libprofile.a（D-Bus 客户端库）
        lib/pkgconfig/profile.pc
  bin/  profiled（守护进程，D-Bus 名 com.nokia.profiled）
        profileclient（命令行：查询/切换 profile）
        profile-tracker（变更跟踪调试工具）
  include/profiled/{libprofile.h,profileval.h}
  share/dbus-1/services/com.nokia.profiled.service（会话总线激活文件）

OHOS 适配要点（每条都有实测结论，详见 notes.md）：
 1. dbus-gmain 是 git submodule（mode 160000），GitHub 归档包不含内容 ->
    按 conandata 单独取 sailfishos-mirror/dbus-glib@d42176ae 的
    dbus-gmain.{c,h} 放回 dbus-gmain/ 后再编译（4 个目标都编入该对象）。
 2. 上游 VERS 取自 debian/changelog 首行（仍停在 1.0.12）-> 命令行覆盖
    VERS=1.0.13，保证 profile.pc 与包版本一致。
 3. dbus 依赖包不提供 dbus-1.pc，且 pkg-config 名称是 "dbus"；上游 Makefile
    写死 `pkg-config --cflags dbus-1 glib-2.0` -> generate() 在 conan 生成的
    .pc 目录旁补一份 dbus-1.pc。
 4. 上游 install 规则依赖 install(1)，OHOS 侧无该命令 -> package() 自行落盘。
 5. unique.c 使用 GCC 嵌套函数（clang 不支持）-> patches/0001 移到文件作用域。
 6. 守护进程运行期读 $HOME/.profiled（可写），静态配置目录 /etc/profiled
    缺省时使用内建 profile（general/meeting/outdoors/silent）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
    save,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class ProfiledConan(ConanFile):
    name = "profiled"
    version = "1.0.13"
    description = ("Sailfish/Nemo profile settings daemon: libprofile client library, "
                   "profiled D-Bus service and profileclient/profile-tracker tools")
    license = "BSD-2-Clause"
    homepage = "https://github.com/sailfishos/profiled"
    url = "https://github.com/sailfishos/profiled"
    topics = ("dbus", "profile", "settings", "sailfish", "daemon")

    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libprofile.h 公开 #include <dbus/dbus.h>：shared-library 默认不向消费方
        # 透传依赖头文件，这里显式开启（否则 CMakeDeps 不给 dbus 的 include 路径）
        self.requires("dbus/1.14.10.2", transitive_headers=True)
        self.requires("glib/2.88.3")

    def build_requirements(self):
        # 上游 Makefile 用 pkg-config 取 dbus-1 / glib-2.0 的编译与链接参数
        self.tool_requires("pkgconf/3.0.6")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"profiled supports Linux and OHOS only, got {self.settings.os}"
            )

    # ------------------------------------------------------------------ source
    def source(self):
        src = self.conan_data["sources"][self.version]
        get(self, url=src["url"], sha256=src["sha256"], strip_root=True)

        # dbus-gmain 子模块内容（归档包不含），解到临时目录后只取两个源文件
        tmp = os.path.join(self.source_folder, ".dbus-gmain-src")
        get(self, url=src["dbus_gmain_url"], sha256=src["dbus_gmain_sha256"],
            destination=tmp, strip_root=True)
        copy(self, "dbus-gmain.*", src=tmp,
             dst=os.path.join(self.source_folder, "dbus-gmain"))
        rmdir(self, tmp)

    # ---------------------------------------------------------------- generate
    def generate(self):
        PkgConfigDeps(self).generate()
        self._write_dbus_pc()

    def _write_dbus_pc(self):
        """dbus 包的 pkg-config 名是 dbus，上游只要 dbus-1；补一份同义 .pc。

        dbus 在本仓是静态库（R26），链接时需要 pthread/rt。
        """
        dep = self.dependencies["dbus"]
        content = (
            f"prefix={dep.package_folder}\n"
            "libdir=${prefix}/lib\n"
            "includedir=${prefix}/include/dbus-1.0\n"
            "\n"
            "Name: dbus-1\n"
            "Description: D-Bus message bus client library (conan static build)\n"
            f"Version: {dep.ref.version}\n"
            "Libs: -L${libdir} -ldbus-1 -lpthread -lrt\n"
            "Cflags: -I${includedir}\n"
        )
        save(self, os.path.join(self.generators_folder, "dbus-1.pc"), content)

    def _toolchain_value(self, key, default):
        conf = self.conf.get("tools.build:compiler_executables",
                             default={}, check_type=dict) or {}
        return conf.get(key) or default

    # ------------------------------------------------------------------- build
    def build(self):
        apply_conandata_patches(self)
        cc = self._toolchain_value("c", "clang")
        ar = self._toolchain_value("ar", shutil.which("llvm-ar") or "ar")

        env = Environment()
        env.define("PKG_CONFIG_PATH", self.generators_folder)
        with env.vars(self).apply():
            self.run(
                f'make -j1 VERS={self.version} CC="{cc}" AR="{ar}" build',
                cwd=self.source_folder,
            )
            # profile.pc 由 Makefile 模板渲染（@VERS@/@PREFIX@ 等），
            # 用包目录作为 prefix，与 conan 生成的 .pc 语义一致
            # INCDIR 覆盖为 <pkg>/include：上游把头文件装到 include/profiled，
            # 消费方按 <profiled/libprofile.h> 引用，因此 .pc 的 -I 必须指向父目录
            self.run(
                f'make VERS={self.version} PREFIX="{self.package_folder}" '
                f'INCDIR="{os.path.join(self.package_folder, "include")}" profile.pc',
                cwd=self.source_folder,
            )

    # ----------------------------------------------------------------- package
    def package(self):
        pkg = self.package_folder
        src = self.source_folder

        for header in ("libprofile.h", "profileval.h"):
            copy(self, header, src=src,
                 dst=os.path.join(pkg, "include", "profiled"), keep_path=False)

        copy(self, "libprofile.so.0", src=src, dst=os.path.join(pkg, "lib"),
             keep_path=False)
        copy(self, "libprofile.a", src=src, dst=os.path.join(pkg, "lib"),
             keep_path=False)

        lib_dir = os.path.join(pkg, "lib")
        link = os.path.join(lib_dir, "libprofile.so")
        if os.path.lexists(link):
            os.unlink(link)
        os.symlink("libprofile.so.0", link)

        for tool in ("profiled", "profileclient", "profile-tracker"):
            copy(self, tool, src=src, dst=os.path.join(pkg, "bin"), keep_path=False)

        copy(self, "profile.pc", src=src,
             dst=os.path.join(pkg, "lib", "pkgconfig"), keep_path=False)
        copy(self, "com.nokia.profiled.service", src=src,
             dst=os.path.join(pkg, "share", "dbus-1", "services"), keep_path=False)
        copy(self, "LICENSE", src=src, dst=os.path.join(pkg, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "profile")
        self.cpp_info.libs = ["profile"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
