#!/usr/bin/env python3
"""Conan recipe — intel-oneapi-dpcpp 2026.0.0_220 (candidate nightly snapshot).

版本映射未确认：上游不存在精确 2026.0.0_220 tag。
本配方使用候选 nightly 快照 nightly-2026-07-30
(commit 9084ec7d34d89b9b63613665f5bf8b9757566c58,
 tarball SHA-256 16d2da84a6d802fb2fa32f09fc3bfa2f82e4b208d225f501a93564c2a4691be1)。
不得在配方/报告/PR 中宣称已确认对应 Intel 产品版本。

构建说明（与执行端已验证流程一致）：
- bootstrap host compiler: OHOS SDK Clang 15 (aarch64-unknown-linux-ohos)
- 最终 DPC++ 工具链来自本构建产物 clang-23，不使用系统 Clang 冒充
- CMAKE_SYSTEM_NAME=Linux（OHOS 为 Linux ABI，host triple 仍为 aarch64-unknown-linux-ohos）
- errc_exit_code=0 预设（CMake 官方 TryRunResults 交叉编译机制）
- HarmonyOS 平台模块经 CMAKE_MODULE_PATH 注入（patches/Platform/HarmonyOS.cmake）
- UR lib loader OHOS 条件化补丁 + config.guess HarmonyOS 补丁（patches/）
- UR_ENABLE_SANITIZER/SYMBOLIZER=OFF（OHOS 无 gnu/lib-names.h 等 glibc 头，真实平台缺口）
- 网络可用时依赖由上游 FetchContent 拉取；执行端可注入本地缓存镜像
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout

class InteloneapiDpcppConan(ConanFile):
    name = "intel-oneapi-dpcpp"
    version = "2026.0.0_220"
    description = "intel-oneapi-dpcpp 2026.0.0_220 (candidate nightly-2026-07-30, version mapping UNCONFIRMED)"
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://github.com/intel/llvm"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # hwloc 补丁用于 build() 中预置的 hwloc 源码，非主源码树补丁，
        # 需手动复制进 export_sources 以便干净环境可复现。
        copy(self, "patches/hwloc/hwloc-config-guess-ohos.patch", self.recipe_folder,
             self.export_sources_folder)
        # HarmonyOS 平台模块（CMAKE_MODULE_PATH 注入 Platform/HarmonyOS.cmake 所需）。
        # copy() 保留相对结构：patches/Platform/HarmonyOS.cmake → <export>/patches/Platform/HarmonyOS.cmake
        copy(self, "patches/Platform/HarmonyOS.cmake", self.recipe_folder,
             self.export_sources_folder)

    def layout(self):
        basic_layout(self)

    def source(self):
        # 默认使用 conandata.yml 的公共 GitHub URL（干净环境可复现）。
        # 允许执行端通过环境变量覆盖为本地镜像 URL（CI 提供本地缓存时使用），
        # 配方本身不硬编码任何私有绝对路径。
        url = os.environ.get("OHOS_SRC_URL", self.conan_data["sources"]["url"])
        sha256 = os.environ.get("OHOS_SRC_SHA256", self.conan_data["sources"]["sha256"])
        get(self, url=url, sha256=sha256, strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        import shlex
        import subprocess
        # UMF 的 hwloc ExternalProject 使用 SOURCE_DIR（UMF 副本经本地依赖镜像注入）。
        # 干净构建目录中需预置 hwloc 源码并打上 HarmonyOS config.guess 补丁。
        bdir = self.build_folder
        hwloc_src_dir = os.path.join(bdir, "hwloc_targ-prefix", "src", "hwloc_targ")
        if not os.path.isdir(hwloc_src_dir):
            os.makedirs(hwloc_src_dir, exist_ok=True)
            hwloc_url = "https://download.open-mpi.org/release/hwloc/v2.13/hwloc-2.13.0.tar.gz"
            hwloc_mirror = os.environ.get("OHOS_MIRROR_HWLOC", "")
            if hwloc_mirror:
                hwloc_url = hwloc_mirror
            get(self, url=hwloc_url, sha256="1514a5253f0a5c23bc006d3bdd30a6f6125c9a8dc9b5fa4984913d1fff45315d",
                destination=hwloc_src_dir, filename="hwloc-2.13.0.tar.gz",
                strip_root=True)
            # 应用 HarmonyOS config.guess 补丁
            p = os.path.join(self.export_sources_folder, "patches", "hwloc", "hwloc-config-guess-ohos.patch")
            subprocess.run(["patch", "-p1", "-i", p], cwd=hwloc_src_dir, check=True)

        # UR 的 exp-headers（intel/compute-runtime 稀疏 level_zero/include）：
        # 干净构建中预置稀疏 checkout（网络抖动时重试），避免 configure 期拉取失败。
        # 使用 self.run 以加载 profile buildenv（git 位于 OHOS SDK bin）。
        ceh = os.path.join(bdir, "content-exp-headers")
        if not os.path.isdir(os.path.join(ceh, "level_zero", "include")):
            os.makedirs(os.path.dirname(ceh), exist_ok=True)
            # 优先使用执行端注入的已验证 exp-headers 副本（避免构建期 GitHub 网络抖动）
            seeded = os.environ.get("OHOS_MIRROR_EXP_HEADERS", "")
            if seeded and os.path.isdir(os.path.join(seeded, "level_zero", "include")):
                self.run(f"cp -r {shlex.quote(seeded)} {shlex.quote(ceh)}", env="conanbuild")
            else:
                git_cmd = "git"
                # CI worker 网络受限（github.com:443 不可达，gh-proxy 类镜像可达，
                # 与 conandata.yml sources.url 镜像列表一致）：按序尝试镜像源。
                cr_candidates = []
                injected = os.environ.get("OHOS_MIRROR_COMPUTE_RUNTIME", "").strip()
                if injected:
                    cr_candidates.append(injected)
                cr_candidates += [
                    "https://gh-proxy.com/https://github.com/intel/compute-runtime.git",
                    "https://mirror.ghproxy.com/https://github.com/intel/compute-runtime.git",
                    "https://ghproxy.com/https://github.com/intel/compute-runtime.git",
                    "https://gitclone.com/github.com/intel/compute-runtime.git",
                    "https://github.com/intel/compute-runtime.git",
                ]
                cloned = False
                for cr_url in cr_candidates:
                    for attempt in range(2):
                        rc = self.run(
                            f"{git_cmd} clone --depth 1 --branch 26.18.38308.1 --no-checkout "
                            f"--filter=blob:none --sparse "
                            f"{cr_url} {ceh}",
                            env="conanbuild", ignore_errors=True)
                        if rc == 0:
                            cloned = True
                            break
                        self.run(f"rm -rf {ceh}", env="conanbuild", ignore_errors=True)
                        self.output.warning(
                            f"compute-runtime sparse clone failed ({cr_url}, attempt {attempt + 1})")
                    if cloned:
                        break
                if not cloned:
                    self.output.error(
                        "compute-runtime sparse clone failed on all candidate URLs; "
                        "UR exp-headers 将缺失，构建后续步骤会报错")
                self.run(f"{git_cmd} -C {ceh} sparse-checkout set level_zero/include", env="conanbuild")
                self.run(f"{git_cmd} -C {ceh} checkout", env="conanbuild")

        # ---- configure: 与执行端已验证参数一致 ----
        src = self.source_folder
        inc = " ".join([
            f"-isystem {os.environ.get('OHOS_LIBCXX', '/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/include/libcxx-ohos/include/c++/v1')}",
            f"-isystem {os.environ.get('OHOS_SYSROOT1', '/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include/aarch64-linux-ohos')}",
            f"-isystem {os.environ.get('OHOS_SYSROOT2', '/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include')}",
        ])
        cfg = [
            "python3", f"{src}/buildbot/configure.py",
            "-s", src, "-o", bdir, "-t", "Release",
            "--cmake-opt=-DCMAKE_MODULE_PATH=" + os.path.join(self.export_sources_folder, "patches"),
            "--cmake-opt=-DSYCL_LIBDEVICE_CXX_FLAGS=" + inc,
            "--cmake-opt=-DSYCL_OHOS_INCLUDE=" + os.environ.get("OHOS_SYCL_INCLUDE", ""),
            "--cmake-opt=-DUR_ENABLE_SANITIZER=OFF",
            "--cmake-opt=-DUR_ENABLE_SYMBOLIZER=OFF",
        ]
        # 本地依赖镜像注入（可选）：CI 可通过环境变量提供本地缓存，
        # 避免构建期网络抖动；缺省时由上游 FetchContent 从 GitHub 拉取。
        mirrors = [
            ("FETCHCONTENT_SOURCE_DIR_VC-INTRINSICS", "OHOS_MIRROR_VC_INTRINSICS"),
            ("FETCHCONTENT_SOURCE_DIR_EMHASH", "OHOS_MIRROR_EMHASH"),
            ("FETCHCONTENT_SOURCE_DIR_UNIFIED-MEMORY-FRAMEWORK", "OHOS_MIRROR_UMF"),
            ("FETCHCONTENT_SOURCE_DIR_LEVEL-ZERO-LOADER", "OHOS_MIRROR_L0"),
            ("FETCHCONTENT_SOURCE_DIR_OCL-HEADERS", "OHOS_MIRROR_OCL_HEADERS"),
            ("FETCHCONTENT_SOURCE_DIR_OCL-ICD", "OHOS_MIRROR_OCL_ICD"),
            ("FETCHCONTENT_SOURCE_DIR_PARALLEL-HASHMAP", "OHOS_MIRROR_PARALLEL_HASHMAP"),
            ("LLVM_EXTERNAL_SPIRV_HEADERS_SOURCE_DIR", "OHOS_MIRROR_SPIRV_HEADERS"),
        ]
        for cmake_var, env_var in mirrors:
            val = os.environ.get(env_var, "")
            if val:
                cfg.append(f"--cmake-opt=-D{cmake_var}={val}")
        import shlex
        self.run(" ".join(shlex.quote(a) for a in cfg), cwd=bdir)

        # ---- 自举：先用系统 clang 15 构建出 bin/clang-23，再用它编译 SYCL runtime ----
        # 原因：本 nightly 的 SYCL runtime 源码需要较新编译器（PropsHolder literal type），
        # 系统 clang 15 编译报错；与执行端手工验证一致的方案是构建出 clang-23 后自举。
        self.run(f"cmake --build {bdir} --target clang -j 4", cwd=bdir)

        # 将 SYCL 相关 ninja 编译规则切换到 clang-23（自举），并注入 OHOS libc++/sysroot 头路径
        rules = os.path.join(bdir, "CMakeFiles", "rules.ninja")
        with open(rules, "r", encoding="utf-8") as f:
            content = f.read()
        old_cmd = ("command = ${LAUNCHER}${CODE_CHECK}/data/service/hnp/bin/clang++ "
                   "$DEFINES $INCLUDES $FLAGS -MD -MT $out -MF $DEP_FILE -o $out -c $in")
        new_cc = os.path.join(bdir, "bin", "clang-23")
        new_cmd = (f"command = ${{LAUNCHER}}${{CODE_CHECK}}{new_cc} "
                   f"{inc} $DEFINES $INCLUDES $FLAGS -MD -MT $out -MF $DEP_FILE -o $out -c $in")
        n = 0
        lines = []
        in_rule = False
        rule_name = ""
        for line in content.split("\n"):
            if line.startswith("rule "):
                in_rule = True
                rule_name = line.split()[1]
            elif in_rule and line.startswith("  "):
                pass
            elif in_rule and not line.strip():
                in_rule = False
            if in_rule and "sycl" in rule_name and old_cmd in line:
                line = line.replace(old_cmd, new_cmd)
                n += 1
            lines.append(line)
        if n > 0:
            with open(rules, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            self.output.info(f"bootstrap: switched {n} SYCL ninja rules to clang-23")

        # ---- build: deploy-sycl-toolchain -j4 ----
        self.run(f"python3 {src}/buildbot/compile.py -s {src} -o {bdir} -j 4 -t deploy-sycl-toolchain",
                 cwd=bdir)

    def package(self):
        # 不使用 conan copy() 工具：其在 HMFS 上复制 install 产物会丢失
        # 可执行文件属性（test_package 执行 clang++ 报 Operation not permitted）。
        # 直接从 conan 构建产物目录 shell cp 复制，保留可执行标签
        # （已在 exec-stage 探针验证 dev_adhoc_bin_file/hishell 均可执行）。
        import shlex
        bdir = self.build_folder
        # basic_layout() 可能已让 build_folder 指向 build-release 子目录，
        # 防御性选择实际包含 bin/ 的产物根目录。
        rel = bdir
        for cand in (bdir, os.path.join(bdir, "build-release")):
            if os.path.isdir(os.path.join(cand, "bin")):
                rel = cand
                break
        self.output.info(f"package(): packaging from {rel}")
        for sub in ("bin", "lib", "include"):
            src = os.path.join(rel, sub)
            if os.path.isdir(src):
                self.run(f"mkdir -p {shlex.quote(os.path.join(self.package_folder, sub))}")
                self.run(f"cp -r {shlex.quote(src)}/. {shlex.quote(os.path.join(self.package_folder, sub))}/")
        # 安装 manifest（可选元数据）
        mf = os.path.join(rel, "install")
        if os.path.isdir(mf):
            self.run(f"mkdir -p {shlex.quote(os.path.join(self.package_folder, 'install-meta'))}")

    def package_info(self):
        bindir = os.path.join(self.package_folder, "bin")
        libdir = os.path.join(self.package_folder, "lib")
        self.output.info(f"DPC++ clang++: {os.path.join(bindir, 'clang++')}")
        self.output.info(f"libsycl.so: {os.path.join(libdir, 'libsycl.so')}")
        self.env_info.PATH.append(bindir)
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
