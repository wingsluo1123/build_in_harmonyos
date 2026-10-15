#!/usr/bin/env python3
"""Conan recipe for musl-nscd 1.1.1 — NSCD 协议实现（musl 的 nscd 守护进程）。

上游构建系统是 musl 风格的手写 configure（sh）+ 顶层 Makefile，产出：

    sbin/nscd                   守护进程（NSCD 协议服务端，按 nsswitch.conf 装载 NSS 模块）
    include/nss.h               NSS 模块 API 头（消费者可见）
    share/man/man8/musl-nscd.8  手册页

适配 HarmonyOS（OHOS / aarch64，libc 为 musl 派生，原生编译而非交叉编译）。
"""
import os

from conan import ConanFile
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MuslNscdConan(ConanFile):
    name = "musl-nscd"
    version = "1.1.1"
    description = ("musl-nscd — NSCD 协议实现，为 musl 提供基于 NSS 模块的 "
                   "passwd/group 数据库缓存守护进程")
    license = "MIT"
    homepage = "https://github.com/pikhq/musl-nscd"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # R38: 产物是命令行/守护进程可执行文件（sbin/nscd），不是库
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml", "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        # 上游是 in-source 构建：configure 在源码目录写 config.mak，make 在源码目录
        # 生成 obj/。因此把 build 目录与 source 目录对齐，避免 Makefile 找不到。
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33：上游 configure/Makefile 不识别 Conan Toolchain，无法由构建助手自动
        # 注入编译器（Makefile 直接用 $(CC)，自研 configure 只认 CC= 变量）。因此
        # 编译器路径一律从 Conan conf 取并写进 conanbuild env 脚本 —— 禁止依赖
        # shell 里恰好存在的 $CC/$CFLAGS（release worker 上可能为空，导致静默走错
        # 编译器或编译失败）。
        build_env = VirtualBuildEnv(self)
        build_env.generate()

        env = Environment()
        env.define("CC", self._toolchain("c", "clang"))
        env.define("AR", self._toolchain("ar", "llvm-ar"))
        env.define("RANLIB", self._toolchain("ranlib", "llvm-ranlib"))
        env.vars(self, scope="build").save_script("musl_nscd_toolchain")

    def _toolchain(self, name, default):
        # tools.build:compiler_executables 是 dict 型 conf（形如 {"c": ..., "ar": ...}），
        # 不能用 `:c` 子键直接取 —— 未声明的 conf 名会让 conf.get() 直接抛异常。
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return compilers.get(name, default) if compilers else default

    def build(self):
        apply_conandata_patches(self)

        # R1：参数最小化 —— 自研 configure 只需要 --prefix；--prefix=/ 让
        # sbindir/include/mandir 落在包根下，安装期再用 DESTDIR 隔离到
        # package_folder，从而精确控制打包内容。
        # R9：-j1，并行 make 在 HMDFS 上会踩 jobserver fifo EPERM。
        self.run(f"sh ./configure --prefix=/ CC={self._toolchain('c', 'clang')}",
                 cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

        # ── 上游验证（上游无 make check，见下）──
        # 上游 v1.1.1 没有任何正式测试套件：Makefile 无 check/test 目标，无 tests/
        # 目录，无 ctest/pytest 注册（清点证据见 1.1.1/notes.md）。
        # 上游唯一的自检设施是 port/*.c 这些 -DTEST 编译探针：Makefile 的
        # obj/test/% 规则编译它们，tools/gen_config.sh 再据此生成
        # obj/include/config.h 的 HAVE_PW_PASSWD / HAVE_PW_GECOS / HAVE_GR_PASSWD
        # 宏，决定协议序列化时是否带上对应字段。探针编译失败会被 Makefile 静默
        # 写成空文件（`|| cat </dev/null >$@`），宏随之退化为 undef 而不报错。
        # 这里校验「探针产物」与「生成的宏」严格一致，确保结构体字段探测真的在
        # 本平台跑过，而不是静默退化。
        self.run(
            'set -e; '
            'test -s obj/include/config.h; '
            'for f in obj/test/port/*; do '
            'n=$(basename "$f" | tr a-z A-Z); '
            'if [ -s "$f" ]; then grep -q "^#define HAVE_$n 1$" obj/include/config.h; '
            'else grep -q "^#undef HAVE_$n$" obj/include/config.h; fi; '
            'done',
            cwd=self.source_folder,
        )

    def package(self):
        self.run(f"make install DESTDIR={self.package_folder}", cwd=self.source_folder)
        copy(self, "COPYRIGHT", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["sbin"]
        self.cpp_info.includedirs = ["include"]
        # 本包不产出库文件，显式声明空 libdirs 避免消费者侧生成不存在的搜索路径
        self.cpp_info.libdirs = []
