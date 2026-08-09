#!/usr/bin/env python3
"""Conan recipe — rsyslog-testing 8.2604.0 (rsyslog testbench).

与 rsyslog 主包共 tarball（rsyslog-8.2604.0.tar.gz），--enable-testbench 启用测试框架。
OHOS 适配：E011 HMDFS mktemp + musl pthread_cancel 条件编译 + musl stub（endutxent/_res）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class RsyslogTestingConan(ConanFile):
    name = "rsyslog-testing"
    version = "8.2604.0"
    description = "Rsyslog testbench：1426 RainerScript/shell 用例 + 3 C 单元测试 + 13 Python mock"
    license = "GPL-3.0"
    homepage = "https://www.rsyslog.com/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 与 rsyslog 主包一致的测试链路依赖
        self.requires("libestr/0.1.11")
        self.requires("libfastjson/1.2304.0")
        self.requires("liblogging/1.0.8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # testbench 框架 + 禁用未满足的可选插件（OHOS probe 环境）
        tc.configure_args.append("--enable-testbench")
        tc.configure_args.append("--disable-uuid")
        tc.configure_args.append("--disable-libgcrypt")
        tc.configure_args.append("--disable-fmhttp")
        tc.configure_args.append("--disable-impstats-push")
        tc.generate()

    def build(self):
        import os as _os
        _os.environ["PATH"] = "/data/service/hnp/bin:" + _os.environ.get("PATH", "")
        _os.environ["AUTOCONF"] = "/data/service/hnp/bin/autoconf"
        _os.environ["ACLOCAL_PATH"] = "/data/service/hnp/pkg-config.org/pkg-config_0.29.2/share/aclocal"
        _os.umask(0)
        _tmp = _os.path.join(self.build_folder, "_tmp")
        _os.makedirs(_tmp, exist_ok=True)
        _os.environ["TMPDIR"] = _tmp
        # 依赖 pkgconfig 指向 conan 缓存（libestr/libfastjson .pc prefix=/ 需 CFLAGS/LIBS 覆盖）
        dep_estr = self.dependencies["libestr"].cpp_info
        dep_fj = self.dependencies["libfastjson"].cpp_info
        _os.environ["LIBESTR_CFLAGS"] = " ".join("-I" + p for p in dep_estr.includedirs)
        _os.environ["LIBESTR_LIBS"] = "-L" + dep_estr.libdirs[0] + " -lestr"
        _os.environ["LIBFASTJSON_CFLAGS"] = " ".join("-I" + p for p in dep_fj.includedirs) + " -I" + dep_fj.includedirs[0] + "/libfastjson"
        _os.environ["LIBFASTJSON_LIBS"] = "-L" + dep_fj.libdirs[0] + " -lfastjson"
        apply_conandata_patches(self)
        self.run("autoreconf -fiv", cwd=self.source_folder)
        # E011：configure 与 config.status 生成模板的 mktemp 同步修复
        _cfg = _os.path.join(self.source_folder, "configure")
        with open(_cfg, encoding="utf-8", errors="replace") as _f:
            _txt = _f.read()
        _txt = _txt.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            'tmp=`(umask 000 && mktemp -d "$TMPDIR/confXXXXXX") 2>/dev/null`')
        _txt = _txt.replace(
            'tmp=./conf$$-$RANDOM\n  (umask 077 && mkdir "$tmp")',
            'tmp=$TMPDIR/conf$$-$RANDOM\n  (umask 000 && mkdir -p "$tmp")')
        with open(_cfg, "w", encoding="utf-8") as _f:
            _f.write(_txt)
        # musl stub：omusrmsg.c endutxent / omfwd.c _res（r4 构建期修复，写入配方保证可复现）
        _om = _os.path.join(self.source_folder, "tools", "omusrmsg.c")
        with open(_om, encoding="utf-8", errors="replace") as _f:
            _t = _f.read()
        _t = _t.replace(
            "    #define setutent setutxent\n    #define getutent getutxent\n    #define endutent endutxent",
            "    #if defined(__linux__) && !defined(__GLIBC__)\n"
            "        #ifndef setutent\n            #define setutent() do { } while(0)\n        #endif\n"
            "        #ifndef getutent\n            #define getutent() ((struct utmpx *) NULL)\n        #endif\n"
            "        #ifndef endutent\n            #define endutent() do { } while(0)\n        #endif\n"
            "    #else\n        #define setutent setutxent\n        #define getutent getutxent\n"
            "        #define endutent endutxent\n    #endif")
        with open(_om, "w", encoding="utf-8") as _f:
            _f.write(_t)
        _of = _os.path.join(self.source_folder, "tools", "omfwd.c")
        with open(_of, encoding="utf-8", errors="replace") as _f:
            _t = _f.read()
        _t = _t.replace(
            "    *pres = &_res;\n#endif",
            "    #if defined(__linux__) && !defined(__GLIBC__)\n"
            "    static struct __res_state _musl_res;\n    *pres = &_musl_res;\n"
            "    #else\n    *pres = &_res;\n    #endif\n#endif")
        with open(_of, "w", encoding="utf-8") as _f:
            _f.write(_t)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        # 收集 testbench 产物：C 单元测试二进制 + diag.sh + shell/RainerScript 用例入口
        copy(self, "tools/rsyslogd", src=self.source_folder, dst=os.path.join(self.package_folder, "sbin"))
        copy(self, "lib/rsyslog/*.so", src=self.source_folder, dst=os.path.join(self.package_folder, "lib", "rsyslog"))
        copy(self, "tests/runtime_unit_*", src=self.source_folder, dst=os.path.join(self.package_folder, "tests"))
        copy(self, "tests/diag.sh", src=self.source_folder, dst=os.path.join(self.package_folder, "tests"))
        copy(self, "tests/*.sh", src=self.source_folder, dst=os.path.join(self.package_folder, "tests"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.requires = ["libestr::libestr", "libfastjson::libfastjson", "liblogging::liblogging"]
