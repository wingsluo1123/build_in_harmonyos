from conan import ConanFile
from conan.tools.files import collect_libs, get
import glob
import os
import shutil
from conan.tools.layout import basic_layout


class TclConan(ConanFile):
    name = "tcl"
    version = "9.0.3.1"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports = "scripts/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        # 自定义构建命令自带工具链设置（如 build-ohos.sh 用 ohos.toolchain.cmake）；
        # conan 的 buildenv（CC/CXX、OHOS_NDK_HOME 等）通过 self.run(env="conanbuild") 注入。
        pass

    def build(self):
        # 依赖包路径注入：为每个 requires 导出 CONAN_DEP_<NAME>_ROOT=<依赖包目录>，
        # 供自定义构建脚本定位依赖（如 tk 的 build-ohos.sh 用 $CONAN_DEP_TCL_ROOT 找 Tcl 的 tclConfig.sh/libtcl）。
        for _require, _dep in self.dependencies.items():
            _pf = getattr(_dep, "package_folder", None)
            if _pf:
                _name = _require.ref.name.upper().replace("-", "_").replace(".", "_")
                os.environ["CONAN_DEP_%s_ROOT" % _name] = str(_pf)
        # 库自带的专属构建（可产多个 .so、两趟链接等）。cwd=源码根，注入 conan buildenv。
        self.run(r"""bash ohos-build/build-ohos.sh all""", cwd=self.source_folder, env="conanbuild")

    def package(self):
        # 自定义构建产物落在源码树内（非标准 cmake install）：按 artifacts glob 收集所有 .so 到 lib/，
        # 保留 soname 软链；再收 headers_dir 头文件到 include/。
        libdir = os.path.join(self.package_folder, "lib")
        os.makedirs(libdir, exist_ok=True)
        for pattern in ['ohos-build/dist/usr/lib/libtcl9.0.so', 'ohos-build/tclConfig.sh', 'ohos-build/ohos-configure.env', 'ohos-build/libtclstub.a']:
            for path in glob.glob(os.path.join(self.source_folder, pattern)):
                dst = os.path.join(libdir, os.path.basename(path))
                if os.path.islink(path):
                    target = os.path.basename(os.readlink(path))
                    if not os.path.lexists(dst):
                        os.symlink(target, dst)
                else:
                    shutil.copy2(path, dst)
        headers_dir = "generic"
        if headers_dir:
            # 只收头文件（.h/.hpp/.hh/.inc），保留子目录结构；避免把与头混放的 .c 等源码带进 include。
            src = os.path.join(self.source_folder, headers_dir)
            incdir = os.path.join(self.package_folder, "include")
            for root, _dirs, files in os.walk(src):
                for fn in files:
                    if fn.endswith((".h", ".hpp", ".hh", ".inc")):
                        rel = os.path.relpath(os.path.join(root, fn), src)
                        dst = os.path.join(incdir, rel)
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(os.path.join(root, fn), dst)
        # 资源目录收集（保结构）：每项 "源码相对目录:包内目标子目录"（如 tk 脚本库 → package/res/tk9.0）
        for _res in []:
            _rsrc, _rdst = _res.split(":", 1)
            _rs = os.path.join(self.source_folder, _rsrc)
            _rd = os.path.join(self.package_folder, _rdst)
            if os.path.isdir(_rs):
                shutil.copytree(_rs, _rd, dirs_exist_ok=True)
            elif os.path.isfile(_rs):
                os.makedirs(os.path.dirname(_rd), exist_ok=True)
                shutil.copy2(_rs, _rd)
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        # 鸿蒙 PC 对 dlopen 的 .so 强制校验签名：未签名时 dlopen 不报错但 dlsym 全返回 NULL。
        # 复用 recipe 自带 scripts/sign-so.sh（DevEco binary-sign-tool 自签），对 package 内所有 .so 就地签。
        import glob
        import os
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        sign = os.path.join(self.recipe_folder, "scripts", "sign-so.sh")
        quoted = " ".join('"{}"'.format(s) for s in sos)
        self.run('bash "{}" {}'.format(sign, quoted))

    def package_info(self):
        explicit_libs = []
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "tcl")
        self.cpp_info.set_property("cmake_target_name", "tcl::tcl")
        pkg = "" or self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)
        # 消费方运行环境变量（path 型，相对包根）：如 TK_LIBRARY=res/tk9.0，
        # 让 find_package/VirtualRunEnv 的消费方自动拿到（GUI 库脚本库定位，见 C1）。
        import os
        for _env in []:
            _k, _v = _env.split("=", 1)
            self.runenv_info.define_path(_k, os.path.join(self.package_folder, _v))

    def _detect_pkg_config_name(self):
        # 未显式给 --pkgconfig-name 时，从 install 出的 lib/pkgconfig/*.pc 取第一个文件名 stem。
        import glob
        import os
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]
