# test_package/conanfile.py — globus-openssl-module 5.2 consumer test
"""L1 test: 编译并链接 libglobus_openssl（include globus_openssl.h +
proxycertinfo.h），验证 activate 注册的 OID / X509V3 扩展方法及
deactivate/re-activate 循环，验证头文件 + 库可被消费者正常使用。
"""
import os

from conan import ConanFile


class GlobusOpensslModuleTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 直接声明 openssl：test 图中 openssl 边的 traits 为 run=False，
        # 会被整体 skip（package_folder=None）拿不到 include/lib 路径；
        # 直接 require 使其成为本 test 的直接依赖而参与解析。
        # 版本与主配方 R27 钉版一致（漂移时会显式冲突报错）。
        self.requires("openssl/3.5.6")

    def build(self):
        # TMPDIR 注入（鸿蒙安全框架拦 clang 创建临时文件）
        _tmp_dir = os.path.join(self.build_folder, ".conan_tmp")
        os.makedirs(_tmp_dir, exist_ok=True)
        os.environ["TMPDIR"] = _tmp_dir
        ccs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = ccs.get("c") or "clang"
        src = os.path.join(self.source_folder, "test_package.c")
        out = os.path.join(self.build_folder, "test_globus_openssl_module")
        _inc, _ld = [], []
        for _d in self.dependencies.values():
            _pf = _d.package_folder
            if not _pf:
                continue
            _inc.append(f"-I{os.path.join(_pf, 'include')}")
            _libdir = os.path.join(_pf, "lib")
            if os.path.isdir(_libdir):
                _ld.append(f"-L{_libdir}")
        # 链接完整闭包：本工具链 libtool 链接 .so 形式 deplibs 时会被丢弃，
        # GSI 链上各库产物均不带兄弟库的 DT_NEEDED（同 globus-common/
        # globus-gsi-openssl-error/globus-gsi-proxy-ssl 先例）；musl 加载器
        # 在全局符号域做重定位，test 直接链接全部依赖库后运行期可绑定
        # libglobus_openssl.so.0 的跨库符号。
        self.run(
            f"{cc} {src} -o {out} {' '.join(_inc)} {' '.join(_ld)} "
            f"-lglobus_openssl -lglobus_common -lglobus_proxy_ssl "
            f"-lglobus_openssl_error -lssl -lcrypto")

    def test(self):
        exe = os.path.join(self.build_folder, "test_globus_openssl_module")
        # LD_LIBRARY_PATH 注入运行时 .so 目录（test 二进制链接的
        # libglobus_openssl.so.0/libglobus_common.so.0 及其 DT_NEEDED 链上
        # 的 libglobus_proxy_ssl.so.1/libglobus_openssl_error.so.0/
        # libssl/libcrypto 不在 loader 默认搜索路径——同 globus-callout
        # 4.3 / globus-gsi-openssl-error 4.4 / globus-gsi-proxy-ssl 6.6 先例）
        _libs = []
        for _d in self.dependencies.values():
            if not _d.package_folder:
                continue
            _lp = os.path.join(_d.package_folder, "lib")
            if os.path.isdir(_lp) and _lp not in _libs:
                _libs.append(_lp)
        self.run(f'LD_LIBRARY_PATH="{os.pathsep.join(_libs)}" {exe}')
