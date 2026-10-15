#!/usr/bin/env python3
"""samarium 1.0.0 test_package —— 真实消费者 + 交付形态自检。

① 消费者用例（test_package.cpp）：只 include 交付的公共头、只链接交付的
   libsamarium.so，用外部可核对真值（解析力学、离散闭式解、几何/守恒律、
   均匀分布性质、滑动窗口不变量）判定 —— 不是自证式断言。
② 交付形态自检（test_layout.py）：ELF 架构/soname/运行时依赖链、头文件包含闭包、
   未交付模块已裁掉、许可原文、无测试与构建中间产物、无隐藏文件、
   CMake/pkconfig 契约可重定位、.codesign 段（OHOS）。

本测试的编译与链接**真依赖被测包**：CI 的 L1e(R34) 会把 lib/、include/ 移走后
重跑 conan test，届时本消费者必须编译失败。
"""
import glob
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.tools.build import can_run, cross_building
from conan.tools.cmake import CMake, cmake_layout

ELF_MACHINE = {
    "armv8": "AArch64",
    "armv7": "ARM",
    "x86_64": "x86-64",
    "x86": "Intel 80386",
}


class SamariumTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "PkgConfigDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # samarium 的公共头直接 include range/v3 与 fmt 的头（geometry/Mesh.hpp、
        # graphics/Grid.hpp、physics/ParticleSystem.hpp、util/format.hpp）。Conan 2.29 的
        # CMakeDeps 会把**传递依赖**的 include 置空（仓库知识库
        # DRAFT-conan2-cmakedeps-transitive-include-strip：只对消费端直接 requires 的包
        # 生成完整 *-data.cmake）⇒ 消费端显式声明这两个依赖，与 CCI 生态的常规写法一致。
        self.requires("fmt/8.1.1", transitive_headers=True)
        self.requires("range-v3/0.12.0", transitive_headers=True)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _conan_libdirs(self):
        """每个 conan 依赖（含被测包自己）的 libdir —— 顶层聚合 + 每个组件。"""
        libdirs = []

        def collect(paths, owner):
            for entry in paths or []:
                full = entry if os.path.isabs(entry) else os.path.join(owner, entry)
                if full and full not in libdirs:
                    libdirs.append(full)

        for _ref, dep in self.dependencies.items():
            if not dep.package_folder:
                continue
            collect(dep.cpp_info.libdirs, dep.package_folder)
            for component in dep.cpp_info.components.values():
                collect(component.libdirs, dep.package_folder)
        return libdirs

    def _task_local_resign(self, conan_libdirs):
        """把 **conan 依赖** 的 .so 复制进任务私有 rt-signed/ 并本机重签（E517）。

        只复制+重签 conan 依赖（含被测包自己）的 .so；**绝不碰 SDK 的 libc++/libomp**
        （pangomm #66255 实证：把工具链自己的库也复制重签 ⇒ 整个进程连 C 库符号都解析
        不了）。重签失败的副本立即删除，保证回退到原件而不是把本来能加载的库弄坏。
        """
        scratch = os.path.join(self.build_folder, "rt-signed")
        shutil.rmtree(scratch, ignore_errors=True)
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if str(self.settings.os) not in ("OHOS", "HarmonyOS") or not os.path.isfile(signer):
            return None, set()
        os.makedirs(scratch)
        pending, links = {}, []
        for directory in conan_libdirs:
            for path in sorted(glob.glob(os.path.join(directory, "*.so*"))):
                name = os.path.basename(path)
                if os.path.islink(path):
                    links.append((name, os.path.basename(os.readlink(path)),
                                  os.path.basename(os.path.realpath(path))))
                elif os.path.isfile(path):
                    pending.setdefault(name, path)
        for name, src in sorted(pending.items()):
            shutil.copy2(src, os.path.join(scratch, name))
        kept, failures = set(), []
        for name in sorted(pending):
            path = os.path.join(scratch, name)
            if os.path.isfile(objcopy):
                subprocess.run([objcopy, "--remove-section", ".codesign", path],
                               capture_output=True, check=False)
            signed = path + ".signed"
            res = subprocess.run(
                [signer, "sign", "-selfSign", "1", "-inFile", path, "-outFile", signed],
                capture_output=True, text=True, check=False)
            if (res.returncode == 0 and os.path.isfile(signed)
                    and os.path.getsize(signed) > 0):
                os.replace(signed, path)
                os.chmod(path, 0o755)
                kept.add(name)
            else:
                failures.append(name)
                for stale in (path, signed):
                    if os.path.exists(stale):
                        os.remove(stale)
        for name, target, real in links:
            if target in kept or real in kept:
                dest = os.path.join(scratch, name)
                if not os.path.lexists(dest):
                    os.symlink(target if target in kept else real, dest)
        self.output.info(
            "[runtime-diag] 依赖 .so 复制 {} 个 / 重签成功 {} 个 / 失败 {} 个{}".format(
                len(pending), len(kept), len(failures),
                ("：" + ",".join(sorted(failures))) if failures else ""))
        return scratch, kept

    def _sdk_libdirs(self):
        """SDK 目录**只进搜索路径**（绝不复制/重签，见 _task_local_resign）。"""
        dirs = []
        for candidate in (
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
                "ohos/native/llvm/lib/aarch64-linux-ohos",
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"):
            if os.path.isdir(candidate):
                dirs.append(candidate)
        return dirs

    def _run_consumer(self, binary, is_ohos):
        """真跑消费者二进制（显式 LD_LIBRARY_PATH [+ E517 重签副本]）。

        OHOS 上两条都有本仓实证的约束：
          * 硬坑 F：OHOS 不在 CMake 平台表里 ⇒ CMake 不给可执行文件写 RPATH/RUNPATH
            ⇒ 消费者只能靠 LD_LIBRARY_PATH 找 libsamarium.so / libfmt.so
            （本仓 fmt 8.1.1 与 pango 的 test_package 都为此**显式**拼 LD_LIBRARY_PATH）。
          * E517：加载器可能拒载「带 .codesign 段但签名在本机不被接受」的 .so。本包 CI
            实证（#79896）：`./test_samarium` 报
            `Error loading shared library libsamarium.so: (needed by ./test_samarium)`，
            而本机核对过 VirtualRunEnv 生成的 `conanrunenv-release-*.sh` —— 它**确实**
            把 `<pkg>/lib` 放进了 LD_LIBRARY_PATH（`…/p/lib:…/fmt*/p/lib`），
            所以那是「拒绝加载」而不是「找不到」。处置按 E517 推荐 + 本仓 pangomm
            2.46.5 的成熟做法：rt-signed/ 里重签一份 conan 依赖 .so（含被测包自己的
            libsamarium.so）并排在最前。

        先按**交付态**路径试跑一次（结果写进日志，能把「找不到 / 签名被拒 / 真跑不动」
        区分开）：交付态能跑就用交付态，跑不动才改用重签副本，两者都是真执行。
        """
        conan_libdirs = self._conan_libdirs()
        sdk_libdirs = self._sdk_libdirs()
        scratch, kept = (None, set())
        if is_ohos:
            scratch, kept = self._task_local_resign(conan_libdirs)
        ld_delivered = os.pathsep.join(conan_libdirs + sdk_libdirs)
        ld_resigned = os.pathsep.join(([scratch] if kept else []) + conan_libdirs + sdk_libdirs)

        for name in ("libsamarium.so", "libfmt.so.8"):
            hits = [d for d in ld_delivered.split(os.pathsep)
                    if os.path.exists(os.path.join(d, name))]
            self.output.info("[runtime-diag] {} 在交付态搜索路径上命中 {} 个目录: {}".format(
                name, len(hits), hits))

        probe_env = dict(os.environ)
        probe_env["LD_LIBRARY_PATH"] = (
            ld_delivered + os.pathsep + probe_env["LD_LIBRARY_PATH"]
            if probe_env.get("LD_LIBRARY_PATH") else ld_delivered)
        probe = subprocess.run([os.path.abspath(binary)], capture_output=True, text=True,
                               errors="replace", env=probe_env, timeout=600, check=False)
        self.output.info(
            "[runtime-diag] 交付态（不用重签副本）执行: rc={} stdout={!r} stderr={!r}".format(
                probe.returncode, (probe.stdout or "")[:300].strip(),
                (probe.stderr or "")[-400:].strip()))
        if probe.returncode == 0:
            ld_path = ld_delivered
            self.output.info("[runtime-diag] 交付态可直接执行 ⇒ 官方用例走交付态路径")
        else:
            ld_path = ld_resigned
            self.output.info(
                "[runtime-diag] 交付态无法执行 ⇒ 官方用例改用任务私有重签副本"
                "（rt-signed 里 {} 个库）走在搜索路径最前（E517）".format(len(kept)))

        # 注意：这里用 %-格式化而不是 str.format —— 待拼的字符串里就有 `${...}` 大括号。
        env_prefix = 'LD_LIBRARY_PATH="%s$LD_LIBRARY_PATH"' % ld_path
        # conan 的 env="conanrun" 包装是 `. conanrun.sh && <本条命令>`，所以行内的
        # LD_LIBRARY_PATH 赋值发生在**真正执行二进制的那一刻** ⇒ 上面这份显式列表
        # （重签副本在最前）优先级高于 conanrun 自己的 libdirs。
        bash = ""
        for candidate in ("/data/service/hnp/bin/bash", "/bin/bash", "/usr/bin/bash"):
            if os.path.isfile(candidate):
                bash = candidate
                break
        base = os.path.basename(binary)
        if bash:
            self.run('%s "%s" -c \'./%s\'' % (env_prefix, bash, base), env="conanrun")
        else:
            self.run("%s ./%s" % (env_prefix, base), env="conanrun")

    def test(self):
        is_ohos = str(self.settings.os) in ("OHOS", "HarmonyOS")
        binary = os.path.join(self.cpp.build.bindirs[0], "test_samarium")
        if cross_building(self) or not can_run(self):
            self.output.warning("samarium: cross build, consumer binary not executed")
        else:
            self._run_consumer(binary, is_ohos)

        args = [
            sys.executable,
            os.path.join(self.source_folder, "test_layout.py"),
            '--package-folder=%s' % self.dependencies["samarium"].package_folder,
            '--generators-dir=%s' % self.generators_folder,
            '--consumer=%s' % binary,
            '--version=%s' % self.dependencies["samarium"].ref.version,
        ]
        machine = ELF_MACHINE.get(str(self.settings.arch))
        if machine:
            args.append("--expect-machine=%s" % machine)
        if is_ohos:
            args.append("--expect-ohos")
        self.run(" ".join(args))
