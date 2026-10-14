#!/usr/bin/env python3
"""Conan recipe - AdaptiveCpp 25.10.0 (异构计算编译器：SYCL / C++ stdpar / HIP-CUDA)

适配目标平台：HarmonyOS PC (aarch64-linux-ohos)。

构建方式沿用官方仓库中 clang/llvm/onetbb 等 CMake 类配方的做法：
鸿蒙 PC 真机原生编译（不设 CMAKE_SYSTEM_NAME，不触发交叉编译），
因此 llvm-tblgen 等宿主工具可以原生构建并运行。

依赖说明：AdaptiveCpp 的编译能力集中在一个 Clang 插件（acpp-clang）中，
该插件必须链接 clang 前端库。制品仓中的 clang/22.1.8 通过 Conan 导出
Clang config（ClangConfig.cmake + libclang-cpp.so + libLLVM.so + clang 头），
正好满足 find_package(LLVM) 与 find_package(Clang) 的需要。

版本约束：上游要求 LLVM 主版本落在 15..20（高于 20 或 18+ 的 .0 版本会
直接报错）。clang/22.1.8 超出该范围，因此需开启 ACPP_EXPERIMENTAL_LLVM。
这是本任务在真机上首先要验证的风险项，详见 notes.md。
"""
import glob
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.errors import ConanException
from conan.tools.files import (get, download, apply_conandata_patches, export_conandata_patches,
                                copy)


class AdaptiveCppConan(ConanFile):
    name = "adaptivecpp"
    version = "25.10.0"
    description = "AdaptiveCpp - 面向 C++ 异构编程模型的独立编译器（SYCL / 标准并行 / HIP-CUDA）"
    license = "BSD-2-Clause"
    homepage = "https://github.com/AdaptiveCpp/AdaptiveCpp"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        # 编译器功能档位：full 打开 SSCP/stdpar/加速 CPU（需要 clang 插件）。
        # 保留 none 档位，用于在插件不可用时单独验证运行时部分的可构建性。
        "compiler_feature_profile": ["full", "minimal", "none"],
        # 是否允许使用上游未正式支持的 LLVM 版本（本机情形：LLVM 22 > 上游上限 20）。
        "experimental_llvm": [True, False],
    }
    default_options = {
        "compiler_feature_profile": "full",
        "experimental_llvm": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    # LLVM/OpenMP 运行时源码：包内自带完整 libomp（见 _build_bundled_libomp）。
    _LLVM_URL = "https://github.com/llvm/llvm-project/releases/download/llvmorg-22.1.8/llvm-project-22.1.8.src.tar.xz"
    _LLVM_SHA256 = "922f1817a0df7b1489272d18134ee0087a8b068828f87ac63b9861b1a9965888"

    def source(self):
        # 主源码与 llvm-project 源码都走同一条"官方优先 + sha256 校验 + 镜像回退"
        # 的下载路径：平台 CI 会把 GitHub URL 改写成镜像（ghfast.top 等），实测
        # 这些镜像既可能连不上、也可能截断大文件，所以不依赖 conan 自带下载。
        src = self.conan_data["sources"]
        self._fetch_archive(src["url"], src["sha256"], self.source_folder,
                            strip_leading=True)
        # 单独取 llvm-project 源码（只用到其中的 openmp 运行时），用于构建
        # 包内自带的完整 libomp。
        self._fetch_archive(self._LLVM_URL, self._LLVM_SHA256,
                            os.path.join(self.source_folder, "llvm-project-src"),
                            strip_leading=True)

    _MIRROR_PREFIXES = ("https://gh-proxy.com/", "https://ghfast.top/",
                        "https://ghproxy.net/")

    def _fetch_archive(self, url, sha256, dest, strip_leading):
        """Download + verify + extract an archive, official host first.

        平台 CI 会把 GitHub URL 改写成镜像主机；镜像既可能连接失败，也可能把
        大文件截断（曾实测 ~160MB 归档被截断，conan 自带校验没拦住）。这里显式
        做 sha256 校验，失败即换下一个源重试；成功后再用 python tarfile 解压。
        """
        import hashlib
        import shutil
        import tarfile

        # 平台 CI 的镜像注入有两种形态：把 url 换成 "<mirror>/https://github.com/…"，
        # 或换成 [镜像, 官方] 的列表。两种都要能处理：先还原出官方 URL，再去重、
        # 追加镜像备选（同一列表中已有的镜像会被去重）。
        given = url if isinstance(url, (list, tuple)) else [url]
        bases = []
        for item in given:
            text = str(item)
            idx = text.find("https://github.com")
            if idx > 0:
                text = text[idx:]
            if text and text not in bases:
                bases.append(text)
        if not bases:
            raise ConanException("adaptivecpp: no usable source URL")
        urls = list(bases)
        for prefix in self._MIRROR_PREFIXES:
            for base_url in bases:
                candidate = prefix + base_url
                if candidate not in urls:
                    urls.append(candidate)

        tarball = os.path.join(self.source_folder, "dl-" + hashlib.sha256(
            bases[0].encode()).hexdigest()[:12] + ".archive")

        def digest_of(path):
            digest = hashlib.sha256()
            with open(path, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    digest.update(chunk)
            return digest.hexdigest()

        def extract(archive, origin):
            os.makedirs(dest, exist_ok=True)
            with tarfile.open(archive, "r:*") as tf:
                for member in tf.getmembers():
                    if strip_leading:
                        parts = member.name.split("/", 1)
                        if len(parts) < 2 or not parts[1]:
                            continue
                        member.name = parts[1]
                    tf.extract(member, dest, filter="data")
            self.output.info("sources: verified and extracted from {}".format(origin))

        # 平台修复指导②：把源码预缓存到 conan 的 s/ 目录。CI 会提供 DOWNLOAD_CACHE
        # （实测其值为 /data/cache），布局 s/<sha256>；命中即离线使用，成功下载后回写，
        # 使后续构建不再依赖 Worker 能不能连外网。先例：archives/f/fpc/3.2.2、
        # archives/l/libabigail/1.4、archives/l/linux-headers@5.15、archives/o/osv-scanner/2.1.0。
        cache_root = (os.environ.get("DOWNLOAD_CACHE")
                      or os.environ.get("CONAN_DOWNLOAD_CACHE"))
        cached = os.path.join(cache_root, "s", sha256) if cache_root else None
        if cached and os.path.isfile(cached):
            try:
                if digest_of(cached) == sha256:
                    extract(cached, "cache:" + cached)
                    return
                self.output.warning(
                    "sources: cached copy at {} has the wrong digest, ignoring".format(cached))
            except Exception as exc:
                self.output.warning("sources: cached copy unusable: {}".format(exc))

        def store(path, origin):
            """回写 s/<sha256>，让后续构建离线可用（失败不影响本次构建）。"""
            if not cache_root:
                return
            try:
                cache_dir = os.path.join(cache_root, "s")
                os.makedirs(cache_dir, exist_ok=True)
                target = os.path.join(cache_dir, sha256)
                staging = target + ".part"
                shutil.copyfile(path, staging)
                os.replace(staging, target)
                self.output.info(
                    "sources: cached as {} (next build needs no network)".format(target))
            except OSError as exc:
                self.output.warning(
                    "sources: could not populate DOWNLOAD_CACHE: {}".format(exc))

        for attempt in range(1, 4):
            for candidate in urls:
                try:
                    self.output.info(
                        "sources: downloading {} (attempt {}/3)".format(candidate, attempt))
                    download(self, url=candidate, filename=tarball)
                    if digest_of(tarball) != sha256:
                        self.output.warning(
                            "sources: checksum mismatch via {} "
                            "(truncated mirror?), trying next host".format(candidate))
                        continue
                    extract(tarball, candidate)
                    store(tarball, candidate)
                    return
                except Exception as exc:
                    self.output.warning(
                        "sources: fetch via {} failed: {}".format(candidate, exc))
        raise ConanException(
            "adaptivecpp: could not obtain verified sources for {} "
            "(tried {} hosts x 3 attempts, DOWNLOAD_CACHE={})".format(
                bases[0], len(urls), cache_root or "unset"))

    def layout(self):
        cmake_layout(self, src_folder=".")

    def requirements(self):
        # clang 包同时提供 LLVMConfig 与 ClangConfig（含 libclang-cpp.so），
        # 是 AdaptiveCpp 的 clang 插件能够链接的前提。
        self.requires("clang/22.1.8")

    def _query_target_toolchain_paths(self):
        """Ask the profile's compiler for the target sysroot and libc++ include dir.

        The libkernel bitcode is emitted by invoking the Clang driver standalone,
        so it does not inherit the build's implicit target flags. On OHOS neither
        the libc++ headers nor the sysroot C headers are found through Clang's
        default search paths, so both locations are queried from the toolchain
        itself (never hard-coded) and forwarded to CMake.
        """
        cxx = None
        compilers = self.conf.get("tools.build:compiler_executables", default=None, check_type=dict)
        if compilers:
            cxx = compilers.get("cpp") or compilers.get("c")
        cxx = cxx or shutil.which("clang++") or shutil.which("clang")
        if not cxx or not os.path.isfile(cxx):
            return None, None
        try:
            probe = subprocess.run(
                [cxx, "-target", "aarch64-linux-ohos", "-std=c++17", "-E", "-x", "c++",
                 os.devnull, "-v"],
                capture_output=True, text=True, timeout=120)
        except Exception:
            return None, None
        sysroot, libcxx_include = None, None
        for raw_line in ((probe.stderr or "") + (probe.stdout or "")).splitlines():
            line = raw_line.strip()
            if not line.startswith("/"):
                continue
            if line.endswith("/include/c++/v1"):
                libcxx_include = line
            marker = "/sysroot/usr/include"
            if marker in line:
                sysroot = line.split(marker)[0] + "/sysroot"
        return sysroot, libcxx_include

    def generate(self):
        tc = CMakeToolchain(self)
        # 真机原生编译：不设置 CMAKE_SYSTEM_NAME，保持 CMAKE_CROSSCOMPILING=False。
        tc.cache_variables["CMAKE_BUILD_TYPE"] = str(self.settings.build_type)
        tc.cache_variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"
        tc.cache_variables["ACPP_COMPILER_FEATURE_PROFILE"] = str(self.options.compiler_feature_profile)
        if self.options.experimental_llvm:
            tc.cache_variables["ACPP_EXPERIMENTAL_LLVM"] = "ON"
        # 只做 CPU（OpenMP）后端：鸿蒙 PC 上没有 CUDA / ROCm / Level Zero 运行时。
        tc.cache_variables["WITH_CUDA_BACKEND"] = "OFF"
        tc.cache_variables["WITH_ROCM_BACKEND"] = "OFF"
        tc.cache_variables["WITH_LEVEL_ZERO_BACKEND"] = "OFF"
        # LLVM 侧链接吃内存，保守限制并行子项目任务数。
        tc.cache_variables["ACPP_SUBPROJECT_PARALLEL_JOBS"] = "2"

        # ── 定位 Clang 发行版（真机构建实测必需）──────────────────────────
        # 上游用 find_package(LLVM CONFIG) 取 LLVM_VERSION_MAJOR 等变量。Conan 只为
        # 直接依赖生成 CMakeDeps 的 Clang 包装，不会转发 clang 包内的 LLVMConfig.cmake，
        # 因此必须显式指定 LLVM_DIR；否则 LLVM_VERSION_MAJOR 为空，上游
        # CMakeLists.txt:420 的 if(${LLVM_VERSION_MAJOR} LESS 15) 会展开成
        # if(LESS 15) 直接语法报错（真机实测的首个错误）。
        clang_pkg = self.dependencies["clang/22.1.8"].package_folder
        llvm_dir = os.path.join(clang_pkg, "lib", "cmake", "llvm")
        if os.path.isfile(os.path.join(llvm_dir, "LLVMConfig.cmake")):
            tc.cache_variables["LLVM_DIR"] = llvm_dir

        # 上游还用 clang++ 的路径反推 LLVM_PREFIX_DIR，再去
        # ${LLVM_PREFIX_DIR}/lib/clang/<major>/include 找 clang 内建头
        # （__clang_cuda_runtime_wrapper.h）。若沿用 profile 的工具链前缀
        # （/data/service/hnp），推导出 /data/service，找不到内建头 →
        # CMakeLists.txt:342 SEND_ERROR。指向 clang 包自带的 clang++（与
        # libclang-cpp.so 同版本）后，前缀推导与内建头查找同时成立。
        clang_exe = os.path.join(clang_pkg, "bin", "clang++")
        if os.path.isfile(clang_exe):
            tc.cache_variables["CLANG_EXECUTABLE_PATH"] = clang_exe

        # 双保险：显式锚定含 __clang_cuda_runtime_wrapper.h 的目录。
        for inc in sorted(glob.glob(os.path.join(clang_pkg, "lib", "clang", "*", "include"))):
            if os.path.isfile(os.path.join(inc, "__clang_cuda_runtime_wrapper.h")):
                tc.cache_variables["CLANG_INCLUDE_PATH"] = inc
                break

        # ld.lld：llvm-to-host 链接器。clang/22.1.8 包只带 llc/opt、不含 lld，
        # 而上游只在 ${LLVM_TOOLS_BINARY_DIR}（即 clang 包 bin/）下 NO_DEFAULT_PATH
        # 查找，必然落空并 SEND_ERROR（src/compiler/CMakeLists.txt:49）。
        # 这里从 profile 的工具链目录推导 LLD 位置，不硬编码机器路径。
        lld_candidates = []
        which_lld = shutil.which("ld.lld")
        if which_lld:
            lld_candidates.append(which_lld)
        compiler_execs = self.conf.get("tools.build:compiler_executables", default=None, check_type=dict)
        if compiler_execs and compiler_execs.get("c"):
            lld_candidates.append(os.path.join(os.path.dirname(compiler_execs["c"]), "ld.lld"))
        for cand in lld_candidates:
            if cand and os.path.isfile(cand):
                tc.cache_variables["ACPP_LLD_PATH"] = cand
                break

        # device 侧 libkernel bitcode 由独立调用的 clang 生成，不继承本次构建的
        # sysroot / 标准库搜索路径。OHOS 上必须显式给出 sysroot 与 libc++ 头目录，
        # 否则 <cstdlib>/<cmath>/<cstdio> 等标准头找不到，bitcode 生成直接失败。
        target_sysroot, libcxx_include = self._query_target_toolchain_paths()
        if target_sysroot:
            tc.cache_variables["ACPP_BITCODE_SYSROOT"] = target_sysroot
        if libcxx_include:
            tc.cache_variables["ACPP_BITCODE_LIBCXX_INCLUDE"] = libcxx_include

        # 安装后共享库之间的定位由 patches/0001 在链接行上加 -Wl,-rpath,'$ORIGIN…' 解决。
        # 不走 CMAKE_INSTALL_RPATH：CMake 应用 CMakePresets 的 cacheVariables 时会把
        # $ORIGIN 当变量展开成空串，传进去只会得到坏值。

        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        self._build_bundled_libomp()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()
        self._install_ohos_clang_wrapper()
        self._build_omp_target_api_shim()
        self._package_bundled_libomp()
        self._fix_exported_no_soname()
        self._fix_package_permissions()

    def _fix_package_permissions(self):
        """Normalise packaged artefacts to group readable/executable.

        Scope, stated precisely because the first attempt at this oversold
        itself: on this platform the "other" permission class is **not
        representable at all**. Measured on the shared volume (and confirmed by
        a probe on the CI worker, which reported the wrapper at mode 750 after
        this recipe had explicitly chmod'ed it to 755):

            umask 000 -> 660    umask 022 -> 640    umask 077 -> 600
            chmod 755 -> 770    chmod 644 -> 660

        so a chmod can only ever widen the *group* bits. This function
        therefore guarantees group r-x on directories and on bin/, r-x on every
        .so, and r elsewhere -- the most that can be granted here.

        It does **not** explain, and cannot fix, the CI failure that followed:
        there A5 read the file successfully (llvm-readelf, A4) yet the exec
        mapping was refused with EACCES, which is the hmmac=use_task sandbox
        declining to map another task's file. check_ohos.py handles that
        explicitly instead of pretending a chmod solves it.
        """
        import stat
        lib_dir = os.path.join(self.package_folder, "lib")
        bin_dir = os.path.join(self.package_folder, "bin")
        fixed = 0
        for root, dirs, files in os.walk(self.package_folder):
            for name in dirs:
                path = os.path.join(root, name)
                mode = stat.S_IMODE(os.stat(path).st_mode)
                want = mode | 0o050           # r-x for group (other not expressible)
                if want != mode:
                    os.chmod(path, want)
                    fixed += 1
            for name in files:
                path = os.path.join(root, name)
                mode = stat.S_IMODE(os.stat(path).st_mode)
                # 可执行位：bin/ 下的一切，以及 lib/ 下的 .so
                executable = (root == bin_dir or root.startswith(bin_dir + os.sep)
                              or (root.startswith(lib_dir) and name.endswith(".so")))
                want = mode | (0o050 if executable else 0o040)
                if want != mode:
                    os.chmod(path, want)
                    fixed += 1
        if fixed:
            self.output.info(
                "adaptivecpp: normalised {} packaged entries to group "
                "readable/executable (other bits are not representable "
                "on this platform)".format(fixed))

        # 自证：CI 上曾观察到「配方显式 chmod 0o755 的文件最终为 750」（other 位丢失），
        # 说明该文件系统可能不保留 other 位。这里回读若干个关键条目的真实 mode 并打日志，
        # 让下一轮 CI 日志能直接判定 chmod 是否真的生效，而不是靠猜。
        probes = ["bin/acpp-clang-wrapper", "lib/libacpp-clang.so"]
        for rel in probes:
            path = os.path.join(self.package_folder, rel)
            if os.path.exists(path):
                got = stat.S_IMODE(os.stat(path).st_mode)
                self.output.info(
                    "adaptivecpp: probe {} -> mode {:o} (other-readable: {})".format(
                        rel, got, bool(got & 0o004)))

    def _build_bundled_libomp(self):
        """Build a complete libomp (LLVM OpenMP runtime) into the package.

        The OHOS SDK ships a trimmed libomp which is fatal for AdaptiveCpp:
          * it lacks the omp_target_* entry points that the omp backend's
            JIT-compiled kernel libraries reference;
          * its multi-threaded teardown deadlocks on this platform (observed:
            main thread and one worker both blocked on a futex after main()
            returned, while a complete upstream build of the same version
            exits cleanly).
        The recipe therefore builds the upstream OpenMP runtime and ships it
        as lib/libomp.so; the acpp wrapper's -L/-rpath put the package lib
        directory first so consumers link and run against it.
        """
        # 优先使用 profile 指定的构建编译器：平台的 dev 工具链自带默认 sysroot，
        # 而 SDK 里的 clang 需要显式 --sysroot（cmake 的链接探测会因此失败）。
        tools = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        clang_cc = tools.get("c", "") or ""
        clang_cxx = tools.get("cpp", "") or ""
        if not (os.path.isfile(clang_cc) and os.path.isfile(clang_cxx)):
            clang_pkg = self.dependencies["clang/22.1.8"].package_folder
            clang_cc = os.path.join(clang_pkg, "bin", "clang")
            clang_cxx = os.path.join(clang_pkg, "bin", "clang++")
        if not (os.path.isfile(clang_cc) and os.path.isfile(clang_cxx)):
            raise ConanException("adaptivecpp: no usable clang/clang++ for bundled libomp")

        openmp_src = os.path.join(self.source_folder, "llvm-project-src", "openmp")
        if not os.path.isdir(openmp_src):
            raise ConanException("adaptivecpp: llvm-project sources not found at " + openmp_src)

        # OHOS 的 musl 不提供 POSIX 线程取消接口，按上游 Android 先例关闭该特性
        kmp_h = os.path.join(openmp_src, "runtime", "src", "kmp.h")
        with open(kmp_h) as f:
            content = f.read()
        if "!defined(__GLIBC__)" not in content:
            anchor = "#if KMP_OS_WASI\n#undef KMP_CANCEL_THREADS\n#endif"
            assert anchor in content, "kmp.h: KMP_CANCEL_THREADS anchor not found"
            content = content.replace(
                anchor,
                anchor + "\n\n// musl-based libcs (as shipped for OHOS) do not expose the POSIX\n"
                "// thread-cancellation interface; same situation as Android above.\n"
                "#if defined(__linux__) && !defined(__GLIBC__)\n#undef KMP_CANCEL_THREADS\n#endif\n")
            with open(kmp_h, "w") as f:
                f.write(content)

        build_dir = os.path.join(self.source_folder, "build-libomp")
        self.run('cmake -G Ninja -S "{}" -B "{}" '
                 '-DCMAKE_BUILD_TYPE=Release '
                 '-DCMAKE_C_COMPILER="{}" -DCMAKE_CXX_COMPILER="{}" '
                 '-DLIBOMP_ENABLE_SHARED=ON '
                 # 明确给出 SONAME；并关闭版本脚本——musl 链接器下生成的
                 # 符号版本名异常（...@@VERSION），会让 omp_pause_resource 等
                 # 版本化符号无法被链接。
                 '-DCMAKE_SHARED_LINKER_FLAGS="-Wl,-soname,libomp.so" '
                 '-DLIBOMP_USE_VERSION_SCRIPT=OFF'.format(openmp_src, build_dir, clang_cc, clang_cxx))
        self.run('cmake --build "{}" --target omp'.format(build_dir))
        so = os.path.join(build_dir, "runtime", "src", "libomp.so")
        if not os.path.isfile(so):
            raise ConanException("adaptivecpp: bundled libomp build produced no libomp.so")
        self._bundled_libomp = so

    def _package_bundled_libomp(self):
        so = getattr(self, "_bundled_libomp", None)
        if not so or not os.path.isfile(so):
            raise ConanException("adaptivecpp: bundled libomp is missing at package() time")
        copy(self, "libomp.so", src=os.path.dirname(so),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def _fix_exported_no_soname(self):
        """Correct stale IMPORTED_NO_SONAME flags in the exported CMake targets.

        Upstream builds the clang plugin as a MODULE library, so CMake's export
        step marks it IMPORTED_NO_SONAME even though patch 0001 gives that
        library a real DT_SONAME (it is dlopen()ed by the driver and, on musl,
        must be addressable by name). The flag is therefore stale metadata that
        no longer matches the shipped binaries; flip it to FALSE so downstream
        CMake consumers see the same contract the ELF headers declare.

        实测产物形态（2026-10-08，彻底清缓存重建复现）：CMake 写出的是带配置
        后缀且带引号的

            IMPORTED_NO_SONAME_RELEASE "TRUE"

        而不是裸 `IMPORTED_NO_SONAME TRUE`。旧正则按后者匹配，对真实产物永不
        命中，本修正静默失效（重建日志里没有 "corrected ..." 输出）——L5c
        门禁因此持续失败，且与 conan binary 复用无关。此处按"属性名 + 可选
        配置后缀 + 引号/大小写"匹配，并保持写回后的引号形态。
        """
        import glob
        fixed = []
        pattern = os.path.join(self.package_folder, "lib", "cmake", "**",
                               "*-targets-*.cmake")
        for path in glob.glob(pattern, recursive=True):
            with open(path) as f:
                text = f.read()
            if "IMPORTED_NO_SONAME" not in text:
                continue
            corrected = re.sub(
                r'(IMPORTED_NO_SONAME(?:_[A-Za-z0-9]+)?\s+)"?[Tt][Rr][Uu][Ee]"?',
                r'\1"FALSE"', text)
            if corrected != text:
                with open(path, "w") as f:
                    f.write(corrected)
                fixed.append(os.path.relpath(path, self.package_folder))
        if fixed:
            self.output.info("adaptivecpp: corrected IMPORTED_NO_SONAME in: {}"
                             .format(", ".join(fixed)))

    def _build_omp_target_api_shim(self):
        """Compile a host-semantic OpenMP target API shim into the package.

        The omp backend JIT-compiles kernels into OpenMP-target form, so the
        generated kernel libraries reference omp_target_alloc/free/memcpy.
        Those symbols live in libomptarget, which the OHOS SDK does not ship.
        For a CPU-only target their host semantics are exact (a "device"
        pointer is an ordinary host allocation), so the recipe compiles a
        small shim and patches (patch 0011) make the runtime preload it
        before dlopen()ing any kernel library.
        """
        clang_pkg = self.dependencies["clang/22.1.8"].package_folder
        # shim 为纯 C，用 C 驱动编译以避免引入 libc++ 依赖
        clangxx = os.path.join(clang_pkg, "bin", "clang")
        if not os.path.isfile(clangxx):
            self.output.warning("adaptivecpp: omp target shim not built (clang missing)")
            return
        target_sysroot, libcxx_include = self._query_target_toolchain_paths()
        sysroot_arg = ' --sysroot="{}"'.format(target_sysroot) if target_sysroot else ""
        # C 驱动也会自动补 -lunwind / -lc++，需给出 SDK 内的库搜索路径
        link_dirs = ""
        if target_sysroot:
            sdk_native = os.path.dirname(target_sysroot)
            for d in (os.path.join(sdk_native, "llvm", "lib", "aarch64-linux-ohos"),
                      os.path.join(target_sysroot, "usr", "lib", "aarch64-linux-ohos"),
                      os.path.join(target_sysroot, "usr", "lib")):
                link_dirs += ' -L"{}"'.format(d)
        shim_src = os.path.join(self.package_folder, "lib", "omp_target_api_host.c")
        shim_so = os.path.join(self.package_folder, "lib", "libomptarget_host.so")
        shim_code = """#include <stdlib.h>
#include <string.h>
void *omp_target_alloc(size_t size, int device_num) {
  (void)device_num;
  return malloc(size);
}
void omp_target_free(void *device_ptr, int device_num) {
  /* no-op: on a CPU target the runtime allocator owns the pointer; matches
   * libomptarget behaviour for pointers that were never associated. */
  (void)device_ptr;
  (void)device_num;
}
int omp_target_memcpy(void *dst, const void *src, size_t length,
                      size_t dst_offset, size_t src_offset, int dst_device_num,
                      int src_device_num) {
  (void)dst_device_num;
  (void)src_device_num;
  memcpy((char *)dst + dst_offset, (const char *)src + src_offset, length);
  return 0;
}
int omp_target_memcpy_rect(void *dst, const void *src, size_t element_size,
                           int num_dims, const size_t *dst_dims,
                           const size_t *src_dims, const size_t *dst_offsets,
                           const size_t *src_offsets, const size_t *dst_extents,
                           const size_t *src_extents, int dst_device_num,
                           int src_device_num) {
  (void)dst; (void)src; (void)element_size; (void)num_dims;
  (void)dst_dims; (void)src_dims; (void)dst_offsets; (void)src_offsets;
  (void)dst_extents; (void)src_extents;
  (void)dst_device_num; (void)src_device_num;
  return -1;
}
int omp_target_is_present(const void *ptr, int device_num) {
  (void)device_num;
  return ptr != 0;
}
int omp_target_associate(const void *host_ptr, const void *device_ptr,
                         size_t size) {
  (void)host_ptr; (void)device_ptr; (void)size;
  return 0;
}
int omp_target_disassociate(const void *host_ptr, int device_num) {
  (void)host_ptr; (void)device_num;
  return 0;
}
int omp_get_num_devices(void) { return 0; }
int omp_is_initial_device(void) { return 1; }
"""
        with open(shim_src, "w") as f:
            f.write(shim_code)
        self.run('"{}"{}{} -shared -fPIC -O2 -Wl,-soname,libomptarget_host.so "{}" -o "{}"'.format(
            clangxx, sysroot_arg, link_dirs, shim_src, shim_so))
        self.output.info("adaptivecpp: built omp target API shim -> {}".format(shim_so))

    def _install_ohos_clang_wrapper(self):
        """Install a clang wrapper and make acpp use it by default.

        The clang from the clang/22.1.8 package has no knowledge of the OHOS
        toolchain layout: target sysroot, libc++ headers and linker search paths
        all live inside the OHOS SDK. Without them any SYCL translation unit
        fails on standard headers such as <cstdlib>, <memory> or <omp.h>.
        Baking these paths into a wrapper and pointing acpp's default-clang at it
        keeps consumers configuration-free.
        """
        import json

        target_sysroot, libcxx_include = self._query_target_toolchain_paths()
        clang_exe = os.path.join(self.dependencies["clang/22.1.8"].package_folder, "bin", "clang++")
        if not (target_sysroot and libcxx_include and os.path.isfile(clang_exe)):
            self.output.warning("adaptivecpp: OHOS clang wrapper not installed "
                                "(toolchain paths unavailable)")
            return

        sdk_native = os.path.dirname(target_sysroot)            # .../ohos/native
        sysroot_lib = os.path.join(target_sysroot, "usr", "lib")
        wrapper = os.path.join(self.package_folder, "bin", "acpp-clang-wrapper")
        os.makedirs(os.path.dirname(wrapper), exist_ok=True)
        lines = [
            "#!/bin/sh",
            "# Generated by the adaptivecpp recipe; see conanfile.py for the rationale.",
            'exec "{}" \\'.format(clang_exe),
            '  --sysroot="{}" \\'.format(target_sysroot),
            '  -isystem "{}" \\'.format(libcxx_include),
            '  -isystem "{}" \\'.format(os.path.join(sdk_native, "llvm", "include")),
            '  -L"{}" \\'.format(os.path.join(self.package_folder, "lib")),
            '  -L"{}" \\'.format(os.path.join(sdk_native, "llvm", "lib", "aarch64-linux-ohos")),
            '  -L"{}" \\'.format(os.path.join(sysroot_lib, "aarch64-linux-ohos")),
            '  -L"{}" \\'.format(sysroot_lib),
            '  -Wl,-rpath,"{}" \\'.format(os.path.join(self.package_folder, "lib")),
            '  -Wl,-rpath,"{}" \\'.format(os.path.join(sdk_native, "llvm", "lib", "aarch64-linux-ohos")),
            '  -Wl,-rpath,"{}" \\'.format(os.path.dirname(clang_exe)),
            '  "$@"',
            "",
        ]
        with open(wrapper, "w") as f:
            f.write("\n".join(lines))
        os.chmod(wrapper, 0o755)

        core_json = os.path.join(self.package_folder, "etc", "AdaptiveCpp", "acpp-core.json")
        if os.path.isfile(core_json):
            with open(core_json) as f:
                config = json.load(f)
            config["default-clang"] = wrapper
            with open(core_json, "w") as f:
                json.dump(config, f, indent=2)
                f.write("\n")
            self.output.info("adaptivecpp: acpp default-clang -> {}".format(wrapper))

    def package_info(self):
        # 消费入口：bin/ 下的 acpp 驱动，lib/ 下的运行时。
        # 上游把公开头文件装到 include/AdaptiveCpp/（见顶层 CMakeLists 的
        # install(DIRECTORY include/SYCL ... DESTINATION include/AdaptiveCpp/)），
        # 因此 includedirs 用 include 即可让消费者同时看到 AdaptiveCpp/ 与 sycl/。
        self.cpp_info.set_property("cmake_file_name", "AdaptiveCpp")
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = ["lib/cmake/AdaptiveCpp"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = []
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl", "pthread"]
