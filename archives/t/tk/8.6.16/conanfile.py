import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, collect_libs, copy,
                               export_conandata_patches, get)


class TkConan(ConanFile):
    name = "tk"
    version = "8.6.16"
    description = "Tk 8.6 — Tcl GUI toolkit (X11 client build for HarmonyOS PC)"
    license = "TCL"
    homepage = "https://www.tcl.tk/"
    url = "https://core.tcl-lang.org/tk/home"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        # conan-verify G1 要求配方显式声明 export_sources()：补丁须随配方导出进缓存
        # （e/ 目录），apply_conandata_patches 才能从 export_sources_folder 读到它。
        # 同族 tcl 8.6.16 同形；tk 8.6.16 目前无补丁，此调用为幂等空操作。
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("tcl/8.6.16")
        # Tk 的 unix 后端就是 X11 客户端（generic/tk.h 直接 include <X11/Xlib.h>，
        # tkUnix*.c 链接 -lX11）：OHOS 自身不带 X11，头文件（xorgproto）与客户端库
        # （libx11）都取自制品仓，libX11 再传递带入 libxcb/libXau/libXdmcp/xtrans。
        self.requires("libx11/1.8.13")
        self.requires("xorgproto/2025.1")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def layout(self):
        from conan.tools.layout import basic_layout

        basic_layout(self, src_folder=".")

    def build(self):
        apply_conandata_patches(self)
        # E011/E052：configure 生成的 config.status 用 umask 077 建临时目录，
        # OHOS HMDFS 上不可写 → 所有 configure 的 umask 077 改 022；HMDFS 重写文件
        # 会丢可执行位，必须显式恢复 0755（参考 tcl 8.6.16 已发布方案）。
        import glob

        for _cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as _f:
                    _text = _f.read()
            except OSError:
                continue
            if "umask 077" in _text:
                with open(_cfg, "w", encoding="utf-8") as _f:
                    _f.write(_text.replace("umask 077", "umask 022"))
            os.chmod(_cfg, 0o755)
        # E532：OHOS uname -s 返回 HarmonyOS，tcl.m4 的 system 分支没有对应项 →
        # SHLIB_LD/SHLIB_SUFFIX 落空、共享库链接命令残缺；伪装 Linux 走 Linux* 分支。
        _shim = os.path.join(self.build_folder, "_uname_shim")
        os.makedirs(_shim, exist_ok=True)
        _u = os.path.join(_shim, "uname")
        with open(_u, "w") as _f:
            _f.write('#!/bin/sh\ncase "${1:-}" in\n  -s|"") echo Linux ;;\n  -r) echo 6.6 ;;\n  -m) echo aarch64 ;;\n  *) exec /system/bin/uname "$@" 2>/dev/null || exec /bin/uname "$@" ;;\nesac\n')
        os.chmod(_u, 0o755)
        try:
            _cur_path = self.conf.get("tools.build:env_path")
        except ConanException:
            _cur_path = os.environ.get("PATH", "")
        os.environ["PATH"] = _shim + os.pathsep + _cur_path

        compiler_executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compiler_executables.get("c", "clang")
        cxx = compiler_executables.get("cpp", "clang++")
        unix_dir = os.path.join(self.source_folder, "unix")
        tcl_info = self.dependencies["tcl"].cpp_info
        x11_info = self.dependencies["libx11"].cpp_info
        tcl_libdir = tcl_info.libdirs[0]
        tcl_incdir = tcl_info.includedirs[0]
        x11_incdir = x11_info.includedirs[0]
        x11_libdir = x11_info.libdirs[0]
        proto_incdir = self.dependencies["xorgproto"].cpp_info.includedirs[0]
        # 依赖的编译期 -I 只能走 CFLAGS/CPPFLAGS：Tk 的 CC_SWITCHES 拼的是
        # -I${TCL_GENERIC_DIR}（tclConfig.sh 里指向打包机的源码树，包内不存在），
        # 且 Tk 不读 TCL_INCLUDE_SPEC，所以 tcl.h/X11 头文件都要显式给出。
        # 链接期 -l 一律不进 configure 的编译器探针——探针会带上 -lX11 而在运行期
        # 找不到 .so，误报 "cannot run C compiled programs"；X11 的 -l 由
        # --x-libraries 经 AC_PATH_X（只做链接测试）供给，tcl 的 -l 由 --with-tcl
        # 指向的 tclConfig.sh 的 TCL_LIB_SPEC 供给。
        includes = " ".join("-I%s" % d for d in (tcl_incdir, x11_incdir, proto_incdir) if d)
        ldflags = " ".join("-L%s" % d for d in (tcl_libdir, x11_libdir) if d)
        self.run(
            "cd %s && umask 022 && bash configure --prefix=/usr/local "
            "--enable-shared=%s tcl_cv_sys_version=Linux-6.6 CC=%s CXX=%s "
            "CFLAGS='%s' CPPFLAGS='%s' LDFLAGS='%s' "
            "--with-tcl=%s --x-includes=%s --x-libraries=%s"
            % (unix_dir, "yes" if self.options.shared else "no", cc, cxx,
               includes, includes, ldflags, tcl_libdir, x11_incdir, x11_libdir),
            env="conanbuild",
        )
        # E207：OHOS 上装出的 libtk8.6.so 没有 DT_SONAME，消费者解析不稳定 →
        # 给共享库链接命令补 -Wl,-soname,<TK_LIB_FILE>（tcl 8.6.16 同款处理）。
        makefile = os.path.join(unix_dir, "Makefile")
        with open(makefile, encoding="utf-8") as _f:
            makefile_text = _f.read()
        soname_linker = "SHLIB_LD\t\t= ${CC} ${CFLAGS} ${LDFLAGS} -shared"
        if makefile_text.count(soname_linker) != 1:
            raise ConanException("unexpected Tk Makefile: SHLIB_LD definition count is not one")
        makefile_text = makefile_text.replace(
            soname_linker,
            soname_linker + " -Wl,-soname,$(TK_LIB_FILE)",
        )
        with open(makefile, "w", encoding="utf-8") as _f:
            _f.write(makefile_text)
        # -j1：OHOS 不支持 make jobserver 的 mkfifo（Operation not permitted）
        self.run("cd %s && make -j1" % unix_dir, env="conanbuild")
        # 上游测试入口是 `make test`（构建 tests/tktest 并执行 Tk 测试套件），tktest 需要
        # 真实 X 显示，OHOS 与 CI worker 都没有（E530）→ 非阻塞尝试，结论写入 notes.md，
        # 功能性覆盖由 test_package 的显示无关消费者测试承担。
        test_log = os.path.join(self.build_folder, "upstream_test.log")
        # tktest 的 RUNPATH 只有源码 unix/ 与 tcl lib（Makefile 的 LIB_RUNTIME_DIR），
        # 不含 libX11/libxcb 等依赖目录 → 直接跑 make test 会停在动态加载阶段
        # （"Error loading shared library libX11.so.6" / Error 127），掩盖真正的阻塞点。
        # 先把全部 host 依赖的 lib 目录并进 LD_LIBRARY_PATH：Makefile 内部赋值是
        # LD_LIBRARY_PATH="`pwd`:<tcl lib>:${LD_LIBRARY_PATH}"，会保留这里传入的值。
        dep_libdirs = []
        for _dep in self.dependencies.host.values():
            for _ld in _dep.cpp_info.libdirs:
                if _ld and _ld not in dep_libdirs:
                    dep_libdirs.append(_ld)
        # 第二道干扰：tclConfig.sh 里 TCL_SRC_DIR 指向 tcl 包的原始构建树（二进制包上该路径
        # 不存在），而 Makefile 的 SHELL_ENV 用 $(TCLDIR)/library 定位 tcl 脚本库 → 上游测试
        # 报 "Can't find a usable init.tcl"。做一个 TCLDIR 影子目录（library → 已安装 tcl 的
        # 脚本库 lib/tcl8.6），再用 make 命令行变量覆盖 TCLDIR（命令行变量优先于 Makefile
        # 内部赋值），把测试推进到平台真正的阻塞点。
        tcl_dir_override = ""
        tcl_scriptlib = os.path.join(self.dependencies["tcl"].cpp_info.libdirs[0], "tcl8.6")
        if os.path.isdir(tcl_scriptlib):
            shim_library = os.path.join(self.build_folder, "tcl-test-root", "library")
            os.makedirs(os.path.dirname(shim_library), exist_ok=True)
            if os.path.islink(shim_library):
                os.unlink(shim_library)
            if not os.path.exists(shim_library):
                try:
                    os.symlink(tcl_scriptlib, shim_library)
                except OSError:
                    copy(self, "*", tcl_scriptlib, shim_library)
            tcl_dir_override = " TCLDIR=%s" % os.path.dirname(shim_library)
        test_rc = self.run(
            "cd %s && LD_LIBRARY_PATH=\"%s:${LD_LIBRARY_PATH}\" make test -j1%s > %s 2>&1"
            % (unix_dir, os.pathsep.join(dep_libdirs), tcl_dir_override, test_log),
            env="conanbuild", ignore_errors=True,
        )
        self.output.info("upstream `make test` rc=%s (log: %s)" % (test_rc, test_log))

    def package(self):
        unix_dir = os.path.join(self.source_folder, "unix")
        # DESTDIR 装进 build 目录内的 staging，再分类拷进 package_folder：--prefix=/usr/local
        # 会让文件落到 <pkg>/usr/local/**，conan 的 cpp_info 期望的是 <pkg>/{lib,include,bin}
        # （tcl 8.6.16 同款处理）。demos/ 是 Tk 演示脚本与示例图片，运行期不需要，不打包。
        staging = os.path.join(self.build_folder, "staging")
        self.run(
            "cd %s && umask 022 && make install DESTDIR=%s" % (unix_dir, staging),
            env="conanbuild",
        )
        prefix = os.path.join(staging, "usr", "local")
        copy(self, "*.so*", src=os.path.join(prefix, "lib"),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.a", src=os.path.join(prefix, "lib"),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "tkConfig.sh", src=os.path.join(prefix, "lib"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.pc", src=os.path.join(prefix, "lib", "pkgconfig"),
             dst=os.path.join(self.package_folder, "lib", "pkgconfig"))
        # Tk 脚本库（lib/tk8.6/**：Tk 核心脚本、ttk、msgcat、图片资源），运行期必需。
        copy(self, "*", src=os.path.join(prefix, "lib", "tk8.6"),
             dst=os.path.join(self.package_folder, "lib", "tk8.6"),
             excludes="demos/*", keep_path=True)
        copy(self, "*.h", src=os.path.join(prefix, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "wish*", src=os.path.join(prefix, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        # 公开头 tk.h 里 include <X11/Xlib.h>，但上游 libx11/1.8.13 配方没有声明
        # cpp_info.includedirs（包内有 include/X11/*.h，生成的 libx11_INCLUDE_DIRS 却是空），
        # xorgproto 同样不进生成器 → OHOS 消费方只 find_package(tk) 拿不到 X11 头，
        # 编 <tk.h> 直接 'X11/Xlib.h' file not found。为让本包自包含，把 X11 头一并装进
        # 本包 include/（X11/ 子目录路径保持），消费方无需再手工拼依赖头目录。
        for _dep in ("libx11", "xorgproto"):
            _dep_inc = os.path.join(self.dependencies[_dep].package_folder, "include")
            if os.path.isdir(_dep_inc):
                copy(self, "*.h", src=_dep_inc,
                     dst=os.path.join(self.package_folder, "include"), keep_path=True)
        # autotools 会把 -L 的目录（本机 conan 缓存绝对路径）写进 RUNPATH，发布包里带着
        # 构建机路径没有意义且会掩盖真实解析顺序；统一收敛成 /usr/local/lib（与兄弟包
        # tcl 8.6.16 一致），运行期库解析交给 conan runenv 的 LD_LIBRARY_PATH。
        _so = os.path.join(self.package_folder, "lib", "libtk8.6.so")
        _patchelf = "/data/service/hnp/bin/patchelf"
        if os.path.isfile(_so) and os.path.isfile(_patchelf):
            self.run('"%s" --set-rpath /usr/local/lib "%s"' % (_patchelf, _so), quiet=True)
        self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.libs = collect_libs(self)
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        # tk.h 公开 include <tcl.h> 与 <X11/Xlib.h>：OHOS 上 X11 头/库来自 conan 依赖
        # （不是系统头），消费方必须一并拿到 libx11/xorgproto 的 include 目录，否则
        # 只 include <tk.h> 就报 'X11/Xlib.h' file not found。
        self.cpp_info.requires = ["tcl::tcl", "libx11::libx11", "xorgproto::xorgproto"]
        self.cpp_info.set_property("cmake_file_name", "tk")
        self.cpp_info.set_property("cmake_target_name", "tk::tk")
        pkg = self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "m", "pthread", "z"]

    def _detect_pkg_config_name(self):
        # 未显式给 --pkgconfig-name 时，从 install 出的 lib/pkgconfig/*.pc 取第一个文件名 stem。
        import glob

        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]

    def _sign_installed_elfs(self):
        """OHOS 不允许加载未签名 ELF（E077）：包内共享库与可执行文件逐个重签。

        构建期 clang 会自动签名，但打包阶段的 ELF 改动（objcopy 去段等）会让原签名失效，
        而签名必须落在最终文件上；因此统一在打包末尾去旧签名再重签，签完不做任何改动。
        工具缺失（纯 Linux 构建机）时跳过，不阻塞打包。
        """
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            self.output.info("OHOS 签名工具不存在，跳过签名")
            return
        targets = []
        for sub in ("lib", "bin"):
            d = os.path.join(self.package_folder, sub)
            if os.path.isdir(d):
                targets.extend(os.path.join(d, n) for n in sorted(os.listdir(d)))
        for path in targets:
            if not os.path.isfile(path):
                continue
            with open(path, "rb") as _f:
                if _f.read(4) != b"\x7fELF":
                    continue
            signed = path + ".signed"
            self.run('"%s" --remove-section .codesign "%s"' % (objcopy, path), quiet=True)
            self.run(
                '"%s" sign -inFile "%s" -outFile "%s" -selfSign 1' % (signer, path, signed),
                quiet=True,
            )
            if not os.path.isfile(signed):
                raise ConanException("签名未产出文件: %s" % path)
            os.replace(signed, path)
            os.chmod(path, 0o755)
