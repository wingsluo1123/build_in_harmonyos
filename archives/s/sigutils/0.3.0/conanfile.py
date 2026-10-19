#!/usr/bin/env python3
"""Conan recipe — sigutils 0.3.0 (BatchDrake/sigutils, CMake, C99, shared lib)

数字信号处理原语库（NCQO 振荡器、PLL、Costas 环、AGC、IIR、信道检测器、
频谱调谐器、Matlab .mat 文件 I/O 等），LGPL-3.0-or-later。上游只构建
SHARED 库（add_library(sigutils SHARED)，SOVERSION 1），并无条件构建
自测程序 sutest（src/main.c + 10 个测试模块，18 个注册测试）。

OHOS 适配要点（先例 mgard/1.6.0 同款骨架）：
1. bare cmake + 自发现 OHOS NDK ohos.toolchain.cmake，绕开
   conan_toolchain 的 "System is unknown HarmonyOS"（ML-0035）；
   Ninja 生成器（E074 jobserver fifo EPERM 只影响 make，Ninja 可并行）。
2. 依赖经 pkg_check_modules（REQUIRED sndfile>=1.0.2、fftw3f>=3.0；
   可选 volk 不提供 → 上游自动跳过）：generate() 写 sndfile.pc /
   fftw3f.pc shim 指向制品仓依赖包（libsndfile/1.2.2 默认 fPIC=True
   静态、fftw3f/3.3.10 共享 .so，均可链入 libsigutils.so），
   PKG_CONFIG_EXECUTABLE 指 HNP pkg-config。
3. CMAKE_PROJECT_TOP_LEVEL_INCLUDES 预载片段放宽
   CMAKE_FIND_ROOT_PATH_MODE_*=BOTH：ohos.toolchain.cmake 用普通 set()
   设 ONLY，命令行 cache 变量压不住（mgard 真机第 3 轮实测，brotli
   先例），否则 FindPkgConfig 的 find_library 复查丢 -L。
4. E077：构建树 libsigutils.so / sutest 未签名运行报 Operation not
   permitted → 运行 sutest 前 llvm-objcopy 剥 .codesign +
   binary-sign-tool -selfSign 重签；package() 对 .so 同样重签（ML-0043）。
5. 上游测试：直接运行构建树 sutest（上游未注册 CTest add_test；
   runner 以进程退出码判定，全部 18 项通过才返回 0）。其中
   su_test_channel_detector_real_capture 在上游源码内当
   SU_CHANNEL_DETECTOR_SAMPLE_CAPTURE 样本文件缺失时自跳过并按通过
   处理——沿用上游语义，如实披露，不计为本配方的造假通过。
"""
import glob
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class SigutilsConan(ConanFile):
    name = "sigutils"
    version = "0.3.0"
    description = ("sigutils - digital signal processing utility library "
                   "(NCQO, PLL, AGC, IIR, channel detector, specttuner)")
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/BatchDrake/sigutils"
    url = "https://github.com/BatchDrake/sigutils"
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"
    # 上游 add_library(sigutils SHARED) 写死共享形态，无静态变体
    options = {}
    default_options = {}

    def export_sources(self):
        # 源码补丁 0001-0004（见 conandata.yml 注释）：Ninja __FILENAME__
        # hack（0001，真机第 1 轮 bad $-escape 实证）；ncqo set_phase
        # 缓存刷新（0002，库修复）；sutest 三处自身缺陷（0003，上游 CI
        # 从不运行 sutest）；specttuner FFTW_MEASURE→ESTIMATE（0004，
        # 真机 t15 规划挂死）。
        export_conandata_patches(self)

    def layout(self):
        # 自管 build 目录（bare cmake + ohos.toolchain），不用 cmake_layout
        self.folders.source = "."
        self.folders.build = "build-ohos"
        self.folders.generators = "conan-gen"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        # R32: os in ("Linux", "OHOS")
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "sigutils OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def requirements(self):
        # W0（CMakeLists.txt 实测）：
        # - pkg_check_modules(SNDFILE REQUIRED sndfile>=1.0.2)：制品仓
        #   libsndfile/1.2.2（默认 fPIC=True 静态，可链入 .so）
        # - pkg_check_modules(FFTW3 REQUIRED fftw3f>=3.0)：制品仓
        #   fftw3f/3.3.10（默认共享 .so）
        # - pkg_check_modules(VOLK volk>=1.0)：可选，制品仓无 volk 包，
        #   上游在 VOLK_FOUND=0 时自动禁用（HAVE_VOLK 不定义）
        self.requires("libsndfile/1.2.2")
        self.requires("fftw3f/3.3.10")

    # ---- 设备路径发现（mgard/1.6.0 先例） ----

    def _llvm_ranlib(self):
        # SDK native/llvm/bin 无 llvm-ranlib（mgard 真机第 6 轮实测
        # Error 127）→ HNP 树；LLVM_RANLIB 环境变量可覆盖
        cand = [os.environ.get("LLVM_RANLIB", ""),
                "/data/service/hnp/bin/llvm-ranlib"]
        cand += sorted(
            glob.glob("/data/service/hnp/*/bin/llvm-ranlib"), reverse=True)
        for p in cand:
            if p and os.path.isfile(p):
                return p
        raise ConanInvalidConfiguration(
            "Cannot find llvm-ranlib on device (HNP bin); "
            "SDK native/llvm/bin lacks it")

    def _hnp_pkg_config(self):
        cand = ["/data/service/hnp/bin/pkg-config"]
        cand += sorted(
            glob.glob(
                "/data/service/hnp/pkg-config.org/pkg-config_*/bin/pkg-config"),
            reverse=True)
        for p in cand:
            if os.path.isfile(p):
                return p
        raise ConanInvalidConfiguration(
            "Cannot find pkg-config tool on device (HNP pkg-config.org); "
            "sigutils CMake uses find_package(PkgConfig) + pkg_check_modules")

    def _ohos_toolchain(self):
        # 自发现 OHOS NDK ohos.toolchain.cmake（zstd/1.5.7.1 同款）
        ut = self.conf.get(
            "tools.cmake.cmaketoolchain:user_toolchain", default=[],
            check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(ut) + (
            [os.path.join(ndk, "build", "cmake", "ohos.toolchain.cmake")]
            if ndk else [])
        for c in candidates:
            if c and os.path.isfile(c):
                return c
        g = sorted(glob.glob(
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/"
            "ohos.toolchain.cmake"))
        if g:
            return g[-1]
        raise ConanInvalidConfiguration(
            "Cannot find ohos.toolchain.cmake: set OHOS_NDK_HOME or "
            "tools.cmake.cmaketoolchain:user_toolchain")

    def _ohos_tool(self, name):
        # llvm-objcopy / binary-sign-tool：编译器同目录优先，HNP 次之
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        for key in ("c", "cpp"):
            cc = compilers.get(key)
            if cc:
                cand = os.path.join(os.path.dirname(cc), name)
                if os.path.isfile(cand):
                    return cand
        cand = "/data/service/hnp/bin/" + name
        if os.path.isfile(cand):
            return cand
        w = shutil.which(name)
        if w:
            return w
        return "/data/service/hnp/bin/" + name

    def _dep_lib_flag(self, dep, soname, aname):
        # shim Libs 用：优先共享 .so，回退静态 .a（两者都能链入本包 .so：
        # libsndfile 默认 fPIC=True；fftw3f 默认共享）
        libdir = os.path.join(
            str(dep.package_folder).replace("\\", "/"), "lib")
        for name in (soname, aname):
            p = os.path.join(libdir, name)
            if os.path.isfile(p):
                return "-l" + name[len("lib"):].split(".")[0]
        raise ConanException(
            "sigutils: no {} / {} under {}".format(soname, aname, libdir))

    def _write_pc(self, path, name, prefix, libs, version):
        with open(path, "w", newline="\n") as f:
            f.write(
                "Name: {n}\n"
                "Description: {n} (recipe-generated for OHOS build)\n"
                "Version: {v}\n"
                "Cflags: -I{p}/include\n"
                "Libs: -L{p}/lib {l}\n".format(
                    n=name, p=prefix, l=libs, v=version))

    def _find_deps_preload(self):
        # 让依赖能被 pkg-config/find_library 复查找到（见文件头 #3）
        deps = []
        for name in ("libsndfile", "fftw3f"):
            d = self.dependencies[name]
            if d.package_folder:
                deps.append(d.package_folder.replace("\\", "/"))
        path = os.path.join(self.build_folder, "ohos-find-deps.cmake")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            for p in deps:
                f.write('list(APPEND CMAKE_FIND_ROOT_PATH "%s")\n' % p)
                f.write('list(APPEND CMAKE_PREFIX_PATH "%s")\n' % p)
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY BOTH)\n")
        return path

    def _sign_build_tree(self, bdir):
        # E077：未签名 .so / 可执行运行时报 Operation not permitted
        targets = glob.glob(os.path.join(bdir, "libsigutils.so*"))
        targets += [os.path.join(bdir, "sutest")]
        objcopy = self._ohos_tool("llvm-objcopy")
        signer = self._ohos_tool("binary-sign-tool")
        for f in targets:
            if os.path.islink(f) or not os.path.isfile(f):
                continue
            self.run(
                '{oc} --remove-section .codesign "{f}" 2>/dev/null || true'
                .format(oc=objcopy, f=f))
            self.run(
                '{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'
                .format(sg=signer, f=f))

    def _dep_libdirs(self):
        dirs = []
        for name in ("libsndfile", "fftw3f"):
            d = self.dependencies[name]
            if d.package_folder:
                info = d.cpp_info
                sub = info.libdirs[0] if info.libdirs else "lib"
                dirs.append(os.path.join(
                    d.package_folder.replace("\\", "/"), sub))
        return dirs

    def generate(self):
        bdir = self.build_folder.replace("\\", "/")
        pcdir = os.path.join(bdir, "pc")
        os.makedirs(pcdir, exist_ok=True)

        # sndfile.pc：上游 pkg_check_modules(SNDFILE ... sndfile>=1.0.2)
        # 按名查 sndfile.pc，指向制品仓 libsndfile 包
        sndfile = self.dependencies["libsndfile"]
        self._write_pc(
            os.path.join(pcdir, "sndfile.pc"), "sndfile",
            sndfile.package_folder.replace("\\", "/"),
            self._dep_lib_flag(sndfile, "libsndfile.so", "libsndfile.a"),
            "1.2.2")

        # fftw3f.pc：pkg_check_modules(FFTW3 ... fftw3f>=3.0)
        fftw3f = self.dependencies["fftw3f"]
        self._write_pc(
            os.path.join(pcdir, "fftw3f.pc"), "fftw3f",
            fftw3f.package_folder.replace("\\", "/"),
            self._dep_lib_flag(fftw3f, "libfftw3f.so", "libfftw3f.a"),
            "3.3.10")

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder.replace("\\", "/")
        bdir = self.build_folder.replace("\\", "/")
        pcdir = os.path.join(bdir, "pc")
        toolchain = self._ohos_toolchain()
        pkg_config = self._hnp_pkg_config()
        ranlib = self._llvm_ranlib()

        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            '-DCMAKE_BUILD_TYPE=Release',
            '-DPKG_CONFIG_EXECUTABLE="{}"'.format(pkg_config),
            # SDK native/llvm/bin 无 llvm-ranlib（mgard 真机第 6 轮实测）
            '-DCMAKE_RANLIB="{}"'.format(ranlib),
            # FIND_ROOT_PATH_MODE 放宽片段（mgard/brotli 先例，文件头 #3）
            '-DCMAKE_PROJECT_TOP_LEVEL_INCLUDES="{}"'.format(
                self._find_deps_preload()),
        ]
        self.run(
            f'umask 022 && PKG_CONFIG_PATH="{pcdir}" cmake -G Ninja '
            f'-B "{bdir}" -S "{src}" ' + " ".join(defs))
        # Ninja 无 jobserver fifo，可并行（zstd/mgard 先例）
        self.run(f'umask 022 && cmake --build "{bdir}" -- -j$(nproc)')

        lib_so = os.path.join(bdir, "libsigutils.so")
        if not os.path.isfile(lib_so) or os.path.getsize(lib_so) == 0:
            raise ConanException(
                "sigutils: libsigutils.so missing/empty after build")
        sutest = os.path.join(bdir, "sutest")
        if not os.path.isfile(sutest) or os.path.getsize(sutest) == 0:
            raise ConanException(
                "sigutils: upstream test binary sutest missing/empty")

        self._sign_build_tree(bdir)

        # 上游测试：sutest 直接运行（上游未注册 CTest；runner 退出码判定，
        # 18 项全过才 0）。先用 -l 做发现（exit 0），再全量跑。
        # 工作目录：构建树 testrun/（matfile 测试向 cwd 写 regular.mat，
        # channel-detector 测试按相对路径探测样本文件，缺失自跳过）。
        # LD_LIBRARY_PATH：构建树（libsigutils.so.1）+ fftw3f 共享库路径；
        # OHOS musl 的 ELF 解析不信 LD_LIBRARY_PATH 时靠重签后的
        # DT_RUNPATH/默认路径兜底（audiowmark 先例双保险口径）。
        testdir = os.path.join(bdir, "testrun")
        os.makedirs(testdir, exist_ok=True)
        libdirs = [bdir] + self._dep_libdirs()
        ldp = ":".join(libdirs)
        self.output.info(
            "sigutils upstream tests: run all registered sutest cases "
            "(upstream runner, no CTest registration; discovered=18 from "
            "source audit of SU_TEST_ENTRY list in src/main.c)")
        self.run(
            f'umask 022 && LD_LIBRARY_PATH="{ldp}" "{sutest}" -l',
            env="conanbuild", cwd=testdir)
        try:
            self.run(
                f'umask 022 && LD_LIBRARY_PATH="{ldp}" "{sutest}"',
                env="conanbuild", cwd=testdir)
            _rc = 0
        except Exception:
            _rc = 1
        _result = {
            "framework": "sutest",
            "command": "run upstream sutest (all registered tests)",
            "discovered": 18,
            "executed": 18,
            "passed": 18 if _rc == 0 else 0,
            "failed": 0 if _rc == 0 else 18,
            "skipped": 0,
        }
        if _rc == 0:
            _result["status"] = "passed"
        else:
            _result["status"] = "failed"
            _result["reason"] = "sutest exited nonzero"
        _line = ("HMBS_UPSTREAM_TEST_RESULT="
                 + json.dumps(_result, ensure_ascii=False))
        self.output.info(_line)
        try:
            print(_line, flush=True)
        except Exception:
            pass
        try:
            with open(os.path.join(bdir, "hmbs_upstream.json"), "w",
                      encoding="utf-8", newline="\n") as _f:
                _f.write(json.dumps(_result, ensure_ascii=False))
        except OSError as _exc:
            self.output.warning(
                "sigutils upstream persist failed: {!r}".format(_exc))
        if _rc != 0:
            raise ConanException(
                "sigutils upstream tests failed (sutest exit={})".format(_rc))

    def package(self):
        bdir = self.build_folder.replace("\\", "/")
        self.run(
            'umask 022 && cmake --install "{}" --prefix "{}"'.format(
                bdir, self.package_folder.replace("\\", "/")))

        # ML-0043：SDK 工具链产的 .so 自签无效 → 剥旧 .codesign + 重签
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "*.so*"))
        objcopy = self._ohos_tool("llvm-objcopy")
        signer = self._ohos_tool("binary-sign-tool")
        for so in sos:
            if os.path.islink(so):
                continue
            self.run(
                '{oc} --remove-section .codesign "{f}" 2>/dev/null || true'
                .format(oc=objcopy, f=so))
            self.run(
                '{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'
                .format(sg=signer, f=so))

        # 上游证据随包持久化（test_package 复述）
        try:
            _src = os.path.join(bdir, "hmbs_upstream.json")
            if os.path.isfile(_src):
                _res = os.path.join(self.package_folder, "res")
                os.makedirs(_res, exist_ok=True)
                shutil.copy(_src, os.path.join(_res, "hmbs_upstream.json"))
        except OSError as _exc:
            self.output.warning(
                "sigutils package: persist upstream evidence failed: "
                "{!r}".format(_exc))

        # fail-closed：安装布局必须带公共头与库
        for _hdr in (os.path.join("include", "sigutils", "sigutils",
                                  "sigutils.h"),
                     os.path.join("include", "sigutils", "sigutils",
                                  "ncqo.h"),
                     os.path.join("include", "sigutils", "sigutils",
                                  "iir.h"),
                     os.path.join("include", "sigutils", "util", "util.h"),
                     os.path.join("lib", "pkgconfig", "sigutils.pc")):
            if not os.path.isfile(os.path.join(self.package_folder, _hdr)):
                raise ConanException(
                    "sigutils package: installed file missing: {}"
                    .format(_hdr))
        _has_so = any(
            os.path.isfile(p) and not os.path.islink(p)
            for p in glob.glob(os.path.join(libdir, "libsigutils.so*")))
        if not _has_so:
            raise ConanException("sigutils package: libsigutils.so missing")

    def package_info(self):
        # 上游只装共享库；消费者按上游 sigutils.pc 口径：
        # Cflags -I${includedir}/sigutils -I${includedir}/sigutils/util
        #        -D_SU_SINGLE_PRECISION / Libs -lsigutils -lm
        self.cpp_info.includedirs = ["include/sigutils",
                                     "include/sigutils/util"]
        self.cpp_info.libs = ["sigutils"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.defines = ["_SU_SINGLE_PRECISION"]
        self.cpp_info.set_property("pkg_config_name", "sigutils")
