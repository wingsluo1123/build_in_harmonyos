#!/usr/bin/env python3
"""Conan recipe for mfgtools (NXP uuu) 1.5.243 — Universal Update Utility（C++ / CMake）。

**上游与来源**：任务平台条目名是 `mfgtools 1.5.243`，上游是 **NXPmicro/mfgtools**，产物叫 **`uuu`**
（Universal Update Utility，i.MX 系列烧写工具）。源码**只以 GitHub release 资产发布**：
`https://github.com/NXPmicro/mfgtools/releases/download/uuu_1.5.243/uuu_source-uuu_1.5.243.tar.gz`，
sha256 `dee3be0f337c631bf93232f5ea42440f07782ce005c9219a14731d66bbe83658`
（与 AUR 的 PKGBUILD 记录一致，本地实测下载后 sha256 相同 ✓）。

**依赖**（`libuuu/CMakeLists.txt` 与 `uuu/CMakeLists.txt` 里 REQUIRED 的那些，**全部已在仓库归档** →
按"算依赖先扣掉仓库已有"的口径不构成阻塞）：libusb-1.0 / libzstd / tinyxml2 / zlib / bzip2，
另有 OpenSSL（上游为 `find_package(OpenSSL)`，非 REQUIRED）。

**上游测试**：**没有**（源码树没有 test/tests 目录，CMake 也没有 `enable_testing`/`add_test`）→ 按仓库既有
做法（rp / indi-armadillo-platypus 那次）在配方里**补能真跑的功能级测试**：上游 CLI 支持 `-h`/`help`，
构建完成后直接运行产物断言 `uuu -h` rc=0 且打印用法。构成在 test_package/MANIFEST.yml 里摊开，
**不谎称"上游自带测试"**。
"""
import glob
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get
from conan.tools.gnu import PkgConfigDeps


class MfgtoolsConan(ConanFile):
    name = "mfgtools"
    version = "1.5.243"
    description = ("NXP mfgtools / uuu — Universal Update Utility, an i.MX "
                   "series flashing tool (C++ / CMake)")
    license = "BSD-3-Clause"
    homepage = "https://github.com/NXPmicro/mfgtools"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        # 全部取自仓库已归档版本（口径：先扣掉仓库已有依赖）
        self.requires("libusb/1.0.27")
        self.requires("zstd/1.5.7.1")
        self.requires("tinyxml2/11.0.0")
        self.requires("zlib/1.3.2")
        self.requires("bzip2/1.0.8")
        self.requires("openssl/3.5.6")

    def source(self):
        spec = dict(self.conan_data["sources"])
        spec.pop("note", None)
        get(self, **spec, strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        # 上游 libuuu/uuu 的 CMake 用 pkg_check_modules(... REQUIRED libusb-1.0/libzstd/tinyxml2/zlib)
        # 找依赖 → 必须让 conan 生成 .pc 文件，否则 CMake 直接 "required packages were not found"
        PkgConfigDeps(self).generate()
        tc = CMakeToolchain(self)
        # conan 环境下 FindOpenSSL 不会自己找到 conan 的 openssl 包 → 显式给根目录
        # （找不到时上游 UUUSSL 未定义，而 http.cpp:506 的 base64_encode 使用处没加同样守卫 → 编译错）
        tc.cache_variables["OPENSSL_ROOT_DIR"] = self.dependencies["openssl"].package_folder
        # ⚠️ 跳过 CMake 编译器自检：CI Worker 上 fork/exec 配额被占满时，TryCompile 里的
        #    `make -f Makefile cmTC_xxx/fast` 会报 `make[1]: /bin/sh: Resource temporarily unavailable`
        #    → Error 127（实测构建 #93910，与 indi #93902 同类）。该工具链已知可用（本地 configure 正常），
        #    故用 CMake 官方开关跳过；真正的编译仍由随后正常执行的 make 完成，工具链真有问题照样会暴露。
        tc.cache_variables["CMAKE_C_COMPILER_WORKS"] = "1"
        tc.cache_variables["CMAKE_CXX_COMPILER_WORKS"] = "1"
        tc.generate()

    def build(self):
        self._patch_upstream_cmake()
        cmake = CMake(self)
        cmake.configure()
        # ⚠️ 不用 cmake.build()：它按 `tools.build:jobs` 发 `-- -jN`（CI 上为 -j20），受限 Worker 上
        #    一口气 fork 出 20 个编译器即报 `can't fork - try again` / `Resource temporarily unavailable`。
        #    改为自己调用构建命令并固定 `-j2`。
        import shutil as _sh
        cm = _sh.which("cmake") or "/data/service/hnp/cmake.org/cmake_4.1.2/bin/cmake"
        self.run('"%s" --build "%s" -- -j2' % (cm, self.build_folder))
        self._run_added_tests()

    def _dep_libpaths(self):
        """依赖包在 conan 缓存里的 lib 目录（链接期与运行时都要用）。"""
        return sorted(os.path.join(self.dependencies[r].package_folder, "lib").replace("\\", "/")
                      for r in ("bzip2", "openssl", "libusb", "zstd", "tinyxml2", "zlib"))

    def _patch_upstream_cmake(self):
        """conan 环境适配（不改上游逻辑，只注入 conan 依赖的绝对路径 + 补 UUUSSL）：
        ① libuuu 的 include_directories 漏了 BZip2 → buffer.cpp 找不到 bzlib.h；
        ② conan 下 FindOpenSSL 不命中 → OPENSSL_FOUND 为假 → UUUSSL 未定义，而 http.cpp:506 的
           base64_encode 使用处**没有同等守卫** → 未声明标识符。
        做法与仓库里 argp-standalone 配方就地改 configure 的套路一致。
        """
        bz = self.dependencies["bzip2"].package_folder.replace("\\", "/")
        ssl = self.dependencies["openssl"].package_folder.replace("\\", "/")
        libdirs = " ".join(sorted('"%s"' % os.path.join(self.dependencies[r].package_folder, "lib").replace("\\", "/")
                                  for r in ("bzip2", "openssl", "libusb", "zstd", "tinyxml2", "zlib")))
        libpaths = self._dep_libpaths()
        # 直接给链接器 -Wl,-rpath（不受上游 CMAKE_SKIP_RPATH / CMake rpath 逻辑影响，最可靠）
        rpath_flags = " ".join("-Wl,-rpath," + p for p in libpaths)
        inject = (
            "\n# ── conan 适配注入（配方 _patch_upstream_cmake；仅补路径，不改上游逻辑）──\n"
            'set(UUUSSL "-DUUUSSL")\n'
            # 注意：OpenSSL 的 include 必须直接进 include_directories —— 上游只在
            # if(OPENSSL_FOUND) 里才把 OPENSSL_INCLUDE_DIR 赋给 UUUOPENSLL_INCLUDE_DIR，
            # conan 下 OPENSSL_FOUND 为假（FindOpenSSL 不认 conan 包）→ 否则 <openssl/ssl.h> 找不到
            'include_directories("%s/include" "%s/include")\n'
            'set(OPENSSL_INCLUDE_DIR "%s/include")\n'
            'set(OPENSSL_LIBRARIES "%s/lib/libssl.a" "%s/lib/libcrypto.a")\n'
            "link_directories(%s)\n"
            # 运行时必须解析到 conan 的依赖库：否则加载器可能解析到别处同名 so，
            # 出现 "Error relocating …: <tinyxml2 符号> symbol not found"。
            # ⚠️ 上游两个 CMakeLists 顶部都有 set(CMAKE_SKIP_RPATH ON) —— 不关掉的话
            #    下面两条 rpath 设置会被完全忽略（实测二进制里没有任何 RPATH）。
            "set(CMAKE_SKIP_RPATH OFF)\n"
            'set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} %s")\n'
            "set(CMAKE_BUILD_RPATH %s)\n"
            "set(CMAKE_INSTALL_RPATH %s)\n" % (bz, ssl, ssl, ssl, ssl,
                                               libdirs, rpath_flags, libdirs, libdirs)
        )
        for rel in ("libuuu/CMakeLists.txt", "uuu/CMakeLists.txt"):
            p = os.path.join(self.source_folder, rel)
            if not os.path.isfile(p):
                continue
            text = open(p, encoding="utf-8").read()
            if "conan 适配注入" in text:
                continue
            text = text.replace("find_package(OpenSSL)", "find_package(OpenSSL)" + inject, 1)
            text = text.replace("include_directories(${LIBUSB_INCLUDE_DIRS}",
                                "include_directories(${BZIP2_INCLUDE_DIRS} ${LIBUSB_INCLUDE_DIRS}")
            if rel == "libuuu/CMakeLists.txt":
                # ⚠️ 上游用 `add_custom_command(PRE_BUILD … COMMAND sh -c '… ./gen_ver.sh …')` 现场生成
                #    gitversion.h —— 受限 Worker 上这一步的 `sh` fork 会直接失败
                #    （`sh: can't fork - try again` → `libuuu/CMakeFiles/uuc_s.dir/…gitversion.h` Error 1，
                #    构建才 2% 就死，CI #94830 实测）。改为**configure 期**由 CMake 自己 `file(WRITE …)`
                #    写出该头：不 fork 任何进程、也不再需要那条 PRE_BUILD 步骤。
                #    必须写**两处**：生成目录（`include_directories` 指向它，供 version.cpp include）
                #    + `libuuu/` 源目录（上游 SOURCES 列表里就写着 `gitversion.h`，CMake 要求它能在
                #    源目录解析到，否则 configure 报 `Cannot find source file: gitversion.h`）。
                #    内容与 gen_ver.sh 的产物一致（一行 `#define GIT_VERSION "lib<版本>"`）。
                gen_hdr = ('file(WRITE "${gitversion_h}" "#define GIT_VERSION \\"lib%s\\"\\n")\n'
                           'file(WRITE "${CMAKE_CURRENT_SOURCE_DIR}/gitversion.h"'
                           ' "#define GIT_VERSION \\"lib%s\\"\\n")\n' % (self.version, self.version))
                _start = text.find("add_custom_command(\n\tOUTPUT gitversion.h")
                if _start >= 0:
                    _end = text.find("\n)\n", _start)
                    if _end > _start:
                        text = text[:_start] + gen_hdr + text[_end + 3:]
                        self.output.info("[patch] libuuu 的 gitversion.h 改为 configure 期 file(WRITE) "
                                         "生成（去掉 PRE_BUILD 的 sh/gen_ver.sh，避免 fork 失败）")
            open(p, "w", encoding="utf-8").write(text)
            self.output.info("[patch] %s 已注入（UUUSSL / BZip2 / OpenSSL 绝对路径）" % rel)

    # ── 补的功能级测试（上游无测试套件）────────────────────────────────
    # libusb 打桩源码：uuu 在**解析参数之前**就 libusb_init（libuuu/usbhotplug.cpp:77），
    # 无 USB 子系统的沙箱/CI 上该调用返回 <0 → 抛 std::runtime_error 直接 abort（rc=134），
    # 于是 `uuu -h` / `-V` 这类纯 CLI 路径也跑不起来。本桩只让 USB 初始化/热插拔注册/设备枚举
    # “成功且无设备”，使**真实二进制**的参数解析与帮助/版本输出路径能真正执行；不伪造设备。
    # ⚠️ 同一份源码在 test_package/check_uuu.py 里也有一份（消费者侧用），两处必须保持一致。
    _USB_STUB_C = r"""/* libusbstub.c — 仅供本包测试使用的 libusb 打桩（LD_PRELOAD） */
#include <stddef.h>
typedef void *libusb_context;
typedef void *libusb_hotplug_callback_handle;
int libusb_init(libusb_context **ctx) { if (ctx) *ctx = (libusb_context)0x1; return 0; }
int libusb_init_context(libusb_context **ctx, const void *o, int n) { (void)o; (void)n; return libusb_init(ctx); }
void libusb_exit(libusb_context *ctx) { (void)ctx; }
int libusb_set_option(libusb_context *ctx, int option, ...) { (void)ctx; (void)option; return 0; }
int libusb_hotplug_register_callback(libusb_context *ctx, int e, int f, int v, int p, int c,
                                     void *cb, void *ud, libusb_hotplug_callback_handle *h)
{ (void)ctx; (void)e; (void)f; (void)v; (void)p; (void)c; (void)cb; (void)ud; if (h) *h = (libusb_hotplug_callback_handle)0x1; return 0; }
void libusb_hotplug_deregister_callback(libusb_context *ctx, libusb_hotplug_callback_handle h) { (void)ctx; (void)h; }
int libusb_get_device_list(libusb_context *ctx, void ***list) { (void)ctx; if (list) *list = NULL; return 0; }
void libusb_free_device_list(void **list, int u) { (void)list; (void)u; }
const char *libusb_error_name(int e) { (void)e; return "stub"; }
"""

    def _cc(self):
        import shutil
        for cand in ("clang", "cc", "gcc"):
            p = shutil.which(cand)
            if p:
                return p
        return "/data/service/hnp/bin/clang"

    def _build_usb_stub(self):
        work = os.path.join(self.build_folder, "usb-stub")
        os.makedirs(work, exist_ok=True)
        src = os.path.join(work, "libusbstub.c")
        so = os.path.join(work, "libusbstub.so")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(self._USB_STUB_C)
        self.run('"%s" -shared -fPIC -o "%s" "%s"' % (self._cc(), so, src), cwd=work)
        return so

    def _find_uuu(self):
        for p in glob.glob(os.path.join(self.build_folder, "**", "uuu"), recursive=True):
            if os.path.isfile(p) and os.access(p, os.X_OK):
                try:
                    with open(p, "rb") as fh:
                        if fh.read(4) == b"\x7fELF":
                            return p
                except OSError:
                    continue
        raise ConanInvalidConfiguration("[added tests] 构建目录里没找到 ELF 可执行的 uuu")

    def _run_added_tests(self):
        exe = self._find_uuu()
        self.output.info("[added tests] 产物 = %s（%d 字节）" % (exe, os.path.getsize(exe)))
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = ":".join(self._dep_libpaths()) + ":" + env.get("LD_LIBRARY_PATH", "")

        # ⓪ 原生（不打桩）行为如实记录：无 USB 子系统时 uuu 在解析参数前 libusb_init 失败
        r0 = subprocess.run([exe, "-h"], capture_output=True, text=True, timeout=300, env=env)
        raw = ((r0.stdout or "") + (r0.stderr or "")).strip()
        self.output.info("[added tests] ⓪ 原生（不打桩）`uuu -h` rc=%d：%s"
                         % (r0.returncode, (raw.splitlines()[0][:110] if raw else "（无输出）")))

        # ① 打桩 libusb 后，真实二进制的 CLI 路径**必须真跑通**（硬断言；打桩只让 USB 初始化成功）
        stub = self._build_usb_stub()
        env2 = dict(env)
        env2["LD_PRELOAD"] = stub
        r = subprocess.run([exe, "-h"], capture_output=True, text=True, timeout=300, env=env2)
        out = (r.stdout or "") + (r.stderr or "")
        if r.returncode != 0 or "Universal Update Utility" not in out:
            raise ConanInvalidConfiguration(
                "[added tests] 打桩 libusb 后 `uuu -h` 仍未跑通（rc=%d）：\n%s"
                % (r.returncode, out[-500:]))
        self.output.info("[added tests] ① 打桩后 `uuu -h` rc=0 且打印上游用法 ✓（首行：%s）"
                         % out.strip().splitlines()[0][:120])

        # ② 版本横幅：uuu 的用法输出里就带 libuuu 版本（形如 `… for nxp imx chips -- lib<版本>`）。
        # ⚠️ 不要拿 `uuu -V` 当版本开关：上游 uuu.cpp:187 明写 `-v -V  verbose mode,
        #    -V enable libusb error\warning info` —— `-V` 是 libusb 详细日志开关，不是版本。
        want = "lib" + self.version
        if want not in out:
            raise ConanInvalidConfiguration(
                "[added tests] `uuu -h` 的横幅里没有版本串 %s：\n%s" % (want, out[-400:]))
        self.output.info("[added tests] ② `uuu -h` 横幅含版本 %s ✓" % want)

    def package(self):
        cmake = CMake(self)
        cmake.install()                     # 上游 install(TARGETS uuu DESTINATION bin)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
