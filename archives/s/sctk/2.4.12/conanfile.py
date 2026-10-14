#!/usr/bin/env python3
"""Conan recipe for sctk 2.4.12 — NIST Speech Recognition Scoring Toolkit.

sctk (SCTK) is a collection of command-line tools for scoring and analyzing
speech recognition output (sclite, asclite, rfilter1, ...). Build system is
plain Makefile (top-level makefile driving per-tool sub-makefiles; per-tool
config generated via `make config` with sed/config.sh).
"""
import glob
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SctkConan(ConanFile):
    name = "sctk"
    version = "2.4.12"
    description = "NIST Speech Recognition Scoring Toolkit (sclite/asclite/rfilter1)"
    license = "LicenseRef-USGov-PublicDomain"
    homepage = "https://github.com/usnistgov/SCTK"
    url = "https://github.com/usnistgov/SCTK"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("perl/5.42.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: compilers from Conan conf, never bare ${CC}/${CFLAGS}
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        ranlib = compilers.get("ranlib", "llvm-ranlib") if compilers else "llvm-ranlib"

        # asclite uses autoconf-generated config.sh; on OHOS the conftest
        # run-check cannot execute the freshly-built binary (E064), so pin the
        # compiler-works caches the same way other adapted recipes do.
        env = Environment()
        env.define("CC", cc)
        env.define("CXX", cxx)
        env.define("AR", ar)
        env.define("RANLIB", ranlib)
        env.define("CFLAGS", "-fPIC -O2")
        env.define("CXXFLAGS", "-fPIC -O2")
        env.define("ac_cv_prog_cxx_works", "yes")
        env.define("ac_cv_prog_cc_works", "yes")
        # E064 (config.sh conftest run-check): the freshly-built C++ conftest
        # needs libc++_shared.so from the SDK aarch64-linux-ohos dir on
        # LD_LIBRARY_PATH to actually run on OHOS. Also the user-local
        # libxml2 in ~/usr/local/lib breaks SDK lld (symbol relocation), so
        # override LD_LIBRARY_PATH with clean SDK/system paths instead of
        # appending to the polluted inherited value.
        sdk_llvm = None
        sdk_cxx = None
        for _p in sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib")):
            if os.path.isdir(_p):
                sdk_llvm = _p
                break
        for _p in sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib/aarch64-linux-ohos")):
            if os.path.isdir(_p):
                sdk_cxx = _p
                break
        clean_ld = []
        if sdk_llvm:
            clean_ld.append(sdk_llvm)
        else:
            self.output.warning("SDK llvm/lib not found; asclite config.sh conftest "
                                "run-check may fail (E064)")
        if sdk_cxx:
            clean_ld.append(sdk_cxx)
        else:
            self.output.warning("SDK aarch64-linux-ohos c++ runtime lib not found; "
                                "asclite config.sh conftest run-check may fail (E064)")
        clean_ld.append("/system/lib64")
        env.define("LD_LIBRARY_PATH", os.pathsep.join(clean_ld))

        # R39/OHS tmp:
        #  (1) asclite/utf_filt 的 autoconf config.sh 用 mktemp -d 建 0700 临时
        #      目录写 subs.sed。OHOS /storage 文件系统上该目录被映射为另一
        #      uid（实测属主 20001006 vs 构建进程 20020179），写入即
        #      Permission denied；配 chmod 0777 后实测可写（见补丁 0004/0006/0024）。
        #  (2) sh 解释器自身（heredoc/$( )）也要用 $TMPDIR 建临时文件：
        #      TMPDIR 置空时 fallback /tmp（OHOS 只读）→ sh 直接失败。
        #      故把 TMPDIR 固定为可写的 $HOME/tmp（先 makedirs 确保存在）。
        _tmp_dir = os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(_tmp_dir, exist_ok=True)
        env.define("TMPDIR", _tmp_dir)

        with env.vars(self).apply():
            self.run("make config -j1", cwd=self.source_folder)
            self.run("make all -j1", cwd=self.source_folder)
            # sctk 的产物需 make install 才复制到顶层 bin/（26 个工具）
            self.run("make install -j1", cwd=self.source_folder)

    def package(self):
        copy(self, "*", os.path.join(self.source_folder, "bin"),
             os.path.join(self.package_folder, "bin"))
        # MD-EVAL.PL FIX: several upstream perl scripts use a CRLF line-ending
        # first line (`#!/usr/bin/perl -w\r\n`) which prevents refresh-patch
        # from generating a valid patch for the shebang (patch line-ending
        # mismatch). To guarantee every perl script is runnable on OHOS (no
        # /usr/bin/perl), normalize the shebang of all packaged .pl tools to
        # `#!/usr/bin/env perl` (idempotent, abcselect-style).
        bindir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bindir):
            self.output.warning("bin dir not found in package folder; "
                                "skip perl shebang normalization")
            return
        for _f in sorted(os.listdir(bindir)):
            if _f.endswith((".pl", ".sh", ".py")) or _f == "csrfilt.sh":
                _path = os.path.join(bindir, _f)
                try:
                    with open(_path, "r", encoding="utf-8", errors="replace") as _fh:
                        _lines = _fh.readlines()
                except OSError:
                    continue
                if not _lines or not _lines[0].startswith("#!"):
                    continue
                _first = _lines[0].replace("\r", "").rstrip("\n")
                _rewritten = _first.rstrip()
                if "/usr/bin/perl" in _rewritten:
                    _lines[0] = "#!/usr/bin/env perl\n"
                    with open(_path, "w", encoding="utf-8", newline="") as _fh:
                        _fh.writelines(_lines)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
