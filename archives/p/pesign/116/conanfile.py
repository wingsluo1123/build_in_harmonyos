"""pesign 116 —— 对 PE/COFF 二进制（UEFI 应用、shim、内核等）做签名与校验的工具集（HarmonyOS PC 适配）。

**它是什么**：pesign 基于 NSS 证书库对 PE-COFF 文件签名/校验，提供 `pesign`（签名服务与 CLI）、
`pesign-client`、`efikeygen`（生成自签名证书）、`authvar`（写 EFI 认证变量）、`pesigcheck` 等命令，
广泛用于 UEFI Secure Boot 流程。

**依赖**（上游 `Make.defaults` 的 `PKGS = efivar nspr nss nss-util uuid`，部分目标另加 `popt`）：
`efivar/39`、`nspr/4.37`、`nss/3.118.1`、`popt/1.19`、`uuid/2.40.1` —— 均在制品仓。
其中 **`nss-util` 在制品仓里没有独立包**（NSS 的构建产物自带 `libnssutil3`），而上游的 `PKGS` 会
用 pkg-config 找它，缺了会静默失败、编译期才报缺头文件；因此本配方在生成器目录里**补一个最小的
`nss-util.pc` 指向 `nss` 包**（不改上游任何文件）。

**构建**：手写 Makefile 体系，**不是 autotools** → 不需要 autoreconf（也就避开受限 Worker 上
autoreconf 卡死那一类问题）；依赖经 pkg-config 查找，由 conan 的 PkgConfigDeps 提供 .pc。

**移植补丁**：musl 不声明 `reallocarray()`（隐式声明成 int → 指针赋值报错），两处调用改为等价的
`realloc`（其后都紧跟判空），见 `patches/0001-reallocarray-portability.patch`。
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, get, save
from conan.tools.gnu import AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class PesignConan(ConanFile):
    name = "pesign"
    version = "116"
    package_type = "application"
    description = ("对 PE/COFF（UEFI 应用、shim、内核等）做签名与校验的工具集，"
                   "提供 pesign / pesign-client / efikeygen / authvar / pesigcheck")
    license = "GPL-2.0-only"
    url = "https://github.com/rhboot/pesign"
    homepage = "https://github.com/rhboot/pesign"
    topics = ("uefi", "secure-boot", "pe-coff", "signing", "nss", "efi")
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # 上游 Make.defaults 的 PKGS 及各目标追加项，均在制品仓
        self.requires("efivar/39")
        self.requires("nspr/4.37")
        self.requires("nss/3.118.1")
        self.requires("popt/1.19")
        self.requires("uuid/2.40.1")

    def generate(self):
        PkgConfigDeps(self).generate()
        # ⚠️ 上游 Make.defaults 里 `CC ?= gcc`，而本环境只有 clang（实测 `make[2]: gcc: No such file
        #    or directory`）。这里生成构建环境（CC/CXX/AR/RANLIB/STRIP + 依赖的 -I/-L），再交给 make，
        #    仍然不改上游任何文件。
        tc = AutotoolsToolchain(self)
        tc.generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

        # ⚠️ 制品仓没有独立的 nss-util 包（NSS 自带 libnssutil3），而上游 PKGS 里写了 nss-util →
        #    pkg-config 找不到它时 $(shell) 静默失败、编译期才报缺头文件。
        #    这里在 PkgConfigDeps 生成的 .pc 目录里补一个最小的 nss-util.pc 指向 nss 包（不改上游）。
        nss = self.dependencies["nss"]
        inc = os.path.join(nss.package_folder, nss.cpp_info.includedirs[0])
        lib = os.path.join(nss.package_folder, nss.cpp_info.libdirs[0])
        pcs = glob.glob(os.path.join(self.generators_folder, "**", "*.pc"), recursive=True)
        pc_dir = os.path.dirname(pcs[0]) if pcs else self.generators_folder
        save(self, os.path.join(pc_dir, "nss-util.pc"),
             "prefix=%s\nexec_prefix=${prefix}\nlibdir=%s\nincludedir=%s\n\n"
             "Name: nss-util\n"
             "Description: NSS utility library (provided by the conan nss package)\n"
             "Version: %s\n"
             "Libs: -L${libdir} -lnssutil3\n"
             "Cflags: -I${includedir}\n"
             % (nss.package_folder, lib, inc, nss.ref.version))
        self.output.info("[generate] 已补 nss-util.pc → %s（指向 %s）" % (pc_dir, nss.ref))

    def source(self):
        spec = dict(self.conan_data["sources"])
        spec.pop("note", None)
        get(self, **spec, strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # 手写 Makefile：`make all` 即可（不是 autotools）。`-j1`：受限 Worker 上避免并行 fork 压力。
        # ⚠️ 必须显式把依赖的 `-L` 交给 make：上游的 `LDLIBS` 只含 `-l…`（来自 pkg-config 的
        #    `--libs-only-l`），`-L` 那段来自 `ccldflags` 里的 `$(LDFLAGS)`，而 conan 的
        #    AutotoolsToolchain 生成的 env 文件不在 `conanbuild` 组里 → 链接行上没有 `-L`，
        #    直接报 `ld.lld: unable to find library -lfreebl/-lnssckfw/-lnssdbm/-lsqlite/-lnspr4…`
        #    （实测）。这些库在 conan 包里都在（如 efivar 的 lib/libefivar.so、nss 的 libfreebl.a 等），
        #    所以只补 `-L` 即可；用 LDFLAGS 传入（上游 ccldflags 会带上它）。
        libs = " ".join(sorted({"-L" + os.path.join(self.dependencies[r].package_folder, "lib")
                                for r in ("efivar", "nspr", "nss", "popt", "uuid")}))
        # ⚠️ 运行期也要能找到这些 .so：把同样的目录写成 DT_RUNPATH。实测不写 rpath 时，消费者侧
        #    `pesign --help` 会 rc=127「Error loading shared library libfreebl3.so」——
        #    即用运行依赖环境之外的路径直接跑二进制就会挂。直接给链接器 rpath 最可靠
        #    （不受 LD_LIBRARY_PATH 是否被设置影响，仓库里 mfgtools 也是这么处理的）。
        rpath = " ".join(sorted({"-Wl,-rpath," + os.path.join(self.dependencies[r].package_folder, "lib")
                                 for r in ("efivar", "nspr", "nss", "popt", "uuid")}))
        # ⚠️ RANLIB 也要显式给：conan 环境里它是 `clang-ranlib`，而本工具链里该工具名为
        #    `llvm-ranlib`（实测 `make[1]: clang-ranlib: No such file or directory` →
        #    Make.rules:23 Error 127，静态库那步就死）。按实际存在的路径 pin。
        import shutil as _sh
        ranlib = _sh.which("llvm-ranlib") or _sh.which("ranlib") or "llvm-ranlib"
        # ⚠️ musl 缺的 glibc 扩展要自己声明，否则 clang 15 在 C99 下把"隐式声明 + int→指针"当**硬错误**
        #    （实测 password.c:70 的 `secure_getenv` 赋值报 incompatible integer to pointer conversion；
        #    另有 list.h:759 的 `qsort_r`）。垫片放在 `<source>/include/` —— 该目录在**每个**编译单元的
        #    `-I` 里（实测命令行含 `-I<source>/include`），再由补丁在该 Makefile 的 CFLAGS 行加
        #    `-include conan_musl_shim.h`，于是对所有 .c 生效，且无需知道垫片的绝对路径。
        save(self, os.path.join(self.source_folder, "include", "conan_musl_shim.h"),
             "/* conan 适配垫片：补齐 musl 缺的 glibc 扩展（仅声明，实现由 libc 提供）。 */\n"
             "#ifndef __OHOS_MUSL_SHIM_H__\n"
             "#define __OHOS_MUSL_SHIM_H__\n"
             "#include <stddef.h>\n"
             "#include <sys/types.h>\n"
             "#ifndef __OHOS_ERROR_T_DEFINED__\n"
             "#define __OHOS_ERROR_T_DEFINED__\n"
             "typedef int error_t;                    /* musl 无 error_t（glibc 在 <errno.h>） */\n"
             "#endif\n"
             "#ifndef __DEFINED_loff_t\n"
             "#define __DEFINED_loff_t\n"
             "typedef off_t loff_t;                   /* 与 musl 的 __DEFINED_loff_t 机制互斥 */\n"
             "#endif\n"
             "extern void qsort_r(void *base, size_t nmemb, size_t size,\n"
             "                    int (*compar)(const void *, const void *, void *), void *arg);\n"
             "extern char *secure_getenv(const char *name);\n"
             "/* glibc 专有的程序名变量：先声明（与 libc 已有的声明类型一致，重复声明合法），\n"
             " * 若 libc 未提供定义则由垫片 .c 里的 weak 定义兜底。 */\n"
             "extern char *program_invocation_short_name;\n"
             "extern char *program_invocation_name;\n"
             "#endif\n")
        self.output.info("[build] 已写 musl 垫片 conan_musl_shim.h（error_t / loff_t / qsort_r / secure_getenv）")
        # ⚠️ 光有声明不够：OHOS 的 musl **没有** `secure_getenv` 的实现（实测链接期
        #    `ld.lld: undefined symbol: secure_getenv`）。这里补一个最小实现并编成 .o 交给链接
        #    （对象文件提供的是**定义**，放在 LDFLAGS 里与链接顺序无关）。
        #    语义如实说明：`secure_getenv` 是 glibc 扩展（setuid/setgid 进程里返回 NULL）；
        #    musl 无此函数、pesign 也不是 setuid 程序，故此处等价于 `getenv` —— 这一处偏离已写进
        #    notes.md / manifest.yaml。
        shim_c = os.path.join(self.source_folder, "include", "conan_musl_shim.c")
        save(self, shim_c,
             "/* conan 适配：OHOS musl 未提供 secure_getenv（glibc 扩展）。非 setuid 场景下等价 getenv。 */\n"
             "#include <stdlib.h>\n"
             "char *secure_getenv(const char *name) { return getenv(name); }\n"
             "/* glibc 专有的程序名变量：用 weak 给出兜底定义（libc 若有强定义会被优先采用，不冲突）。 */\n"
             "__attribute__((weak)) char *program_invocation_short_name = \"pesign\";\n"
             "__attribute__((weak)) char *program_invocation_name = \"pesign\";\n")
        cc = _sh.which("clang") or "clang"
        obj = shim_c + ".o"
        self.run('"%s" -c -O2 -fPIC -o "%s" "%s"' % (cc, obj, shim_c),
                 cwd=self.source_folder, env="conanbuild")
        self.output.info("[build] 已编译 musl 垫片实现：%s（提供 secure_getenv）" % obj)
        # ⚠️ 上游的 `-l…` 来自 nss.pc（`-lnss -lssl -lsmime -lnssutil -lsoftokn -lfreebl …`），但那套
        #    名字在 conan 的 nss 包里对不上：实测缺的 NSS 符号（PK11_* / CERT_* / SECKEY_*）都在
        #    **libnss3.so** 里，而 `-lnss` 解析不到它（nss.pc 的 `-lnssutil` 之类同理）。
        #    做法：扫描各依赖包 lib/ 下**实际存在的共享库**，按真实文件名补 `-l` 列表，并用 LDFLAGS
        #    传入（共享库不讲究顺序，且不覆盖上游的 LDLIBS/LIBS 语义）。
        extra = []
        for r in ("nss", "nspr", "popt", "efivar", "uuid"):
            d = os.path.join(self.dependencies[r].package_folder, "lib")
            if not os.path.isdir(d):
                continue
            for fn in sorted(os.listdir(d)):
                if not fn.startswith("lib") or ".so" not in fn:
                    continue
                stem = fn.split(".so")[0]
                if len(stem) > 3 and all(c.isalnum() or c in "_-+" for c in stem[3:]):
                    extra.append("-l" + stem[3:])
        extra = sorted(set(extra))
        self.output.info("[build] 按包内实际库补的 -l 列表：%s" % " ".join(extra))
        self.run('make -j1 all LDFLAGS="%s %s %s %s" RANLIB="%s"'
                 % (libs, rpath, " ".join(extra), obj, ranlib),
                 cwd=self.source_folder, env="conanbuild")
        self._run_added_tests()

    # ── 补的功能级测试（上游 116 无测试目录）──────────────────────────────
    def _find_exe(self, name):
        # ⚠️ 上游是**源码内构建**：二进制落在 `<source>/src/<name>`（不是 <source>/<name>）。
        #    实测只找 <source>/<name> 会报 "[added tests] 没找到 ELF 可执行的 pesign"，所以三处都看。
        hits = []
        for p in ([os.path.join(self.source_folder, name),
                   os.path.join(self.source_folder, "src", name)]
                  + glob.glob(os.path.join(self.source_folder, "**", name), recursive=True)):
            if os.path.isfile(p) and os.access(p, os.X_OK) and ".so" not in os.path.basename(p):
                try:
                    with open(p, "rb") as fh:
                        if fh.read(4) == b"\x7fELF":
                            hits.append(p)
                except OSError:
                    continue
        return hits


    def _run_added_tests(self):
        """真跑产物：pesign 与 efikeygen 各跑一次 `--help`（rc=0 且有输出才算过）。"""
        env = dict(os.environ)
        # 运行期要能找到依赖的 .so（构建期子进程不继承 conan run env）→ 并入全部 host 依赖的 lib 目录
        libs = set()
        for item in self.dependencies.items():
            dep = item[1] if isinstance(item, tuple) else item
            try:
                libs.add(os.path.join(dep.package_folder, dep.cpp_info.libdirs[0]))
            except Exception:
                continue
        env["LD_LIBRARY_PATH"] = ":".join(sorted(libs)) + ":" + env.get("LD_LIBRARY_PATH", "")

        checked = []
        for name in ("pesign", "efikeygen"):
            hits = self._find_exe(name)
            if not hits:
                raise ConanInvalidConfiguration("[added tests] 没找到 ELF 可执行的 %s" % name)
            exe = hits[-1]
            blob, rc, used = "", None, ""
            for flag in ("--help", "-h"):
                r = subprocess.run([exe, flag], capture_output=True, text=True, timeout=300, env=env)
                blob = ((r.stdout or "") + (r.stderr or "")).strip()
                rc, used = r.returncode, flag
                if rc == 0 and blob:
                    break
            if rc != 0 or not blob:
                raise ConanInvalidConfiguration(
                    "[added tests] `%s %s` 未成功（rc=%s）：\n%s" % (name, used, rc, blob[-400:]))
            self.output.info("[added tests] ✓ `%s %s` 真跑成功（首行：%s）"
                             % (name, used, blob.splitlines()[0][:70]))
            checked.append(name)
        self.output.info("[added tests] 共真跑 %d 个产物：%s" % (len(checked), ", ".join(checked)))

    def package(self):
        # ⚠️ 必须用上游自己的 DESTDIR 机制：Make.defaults 里 `INSTALLROOT = $(DESTDIR)`，而 install
        #    规则里有 `install -d -m 700 $(INSTALLROOT)/etc/pki/pesign/` 这类**绝对路径**步骤 ——
        #    实测只传 `prefix=<包>`（不传 DESTDIR）时 INSTALLROOT 为空 → 它会去写真实的 /etc/pki，
        #    在只读文件系统上直接 `install: /etc/pki: Read-only file system` → Error 1。
        #    正确做法：`prefix=/`（配合 `prefix := $(abspath $(prefix))/` 得到 //bin/ 等）+ DESTDIR 指向包目录。
        self.run('make install prefix=/ DESTDIR="%s"' % self.package_folder,
                 cwd=self.source_folder, env="conanbuild")
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        for f in ("README", "README.md", "NEWS"):
            copy(self, f, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "libexec"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.set_property("cmake_file_name", "pesign")
