#!/usr/bin/env python3
"""Conan recipe — pnc 0.9.5（libphonenumber 命令行封装）。

上游：https://git.sr.ht/~anjan/pnc
      源码归档 https://git.sr.ht/~anjan/pnc/archive/0.9.5.tar.gz
      （sr.ht 按需打包，实测连续两次下载 sha256 一致，可复现）

pnc 是已归档的 Orange-OpenSource/pn 的延续分支（Sxmo 项目维护）。它用
libphonenumber 及其离线地理编码模块 geocoding 做电话号码的校验/格式化/
从文本中抽取/归属地查询/国际拨号串生成，全部本地完成、不联网。

本包只构建 **CLI**（bin/pnc）。上游同一份源码里还有一个 GNU AWK 扩展
（gawkext/gawkpn.so），本平台实测存在退出期崩溃，因此不纳入本包 ——
详见 notes.md「为什么不构建 gawk 扩展」一节（含复现命令与失败率数据）。
这也是上游自身的行为：CMakeLists 用 check_include_files 探 gawkapi.h，
探不到就打印 "Excluding gawk plugin" 并跳过，本包环境即落在这一分支。

OHOS（HarmonyOS PC aarch64 / clang 15，CMake）适配要点，详见 notes.md 与
patches/：

  A. 上游用 find_library(phonenumber/geocoding/icuuc PATHS /usr/local/lib)
     加 include_directories(/usr/local/include) 定位依赖，这两个硬编码路径
     在打包/交叉环境里都不存在 → patches/0001 改为优先用 pkg-config 模块
     libphonenumber，取不到时回退上游查找（上游构建方式仍可用）。

  B. 为何不是 CMakeDeps：libphonenumber 是静态库（libphonenumber.a +
     libgeocoding.a），链接时必须连带 protobuf / abseil-cpp / icu4c 的静态
     库；而 protobuf 配方刻意不产出 CMake 配置（cpp_info 里
     cmake_find_mode=none），find_package(libphonenumber) 会在
     find_dependency(protobuf) 处直接断链。依赖链只有 .pc 表达得完整
     （与 mmsd-tng/2.6.4 的结论一致）。

  C. protobuf 33.6 包内有 libutf8_validity.a / libutf8_range.a，却没列入
     cpp_info.libs，生成的 protobuf.pc 因此缺这两个库，链接必报
     undefined symbol: utf8_range_IsValid / utf8_range_ValidPrefix。
     generate() 用补写后的 protobuf.pc 覆盖 generators 目录里的那一份：
     CMakeToolchain 会把 generators 目录前置进 PKG_CONFIG_PATH，外置的
     修复目录排不到它前面，只能就地覆盖。

  D. 上游 tests.sh 由 ctest 经 find_program(sh) 启动，构建机 PATH 上可能先
     命中不可执行的 sh 桩（本机 ~/npm/bin/sh 即此类）→ 显式指定 SH_PROG。
"""
import os
import shutil
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps


class PncConan(ConanFile):
    name = "pnc"
    version = "0.9.5"
    description = (
        "libphonenumber command-line wrapper: validate, format, find and "
        "geolocate phone numbers fully offline."
    )
    license = "GPL-3.0-only"
    homepage = "https://git.sr.ht/~anjan/pnc"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    # tests.sh 由 ctest 从 PATH 里 find_program(sh) 挑 shell；优先用 profile
    # 指定的 CONFIG_SHELL，再退回固定路径（逐个验证真能执行，桩文件会在
    # exec 时才暴露）。
    _SHELL_CANDIDATES = ("/data/service/hnp/bin/bash", "/bin/sh")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libphonenumber 是静态库：头文件与静态传递依赖（protobuf/abseil/
        # icu4c）都要透传给本包。
        self.requires("libphonenumber/8.13.51",
                      transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # OHOS worker 在进程压力下会出现 fork/exec 失败（EAGAIN）。clang 编译走
    # 集成汇编器（进程内、不 spawn），唯一 spawn 是链接器，因此该错误几乎只
    # 落在链接步：
    #   clang-15: error: unable to execute command: posix_spawn failed:
    #             Resource temporarily unavailable
    # 实测连续三个不同 worker 命中同一签名，属 worker 侧瞬时资源问题而非配方
    # 缺陷。这里只对这种特征退避重试，其余错误首次即返回。
    _EAGAIN_SIGNATURES = (
        "resource temporarily unavailable",
        "posix_spawn failed",
        "can't fork",
        "cannot fork",
        "failed to fork",
    )

    def _cmake_step(self, label, step, attempts=4, delay=30):
        """执行 CMake 步骤；仅当失败信息命中 EAGAIN 特征时退避重试。

        - 特征同时看「步骤日志」与「异常正文」：顶层 spawn 失败时进程根本没起来，
          日志是空的，EAGAIN 只出现在 ConanException 里。
        - 非 EAGAIN 失败首次即抛（不做重试），避免把真实编译错误拖成重试风暴。
        - 输出先落 build_folder 再回放：CI 会在 conan create 日志里查 ctest 痕迹，
          回放保证这些信息不因重定向而消失。
        """
        if attempts < 1:
            raise ConanException(f"{label}: attempts={attempts} 非法，不下放")

        for attempt in range(1, attempts + 1):
            log = os.path.join(self.build_folder, f"cmake-{label}-{attempt}.log")
            self.output.info(
                f"cmake {label}: 第 {attempt}/{attempts} 次尝试（日志 {log}）")
            try:
                with open(log, "w", encoding="utf-8", errors="replace") as fh:
                    step(stdout=fh, stderr=fh)
            except ConanException as exc:
                output = self._read_log(log)
                hit = next((s for s in self._EAGAIN_SIGNATURES
                            if s in f"{output}\n{exc}".lower()), None)
                if hit is None or attempt == attempts:
                    self.output.error(
                        f"{label} 失败（第 {attempt}/{attempts} 次尝试）：{exc}")
                    if output:
                        self.output.error(output)
                    raise
                self.output.warning(
                    f"{label}: 命中 worker fork/exec EAGAIN（{hit}），"
                    f"{delay}s 后重试（第 {attempt}/{attempts} 次）")
                if output:
                    self.output.warning(
                        "本次失败输出尾部：\n"
                        + "\n".join(output.splitlines()[-20:]))
                time.sleep(delay)
                delay = min(delay * 2, 120)
            else:
                output = self._read_log(log)
                if output:
                    self.output.info(f"--- cmake {label} 输出 ---\n{output}")
                return

        # 兜底：不把「一次都没跑成」放行为成功
        raise ConanException(f"{label}: 重试 {attempts} 次后仍未产出结果")

    @staticmethod
    def _read_log(path):
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                return fh.read()
        except OSError:
            return ""

    def _resolve_shell(self):
        candidates = [os.environ.get("CONFIG_SHELL")]
        candidates.extend(self._SHELL_CANDIDATES)
        candidates.append(shutil.which("sh"))
        for cand in candidates:
            if not cand or not os.path.isfile(cand) or not os.access(cand, os.X_OK):
                continue
            try:
                self.run(f'"{cand}" -c "exit 0"',
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return cand
            except ConanException:
                continue
        return None

    def _override_protobuf_pc(self):
        """protobuf.pc 补入包内已有但未声明的 utf8_validity/utf8_range。"""
        dep = self.dependencies.get("protobuf")
        if dep is None or not dep.package_folder:
            return
        libdir = os.path.join(dep.package_folder, "lib")
        extra = ""
        for lib in ("utf8_validity", "utf8_range"):
            if os.path.exists(os.path.join(libdir, f"lib{lib}.a")) or \
                    os.path.exists(os.path.join(libdir, f"lib{lib}.so")):
                extra += f" -l{lib}"
        text = (
            f"prefix={dep.package_folder}\n"
            "libdir=${prefix}/lib\n"
            "includedir=${prefix}/include\n"
            "bindir=${prefix}/bin\n"
            "\n"
            "Name: protobuf\n"
            "Description: Conan protobuf（+ 包内已有但 cpp_info 未声明的 utf8 库）\n"
            f"Version: {dep.ref.version}\n"
            f'Libs: -L"${{libdir}}" -lprotobuf{extra} -lpthread\n'
            'Cflags: -I"${includedir}"\n'
            "Requires: abseil-cpp zlib\n"
        )
        with open(os.path.join(self.generators_folder, "protobuf.pc"),
                  "w", encoding="utf-8") as fh:
            fh.write(text)
        self.output.info(
            f"protobuf.pc: 补入{extra.strip() or '（包内无 utf8 库，跳过）'}")

    def generate(self):
        # 先产 .pc，再覆盖 protobuf.pc（顺序不能倒）。
        PkgConfigDeps(self).generate()
        self._override_protobuf_pc()

        tc = CMakeToolchain(self)
        shell = self._resolve_shell()
        if shell:
            tc.variables["SH_PROG"] = shell
        else:
            self.output.warning("未找到可执行的 sh，ctest 可能无法启动上游测试")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        self._cmake_step("configure", cmake.configure)
        self._cmake_step("build", cmake.build)
        # R51：上游测试真跑 —— ctest 驱动上游 tests.sh（校验/格式化/抽取/
        # 多国号码共 11 项断言）。上游 CMakeLists 在探不到 gawkapi.h 时会打印
        # "Excluding gawk plugin"，属预期分支（见 notes.md）。
        self._cmake_step("test", cmake.test)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "pnc"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
