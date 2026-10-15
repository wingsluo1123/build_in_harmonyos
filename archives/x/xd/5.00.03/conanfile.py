#!/usr/bin/env python3
"""xd 5.00.03 — OHOS Conan 配方（application）

上游: https://gitlab.com/fbb-git/xd (tag 5.00.03)
产物: 单个可执行文件 xd -> <package>/bin/xd

上游构建系统是作者自有的 icmake（`./build program` -> `icmbuild program`），
设备与 CI 都没有 icmake（W0b: ohpcd 制品仓无 icmake 配方）。本配方用 Python
复刻 icmbuild 的 program 模式语义，依据是 xd 自带的 icmconf / INSTALL.im /
CLASSES 与 icmake 的 program 构建模型：

  * 源集合 = 顶层主程序源（MAIN = main.cc，以及顶层其余 *.cc: handle.cc、
    usage.cc、noinput.cc）+ CLASSES 列出的模块目录（options command history
    alternatives selector）下的 *.cc，共 68 个翻译单元。
  * 每个翻译单元以“自身所在目录 + 源码根”为包含根编译: 模块内源码用
    `#include "xxx.ih"`（同目录），main.ih 用 `#include "options/options.h"`、
    `#include "version/version.h"`（源码根）。
  * 编译: $CXX <flags> -I<dir> -I<src> -I<bobcat include> -c -o <obj> <src.cc>
  * 链接: $CXX -o tmp/bin/xd <全部 .o> -L<bobcat lib> -lbobcat -pthread
    （对应上游 icmconf 的 ADD_LIBRARIES "bobcat"）
  * 安装: tmp/bin/xd -> bin/（INSTALL.im 的 BINARY）；xdrc -> share/xd/
    （上游 ./build install 的文档组件: 配置样例）

C++ 标准: 上游 INSTALL.im 未固定标准（Debian 以 ICMAKE_CPPSTD=--std=c++26
构建），依赖 bobcat 6.14.00 的公共头要求至少 C++20，故取
max(profile cppstd, 20)。

编译选项保留上游 INSTALL.im 的 CXXFLAGS（-Wall -Werror -O2 -pthread
-fdiagnostics-color=never），只去掉 ccache 包装；-O 由 build_type 覆盖。

适配证据（本机 aarch64-linux-ohos 交叉编译，OHOS SDK clang 15.0.4 + libc++）:
68/68 翻译单元在 -Wall -Werror 下零告警通过；链接产出 ELF aarch64 可执行
文件，NEEDED = libbobcat.so.6 / libc++_shared.so / libc.so。

源码补丁：1 个（patches/0001）——HMDFS 大小写不敏感使 tarball 根级 VERSION
（文件）与 version/（目录）冲突，source() 以 excludes 排除该文件后，把其三个
宏内联回 version/version.h；除此之外上游源码未改动。

构建驱动加固（worker fork 压力）：编译/链接命令以 argv 形式下发（不用 shell，
每条命令 1 个进程），并发上限 min(CPU, 4)；对瞬时 spawn 失败
（EAGAIN/ENOMEM/EMFILE/ENFILE，CI 实测 BlockingIOError: [Errno 11]）
做 3 次有限重试并写日志，其它 errno 与编译/链接自身失败照旧判负。
"""
import errno
import os
import shutil
import subprocess
import time
from multiprocessing.pool import ThreadPool

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

# worker 上 fork/exec/pipe 受限（OHOS AppSpawn 管控）时会瞬时返回这些 errno：
# 只对它们做有限重试，编译/链接自身的失败照旧直接判负（不掩盖真实错误）。
_TRANSIENT_SPAWN_ERRNOS = frozenset(
    {errno.EAGAIN, errno.ENOMEM, errno.EMFILE, errno.ENFILE}
)


class XdConan(ConanFile):
    name = "xd"
    version = "5.00.03"
    description = (
        "Xd, the eXtra smart Directory changer: expands the initial characters "
        "of nested directory names into the matching directory"
    )
    license = "GPL-3.0-or-later"
    url = "https://gitlab.com/fbb-git/xd"
    homepage = "https://fbb-git.gitlab.io/xd/"
    topics = ("cli", "directory", "shell", "filesystem")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # 上游 build-depends: libbobcat-dev (>= 3.11.01)；仓库内已适配 6.14.00
        self.requires("bobcat/6.14.00")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("xd only supports Linux and OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def source(self):
        # HMDFS 大小写不敏感：上游 tarball 根级同时含 VERSION（文件）与 version/
        # （目录），解包时二者在设备/CI 上同名冲突，source() 直接失败：
        #   IsADirectoryError: [Errno 21] Is a directory: './VERSION'   (CI #89206 实测)
        # 处理（先例 knowledge/drafts/DRAFT-liboggz-1.1.1-hmdfs-patches-collision）：
        # 排除根级 VERSION 文件、保留 version/ 目录，VERSION 提供的
        # AUTHOR/VERSION/YEARS 三个宏由 patches/0001 内联回 version/version.h。
        get(self, **self.conan_data["sources"][self.version], strip_root=True,
            excludes=["*VERSION"])

    # ------------------------------------------------------------------
    # 工具链
    # ------------------------------------------------------------------
    def _toolchain_executables(self):
        # R33: 编译器来自 Conan conf（profile 注入），不经 shell 环境变量。
        # Conan 2.29 不支持 "tools.build:compiler_executables:cpp" 点分子键，
        # 须先取 dict 再索引（workflow §5.3 已知坑）。
        return self.conf.get(
            "tools.build:compiler_executables", {}, check_type=dict
        ) or {}

    def _cxx(self):
        return self._toolchain_executables().get("cpp", "clang++")

    def _cppstd_flag(self):
        # 上游未固定 cppstd（Debian 用 --std=c++26）；bobcat 6.14.00 公共头
        # 使用 C++20 特性，低于 C++20 的 profile 必须抬到 20。
        requested = (str(self.settings.compiler.cppstd) or "").replace("gnu", "")
        try:
            level = int(requested)
        except ValueError:
            level = 20
        return "--std=c++" + str(max(level, 20))

    def _cxxflags(self):
        # 上游 INSTALL.im: CXXFLAGS "-Wall -Werror -O2 -pthread
        # -fdiagnostics-color=never"（去掉 INSTALL.im 的 ccache 包装）
        opt = {
            "Debug": "-O0 -g",
            "Release": "-O2",
            "RelWithDebInfo": "-O2 -g",
            "MinSizeRel": "-Os",
        }.get(str(self.settings.build_type), "-O2")
        return f"{opt} -Wall -Werror -pthread -fdiagnostics-color=never"

    def _subproc_env(self):
        """子进程环境: 继承当前环境，并确保 OHOS SDK 的 llvm/lib 在动态库
        搜索路径中——SDK 自带的 lld 链接器依赖 libxml2.so.16，部分 worker
        环境的 loader 搜索路径未覆盖该目录，缺失会导致链接子进程无法启动
        （unable to execute command）。

        profile 的编译器路径可能是符号链接（如 /data/service/hnp/bin/clang++
        -> SDK llvm/bin/clang++），必须 realpath 后再推导 lib 目录。"""
        env = dict(os.environ)
        llvm_lib = os.path.normpath(
            os.path.join(os.path.dirname(os.path.realpath(self._cxx())), "..", "lib")
        )
        if os.path.isabs(llvm_lib) and os.path.isdir(llvm_lib):
            parts = [p for p in env.get("LD_LIBRARY_PATH", "").split(os.pathsep) if p]
            if llvm_lib not in parts:
                parts.insert(0, llvm_lib)
            env["LD_LIBRARY_PATH"] = os.pathsep.join(parts)
        return env

    def _build_jobs(self):
        """编译并发上限：worker 的进程/fork 资源受限（实测 EAGAIN），
        并发取 min(CPU, 4)——只能用有限重试消化瞬时压力，不能靠加大并发。"""
        try:
            cpus = int(build_jobs(self))
        except Exception:
            cpus = 4
        return max(1, min(cpus, 4))

    def _run_with_retry(self, cmd, cwd, env, log, attempts=3):
        """执行一条命令；对**瞬时** spawn 失败（EAGAIN/ENOMEM/EMFILE/ENFILE）有限重试。

        不使用 shell=True：每个编译/链接只产生 1 个进程（shell 版本会多一个 /bin/sh），
        叠加并发上限后可显著降低 worker 上的 fork 压力。
        """
        last = None
        for attempt in range(1, attempts + 1):
            try:
                proc = subprocess.run(
                    cmd, cwd=cwd, env=env, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, text=True, check=False,
                )
            except OSError as err:                      # BlockingIOError 是 OSError 子类
                last = err
                if err.errno not in _TRANSIENT_SPAWN_ERRNOS:
                    raise
                log.write(f"$ {' '.join(cmd)}\n[retry {attempt}/{attempts}] "
                          f"spawn failed: {err}\n")
                log.flush()
                self.output.info(
                    f"spawn EAGAIN，第 {attempt}/{attempts} 次重试: {os.path.basename(cmd[-1])}"
                )
                time.sleep(1.0 * attempt)
                continue
            log.write(f"$ {' '.join(cmd)}\n{proc.stdout}\n")
            log.flush()
            return proc.returncode
        raise ConanException(
            f"spawn failed after {attempts} attempts: {' '.join(cmd)} ({last})"
        )

    # ------------------------------------------------------------------
    # 源集合（复刻 icmbuild program 模式）
    # ------------------------------------------------------------------
    def _classes(self, src):
        """上游 CLASSES: 逐行读取模块名，跳过注释行。"""
        with open(os.path.join(src, "CLASSES"), encoding="utf-8") as fh:
            return [
                line.strip()
                for line in fh
                if line.strip() and not line.strip().startswith("//")
            ]

    def _program_sources(self, src):
        """[(目录, 文件名)]：顶层 MAIN 及顶层其余 *.cc + 各模块目录下的 *.cc。

        icmbuild 的 program 模式编译 MAIN 与模块（CLASSES）内的全部 SOURCES；
        xd 把 handle/usage/noinput 放在顶层（由 main.ih 声明、非模块），
        与 main.cc 一同编译。"""
        sources = []
        for name in sorted(os.listdir(src)):
            if name.endswith(".cc") and os.path.isfile(os.path.join(src, name)):
                sources.append((src, name))
        for module in self._classes(src):
            mod_dir = os.path.join(src, module)
            if not os.path.isdir(mod_dir):
                continue
            for name in sorted(os.listdir(mod_dir)):
                if name.endswith(".cc") and os.path.isfile(os.path.join(mod_dir, name)):
                    sources.append((mod_dir, name))
        return sources

    # ------------------------------------------------------------------
    def _bobcat_paths(self):
        """(include dirs, lib dirs, libs) —— bobcat 依赖的绝对路径。"""
        dep = self.dependencies["bobcat"]
        cpp = dep.cpp_info
        aggregated = getattr(cpp, "aggregated_components", None)
        if callable(aggregated):
            cpp = aggregated()
        pkg = dep.package_folder or ""

        def resolve(dirs):
            return [d if os.path.isabs(d) else os.path.join(pkg, d) for d in dirs]

        return (
            resolve(list(cpp.includedirs)),
            resolve(list(cpp.libdirs)),
            list(cpp.libs) or ["bobcat"],
        )

    # ------------------------------------------------------------------
    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        cxx = self._cxx()
        stdflag = self._cppstd_flag()
        flags = self._cxxflags().split()
        bobcat_inc, bobcat_lib, bobcat_libs = self._bobcat_paths()

        sources = self._program_sources(src)
        self.output.info(f"xd 源文件: {len(sources)} 个翻译单元")

        # 先清空对象目录：等价上游 ./build clean，避免上一次构建（或本地探索
        # 构建）残留的 .o 参与链接造成重复符号。
        obj_root = os.path.join(src, "tmp", "obj")
        if os.path.isdir(obj_root):
            shutil.rmtree(obj_root)
        os.makedirs(obj_root, exist_ok=True)

        # 编译命令以 argv 形式给出（不经 shell）：路径不再需要手工引用，
        # 每个 TU 只产生一个进程，降低 worker 上的 fork 压力。
        compile_cmds = []
        for directory, name in sources:
            group = "root" if directory == src else os.path.basename(directory)
            out_dir = os.path.join(obj_root, group)
            os.makedirs(out_dir, exist_ok=True)
            obj = os.path.join(out_dir, f"{name[:-3]}.o")
            cmd = [cxx, *flags, stdflag, f"-I{directory}", f"-I{src}",
                   *[f"-I{d}" for d in bobcat_inc],
                   "-c", "-o", obj, os.path.join(directory, name)]
            compile_cmds.append(cmd)

        jobs = self._build_jobs()
        self.output.info(f"编译并发: {jobs}")
        log_path = os.path.join(self.build_folder, "xd_compile_log.txt")
        failures = []
        with open(log_path, "w", encoding="utf-8") as log:
            env = self._subproc_env()

            def run_one(cmd):
                return self._run_with_retry(cmd, cwd=src, env=env, log=log), cmd

            with ThreadPool(processes=jobs) as pool:
                for rc, cmd in pool.imap(run_one, compile_cmds):
                    if rc != 0:
                        failures.append(cmd)
        if failures:
            self.output.error(
                f"编译失败 {len(failures)}/{len(compile_cmds)}，日志: {log_path}"
            )
            raise ConanException(
                f"xd compile failed: {' '.join(failures[0])} (log: {log_path})"
            )
        self.output.info(f"编译完成 {len(compile_cmds)} 个翻译单元")

        objects = sorted(
            os.path.join(root, f)
            for root, _, files in os.walk(obj_root)
            for f in files
            if f.endswith(".o")
        )
        bin_dir = os.path.join(src, "tmp", "bin")
        os.makedirs(bin_dir, exist_ok=True)
        exe = os.path.join(bin_dir, "xd")
        link_cmd = ([cxx, "-o", exe, *objects]
                    + [f"-L{d}" for d in bobcat_lib]
                    + [f"-l{lib}" for lib in bobcat_libs]
                    + ["-pthread"])
        with open(log_path, "a", encoding="utf-8") as log:
            rc = self._run_with_retry(link_cmd, cwd=src,
                                      env=self._subproc_env(), log=log)
        if rc != 0:
            self.output.error(f"链接失败，日志: {log_path}")
            raise ConanException(f"link failed: {exe} (log: {log_path})")
        self.output.info(f"链接完成: {exe} ({len(objects)} 对象)")

    # ------------------------------------------------------------------
    def package(self):
        src = self.source_folder
        pkg = self.package_folder

        copy(self, "xd", src=os.path.join(src, "tmp", "bin"),
             dst=os.path.join(pkg, "bin"))
        # 上游 ./build install 的文档组件: changelog + 配置样例 xdrc
        copy(self, "xdrc", src=src, dst=os.path.join(pkg, "share", "xd"))
        copy(self, "changelog", src=src,
             dst=os.path.join(pkg, "share", "doc", "xd"))
        copy(self, "LICENSE", src=src, dst=os.path.join(pkg, "licenses"))

    def package_info(self):
        # 命令行工具，不是库
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
