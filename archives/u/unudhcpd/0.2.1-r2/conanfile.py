#!/usr/bin/env python3
"""Conan recipe — unudhcpd 0.2.1-r2（极简 DHCP 服务器，纯 C，Meson 构建）

上游: https://gitlab.postmarketos.org/postMarketOS/unudhcpd
产物: bin/unudhcpd（命令行工具 → package_type = "application"）
构建: Meson，零外部依赖（仅 libc）
测试: 层1 上游官方测试 = tests/meson.build 用 test() 注册的 3 个单测
      层2 test_package = 执行已安装的 unudhcpd 二进制做消费者验证
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class UnudhcpdConan(ConanFile):
    name = "unudhcpd"
    version = "0.2.1-r2"
    description = ("unudhcpd — 极简 DHCP 服务器，只给单个客户端下发一个固定 IP"
                   "（postmarketOS）")
    license = "GPL-3.0-or-later"
    homepage = "https://gitlab.postmarketos.org/postMarketOS/unudhcpd"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 产物为可执行文件而非库 → application（R38: 同目录需 commands.json）
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # 零外部依赖：仅用 libc（inet_aton / getprotobyname / socket / ioctl）
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.generate()
        self._inject_meson_archiver()

    def _inject_meson_archiver(self):
        """把 ar/ranlib 全路径注入 conan_meson_native.ini。

        【OHOS 必需】Conan 的 MesonToolchain 不会把 tools.build:compiler_executables 里的
        ar/ranlib 写进 native file（toolchain.py 中 `self.ar = build_env.get("AR")`），
        于是 meson 按**裸名** `llvm-ar` 探测归档器 —— 只要 PATH 上没有 llvm-ar，
        `meson setup` 就直接失败：

            ERROR: Unknown linker(s): [['llvm-ar']]
            Running `llvm-ar --version` gave "[Errno 2] No such file or directory"

        本仓库 CI worker 的 PATH 不含 /data/service/hnp/bin，故 CI 必挂
        （本地因交互式 PATH 含该目录而侥幸通过 —— 这正是本地 W3 未拦截的真实原因）。
        修法：从 c 编译器同目录推导 llvm-ar/llvm-ranlib 全路径并注入 native file，
        不改 PATH、不污染环境（同仓 dav1d/cairo 实证范式）。
        """
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        _ar, _rl = _ce.get("ar"), _ce.get("ranlib")
        # profile 通常只给 c/cpp：从 c 编译器同目录推导 llvm-ar / llvm-ranlib 全路径
        if not _ar:
            _cc = _ce.get("c") or ""
            _bindir = os.path.dirname(_cc) if os.path.sep in _cc else ""
            cands = []
            if _bindir:
                cands += [os.path.join(_bindir, "llvm-ar"), os.path.join(_bindir, "ar")]
            # 兜底：编译器同目录未命中时，再按 PATH 顺序找（生成期不保证 PATH 含工具链目录）
            for _name in ("llvm-ar", "ar"):
                _w = shutil.which(_name)
                if _w:
                    cands.append(_w)
            for _cand in cands:
                if os.path.isfile(_cand):
                    _ar = _cand
                    _rlc = os.path.join(os.path.dirname(_cand), "llvm-ranlib")
                    if not os.path.isfile(_rlc):
                        _rlc = os.path.join(os.path.dirname(_cand), "ranlib")
                    if os.path.isfile(_rlc):
                        _rl = _rlc
                    break
        _nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not (_ar and os.path.isfile(_nf)):
            return
        with open(_nf, encoding="utf-8") as _f:
            _c = _f.read()
        if "\nar =" in _c or "[binaries]" not in _c:
            return
        _ins = "[binaries]\nar = '%s'\n" % _ar
        if _rl:
            _ins += "ranlib = '%s'\n" % _rl
        with open(_nf, "w", encoding="utf-8") as _f:
            _f.write(_c.replace("[binaries]\n", _ins, 1))

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        # Conan 2.x Meson 助手方法为 configure/build/install/test，
        # 无 compile()（ADAPTATION_GUIDE §4.4 模板仍写 meson.compile()，属过期写法）
        meson.build()
        # ── 层1: 上游官方测试（必做，TEST_QUALITY_SPEC §3）──
        # tests/meson.build 用 test() 注册 3 个用例（合计 24 条断言用例）：
        #   Test mac_to_str / Test dhcp_is_invalid_request / Test dhcp_get_request_type
        meson.test()

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
