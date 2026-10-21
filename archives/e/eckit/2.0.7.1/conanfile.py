#!/usr/bin/env python3
"""Conan recipe — eckit 2.0.7 (cmake)"""
from conan import ConanFile
from conan.tools.files import collect_libs, get, save
import os
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
import glob
import shutil
import struct
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches


class EckitConan(ConanFile):
    name = "eckit"
    version = "2.0.7.1"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        self.requires("ecbuild/3.15.0")
        self.requires("libaec/1.1.7")
        self.requires("libzip/1.11.4")
        self.requires("bzip2/1.0.8")
        self.requires("eigen/3.4.0")
        self.requires("lz4/1.10.0")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def generate(self):
        tc = CMakeToolchain(self)
        # ★ 这一行是本路线的全部意义所在。
        # os=OHOS 时 conan 默认把 CMAKE_SYSTEM_NAME 设成 "HarmonyOS"，而 cmake 装的平台文件叫
        # Modules/Platform/OHOS.cmake（内容就一行 include(Platform/Linux)），**没有 HarmonyOS.cmake**。
        # 名字对不上时 cmake 不会报错退出，只打一句 "System is unknown to cmake" 就继续，
        # 把一批平台变量留空——其中 CMAKE_SHARED_LIBRARY_SONAME_C_FLAG 为空，
        # 于是链接命令里没有 -Wl,-soname, → 产物没有 DT_SONAME、也不生成版本软链。
        #
        # 无 SONAME 会**传染给下游**：链接器会把本库的绝对路径原样写进消费方的 DT_NEEDED，
        # 烤死包目录哈希，换机器/清 cache 后消费方在加载期炸（expat → fontconfig 实证）。
        tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
        # 不设则 CMAKE_SYSTEM_PROCESSOR 为 "unknown"，上游按它分支的判断（SIMD/汇编选择等）会走错支。
        tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        # 64 位默认可能装到 lib64/，而 conan cpp_info.libdirs 与 test_package 找 lib/。
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["BUILD_SHARED_LIBS"] = True
        tc.variables["ENABLE_MPI"] = "OFF"
        tc.variables["ENABLE_ECKIT_CMD"] = "OFF"
        tc.variables["ENABLE_BUILD_TOOLS"] = "OFF"
        tc.variables["ENABLE_TESTS"] = "ON"
        tc.variables["ENABLE_EIGEN"] = "ON"
        tc.variables["ENABLE_AEC"] = "ON"
        tc.variables["ENABLE_ZIP"] = "ON"
        tc.variables["ENABLE_BZIP2"] = "ON"
        tc.variables["ENABLE_LZ4"] = "ON"
        tc.variables["ENABLE_RADOS"] = "OFF"
        tc.variables["ENABLE_MKL"] = "OFF"
        tc.variables["ENABLE_OMP"] = "OFF"
        tc.variables["ENABLE_SNAPPY"] = "OFF"
        # §10 硬口径：上游测试必须真实执行。门控变量是 ecbuild 的 **ENABLE_TESTS**（它置 eckit_HAVE_TESTS，顶层 CMakeLists:348 才 add_subdirectory(tests|regressions)）；只设 CTest 的 BUILD_TESTING 不生效——实测 cache ENABLE_TESTS:BOOL=OFF + "Feature TESTS disabled" + ctest -N Total Tests: 0。
        tc.variables["BUILD_TESTING"] = "ON"
        # ── ecbuild 接线（手工，原因见下）─────────────────────────────────
        # eckit 的第 14 行是：
        #   find_package( ecbuild 3.7 REQUIRED HINTS ${CMAKE_CURRENT_SOURCE_DIR}
        #                                             ${CMAKE_CURRENT_SOURCE_DIR}/../ecbuild)
        # 带 HINTS 且我们把 CMAKE_SYSTEM_NAME 设成了 OHOS（CMAKE_CROSSCOMPILING=TRUE），
        # find_package 会走 CMAKE_FIND_ROOT_PATH 过滤，CMakeDeps 放在 generators 里的
        # config 可能被挡掉——实测报 "Could not find a package configuration file
        # provided by ecbuild"，而那个文件明明已经生成了。
        # 直接给 ecbuild_DIR 指到包内宏目录，绕过搜索逻辑（skill「cmake 库依赖库」一节的做法）。
        _ecb = self.dependencies["ecbuild"].package_folder
        tc.variables["ecbuild_DIR"] = _ecb + "/share/ecbuild/cmake"
        tc.variables["ecbuild_ROOT"] = _ecb
        # 让 ecbuild 的宏目录进 CMAKE_MODULE_PATH，include(ecbuild) 才找得到入口
        tc.variables["CMAKE_MODULE_PATH"] = _ecb + "/share/ecbuild/cmake"
        # 我们把 CMAKE_SYSTEM_NAME 设成 OHOS → CMAKE_CROSSCOMPILING=TRUE →
        # find_package 的 config 搜索会走 CMAKE_FIND_ROOT_PATH 过滤。
        # 依赖的包目录虽然在 root path 里，但 MODE_PACKAGE 若为 ONLY，
        # 命中范围仍可能与预期不符。显式放宽这三项（skill「cmake 库依赖库」一节）。
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_INCLUDE"] = "BOTH"
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_LIBRARY"] = "BOTH"
        # ── libzip 目标命名空间钩子（回合19，一手证据）────────────────────────────
        # conan CMakeDeps 给 libzip 生成的目标是 **libzip::libzip**（generators/libzipTargets.cmake:17），
        # 而系统 libzip 自带的 config 与上游 src/eckit/geo/CMakeLists.txt:209（含本包 0005 补丁）用的名字
        # 是 **libzip::zip**。实测 CMakeCache 里 libzip_DIR 已指向 generators ⇒ CONFIG 模式确实命中（不是
        # ecbuild MODULE 模式的『假 found、无 imported target』），缺的只是命名空间；不补则 Generate 阶段报
        # Target "eckit_geo" links to: libzip::zip but the target was not found（diag-test-4.log:264-278）。
        # 做法=CMake 官方钩子 CMAKE_PROJECT_eckit_INCLUDE：project(eckit)（CMakeLists.txt:16）之后、toolchain
        # 已加载时补一个 ALIAS。不改上游语义、不加假头、不用 --build=missing 绕过。
        _zip_hook = os.path.join(self.source_folder, "eckit_adapt_libzip.cmake")
        save(self, _zip_hook, "".join([
            "# eckit OHOS 适配：conan CMakeDeps 生成 libzip::libzip，上游链接 libzip::zip\n",
            "find_package(libzip CONFIG REQUIRED)\n",
            "if(NOT TARGET libzip::zip)\n",
            "  add_library(libzip::zip ALIAS libzip::libzip)\n",
            "endif()\n",
        ]))
        tc.cache_variables["CMAKE_PROJECT_eckit_INCLUDE"] = _zip_hook

        tc.generate()
        # 走这条路线的**理由**：依赖由 CMakeDeps 自动接线，不必像裸 cmake 路那样
        # 逐个手工补 -DX_DIR=... / 预设 find 缓存变量。
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # ⚠️ **必须走命令行 -D，不能只靠 tc.variables**。
        # eckit 的 CMakeLists 第 14 行 find_package(ecbuild) 在第 16 行 project() **之前**，
        # 而 CMAKE_TOOLCHAIN_FILE 是在 project()/enable_language() 时才被加载的 ——
        # 那之前 toolchain 里设的 ecbuild_DIR / CMAKE_PREFIX_PATH / CMAKE_MODULE_PATH
        # **统统还不存在**。实测 --debug-find-pkg=ecbuild 的搜索路径里
        # 完全没有依赖包目录，只有环境默认路径。
        # 命令行 -D 建的是 cache 项，在任何 CMakeLists 语句之前就已生效。
        _ecb = self.dependencies["ecbuild"].package_folder
        # LZ4 的老式变量接线（见下方说明）
        _l = self.dependencies["lz4"].cpp_info
        _lz4_inc = _l.includedirs[0] if _l.includedirs else ""
        _lz4_libdir = _l.libdirs[0] if _l.libdirs else ""
        _lz4_name = _l.libs[0] if _l.libs else "lz4"
        # **不要拼文件名**。第一版写死 lib<name>.so，实际包里不是这个名字，
        # make 报 "No rule to make target '.../liblz4.so'"。
        # 实际去目录里找：优先无版本号的 .so（链接用），退而取带版本的，再退静态库。
        import glob as _glob
        _cands = (sorted(_glob.glob(_lz4_libdir + "/lib" + _lz4_name + ".so")) or
                  sorted(_glob.glob(_lz4_libdir + "/lib" + _lz4_name + ".so.*")) or
                  sorted(_glob.glob(_lz4_libdir + "/lib" + _lz4_name + ".a")))
        _lz4_lib = _cands[0] if _cands else ""
        self.output.info("LZ4_LIBRARIES 解析为: %s（目录 %s 内容: %s）"
                         % (_lz4_lib, _lz4_libdir,
                            ", ".join(sorted(__import__("os").listdir(_lz4_libdir))[:8])
                            if _lz4_libdir else "-"))
        cmake.configure(build_script_folder="", cli_args=[
            '-Decbuild_DIR=%s/share/ecbuild/cmake' % _ecb,
            # ecbuild 的 OS 白名单没有 HarmonyOS，上游报错里给的开关
            '-DDISABLE_OS_CHECK=ON',
            # eckit 对 LZ4 用**老式变量**接线（src/eckit/CMakeLists.txt:926/934
            # 直接引用 "${LZ4_INCLUDE_DIRS}" / "${LZ4_LIBRARIES}"），
            # 而 CMakeDeps 只生成 modern target `lz4::lz4`、不设这两个变量 →
            # 变量为空 → `#include "lz4.h"` 找不到头。
            #
            # ⚠️ 对照：同一文件 940 行的 AEC 走的是 target（$<...:libaec::aec>），
            # 所以 libaec 不用额外接线就生效。**同一个库里两种风格并存**——
            # 不能因为一个依赖通了就假定其余的也通，得逐个看它在 CMakeLists 里怎么被引用。
            '-DLZ4_INCLUDE_DIRS=%s' % _lz4_inc,
            '-DLZ4_LIBRARIES=%s' % _lz4_lib,
            # 同 generate() 内说明：命令行再给一次（本配方已证实 tc.variables 在 project() 前不生效，
            # 而 cache_variables 进的是 CMakePresets，-D 是双保险，两处同值不冲突）
            "-DCMAKE_PROJECT_eckit_INCLUDE=%s" % os.path.join(self.source_folder, "eckit_adapt_libzip.cmake"),
        ])
        cmake.build()
        # 上游 216 个注册用例已在本设备**全量真跑两次**（create#5 93.01s、create#6 91.07s，
        # 两次均为 211 通过 / 5 失败，逐条首错原文与签名见 notes.md「回合 23 定案」）。
        # 下面这 5 项逐条为平台受限，按 §10「个别用例平台受限才逐项 test_skipped 附技术原因」豁免，
        # 其余 211 项在本门内继续真实执行；**不减用例、不缩分母、不重分类**：
        #   eckit_test_container_sharedmemarray        SysV IPC 被 seccomp 击杀：si_code=1(SYS_SECCOMP)
        #       si_syscall=190(semget)，帧 <semget+0x4c>@ld-musl ← <eckit::Semaphore::Semaphore+0x8c>@libeckit；
        #       POSIX shm_open/ftruncate/mmap 实测可用、shmctl/semctl/statx 返 errno ⇒ 仅"创建/挂载"被拦
        #   eckit_test_filesystem_filemode             HMDFS 默认文件模式与 Unix 契约不同（知识库 E011）
        #   eckit_test_log                             unlink 失败时 musl 不填 errno → "No error information"
        #   eckit_test_maths_floating_point_exceptions 上游 WILL_FAIL 契约（ctest --show-only=json-v1：216 项中
        #       仅此一项带 WILL_FAIL ⇒ 期望失败未发生，非本次适配引入）
        #   eckit_test_safe_casts                      默认 ABI 的 char 签名差异（同树 -fsigned-char 对照 RC=0）
        # 排除点是 CMake/ctest 官方支持的机制：本树生成器 Unix Makefiles，Makefile 的 test 规则原文
        # `ctest $(ARGS)`，故经 ARGS 注入 --exclude-regex；正则**必须锚定全名**（已实测：不锚定会连带
        # 误排 eckit_test_log_channels 等同族兄弟，216→205）。`$$` 是 make 的字面 `$` 转义。
        cmake.test(build_tool_args=[
            'ARGS=--output-on-failure -E '
            '"^eckit_test_(container_sharedmemarray|filesystem_filemode|log|'
            'maths_floating_point_exceptions|safe_casts)$$"'
        ])

    def package(self):
        CMake(self).install()
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    @staticmethod
    def _elf_has_codesign_section(path):
        """走真实 ELF64 节头表。按文件字节搜段名会把 objcopy 删段后残留的 shstrtab
        条目也算命中——那正是这条检查不能接受的假通过。"""
        with open(path, "rb") as fh:
            head = fh.read(64)
            if len(head) < 64 or head[:4] != b"\x7fELF" or head[4] != 2 or head[5] != 1:
                return False
            e_shoff = struct.unpack_from("<Q", head, 40)[0]
            e_shentsize = struct.unpack_from("<H", head, 58)[0]
            e_shnum = struct.unpack_from("<H", head, 60)[0]
            e_shstrndx = struct.unpack_from("<H", head, 62)[0]
            if not e_shoff or not e_shnum:
                return False
            fh.seek(e_shoff + e_shstrndx * e_shentsize)
            strtab_sh = fh.read(e_shentsize)
            str_off = struct.unpack_from("<Q", strtab_sh, 24)[0]
            str_size = struct.unpack_from("<Q", strtab_sh, 32)[0]
            fh.seek(str_off)
            strtab = fh.read(str_size)
            for i in range(e_shnum):
                fh.seek(e_shoff + i * e_shentsize)
                name_off = struct.unpack_from("<I", fh.read(e_shentsize), 0)[0]
                end = strtab.find(b"\x00", name_off)
                if strtab[name_off:end] == b".codesign":
                    return True
        return False

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名，否则报 Permission denied /
        # Operation not permitted（cmake/SDK-toolchain 产的自签无效，且 conan install 复制会破坏链接器自签）。
        # ① lib/ 的 .so  ② bin/ 的 ELF 可执行文件（llvm-config/xxx CLI 等）——产可执行文件的包必须签 bin。
        # 硬化三条（照本仓 json-glib 1.10.8.1 已实测做法）：签名器与 objcopy **运行时定位**
        # （写死 /data/service/hnp/bin 在新机 rc=127）、缺件即 **raise 而非 warning+skip**、
        # 签完**逐个断言 .codesign 真在节头表里**——"搬了这段代码"不等于"签上了"。
        if str(self.settings.os) != "OHOS" or not self.options.get_safe("shared"):
            return
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        # 只签真实 ELF：版本化 .so 的软链会对同一目标重复签
        targets = [f for f in targets if not os.path.islink(f)]
        if not targets:
            return
        home = os.path.expanduser("~")
        candidates_objcopy = [
            "/data/service/hnp/bin/llvm-objcopy",
            os.path.join(home, "usr/local/bin/llvm-objcopy"),
            os.path.join(home, ".harmonybrew/bin/llvm-objcopy"),
            shutil.which("llvm-objcopy") or "",
        ]
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        if cc:
            candidates_objcopy.insert(0, os.path.join(os.path.dirname(cc), "llvm-objcopy"))
        objcopy = next((c for c in candidates_objcopy if c and os.path.isfile(c)), None)
        candidates_signer = [
            "/data/service/hnp/bin/binary-sign-tool",
            os.path.join(home, "usr/local/bin/binary-sign-tool"),
            os.path.join(home, ".harmonybrew/bin/binary-sign-tool"),
            shutil.which("binary-sign-tool") or "",
        ]
        signer = next((c for c in candidates_signer if c and os.path.isfile(c)), None)
        missing = []
        if not objcopy:
            missing.append("llvm-objcopy")
        if not signer:
            missing.append("binary-sign-tool")
        if missing:
            checked = ", ".join(c for c in candidates_objcopy + candidates_signer if c)
            raise ConanException(
                "OHOS codesign is mandatory for this package but %s was not found (checked: %s). "
                "Refusing to publish an unsigned artifact that the loader rejects with rc=127."
                % (", ".join(missing), checked))
        self.output.info("OHOS codesign: signer=%s objcopy=%s targets=%d"
                         % (signer, objcopy, len(targets)))
        unsigned = []
        for f in targets:
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))
            if not self._elf_has_codesign_section(f):
                unsigned.append(os.path.relpath(f, self.package_folder))
        if unsigned:
            raise ConanException(
                "binary-sign-tool returned success but no .codesign section is present in: %s"
                % ", ".join(unsigned))

    def package_info(self):
        explicit_libs = ['eckit']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        # 实包确有 bin/eckit-version（create#7 内 35328B），声明 bindirs 使包级 commands.json(binary:true) 与 PF8 配方闸自洽
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "eckit")
        self.cpp_info.set_property("cmake_target_name", "eckit::eckit")
        self.cpp_info.set_property("pkg_config_name", "eckit")
        import os
        for _env in []:
            _k, _v = _env.split("=", 1)
            self.runenv_info.define_path(_k, os.path.join(self.package_folder, _v))
