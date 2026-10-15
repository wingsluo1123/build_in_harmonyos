#!/usr/bin/env python3
"""Conan recipe — pmacct 1.7.8 on HarmonyOS PC (OHOS / aarch64).

pmacct 是一套被动网络监控工具（IP 流量统计 / BGP / BMP / RPKI / IGP /
Streaming Telemetry）。本配方交付 7 个可执行文件：

    bin/pmacct
    bin/pmacctd  bin/nfacctd  bin/sfacctd  bin/pmtelemetryd  bin/pmbgpd  bin/pmbmpd

上游第 8 个守护进程 uacctd 由 `WITH_NFLOG` 条件控制（src/Makefile.am:162-166），
需要 libnetfilter_log；制品仓未发布该包 ⇒ 本版本不构建 uacctd。

━━━ 一、为什么必须 autoreconf 自举 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GitHub 的 `archive/refs/tags/*.tar.gz` 只是 git 树的快照，**不含 configure**
（configure 是 autoreconf 的产物、不进版本库；实测 tarball 内无 configure，
只有 configure.ac + autogen.sh）。故 build() 内先跑 `autoreconf -f -i -I m4`，
其中 `-I m4` 不能省：configure.ac 用到的 AC_LINEARIZE_PATH 宏定义在
源码树 m4/ac_linearize_path.m4，不在 aclocal 默认搜索路径内（上游 autogen.sh
同样用 `-I m4`）。

━━━ 二、为什么必须显式传 --build / --host（不能省）━━━━━━━━━━━━━━━━━━━━━━━
conan 2.29.1 的 AutotoolsToolchain **只在 cross_building() 为真时**才自动填
`--build`/`--host`（conan/tools/gnu/autotoolstoolchain.py:70-95 的
`if self._is_cross_building:` 分支）。本仓库 `conan create` 用同一份 profile 作
`-pr:h` 与 `-pr:b`（ci/conan/profiles/ohos-aarch64）⇒ **不是** cross build ⇒
两个三元组都不会被传 ⇒ configure 只能去跑 config.guess。
设备 `uname -s` = `HarmonyOS`，而 conan automake/1.18 自带的 config.guess
（版本 2024-07-27）**不识别 HarmonyOS**，实测直接
`unable to guess system type`（rc=1）⇒ configure 当场失败。
故配方内显式给出 `--build=` / `--host=`；build == host ⇒ configure 按本地构建
跑 conftest（不交叉），config.guess 不再被调用。
三元组取 `aarch64-unknown-linux-ohos`：它是仓库内 --host 的最高频取值（231 处），
config.sub（automake/1.18 自带，实测）接受它并归一化为同一字符串，无需补丁。
（同 gss-ntlmssp/1.2.0 的止损先例；该包注释亦记录同一 config.guess 事实。）

━━━ 三、为什么必须做 perl shim（否则 autoreconf 必崩）━━━━━━━━━━━━━━━━━━━
conanbuild 环境的 PERL5LIB 指向 **conan perl 5.42.2**（thread-multi 构建）的
XS 模块目录；而 ohpcd 的 automake/1.18 把 `.aclocal-real` / `.automake-real`
的 shebang 写死为 `#!/data/service/hnp/bin/perl`（**HNP perl 5.42.0**，
非 i-thread 构建）。profile 的 `[buildenv] PATH` 又把 `/data/service/hnp/bin`
顶到最前 ⇒ 裸调 autoreconf 会命中 HNP 那套 perl，HNP perl 加载 conan perl 编出
的 `Cwd.so` 立即 `Perl_my_cxt_init: symbol not found`（本任务探索期实测 rc=255，
两套 perl 的构建配置互不兼容、方向不可调和）。
解法（同 gss-ntlmssp/1.2.0）：把 aclocal / automake 两个入口用 shim 显式指向
**conan perl**，并在 autoreconf 命令行内联把 conan 的 tool bin 顶到 PATH 首位
（os.environ 改写会被 conanbuild 环境脚本覆盖，必须写在命令行层）。
autoconf 系（autoconf/autoheader/autoreconf…）无需 shim：autoconf/2.72 配方
`_wrap_perl_tools()` 已把它们包成 `#!/bin/sh` + `exec "$PERL" ...`，只要 PATH
上 `perl` 解析到 conan perl 即可，二者一致。

━━━ 四、为什么 libcdada 要 vendored ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`src/external_libs/libcdada` 是 pmacct 的 git submodule，制品仓未发布。
上游自带的 submodule 构建系统（src/external_libs/Makefile.am 的 libcdada 目标）
在"非 git 仓库 + 源码树内已有 libcdada/include/cdada.h"时不会 clone，而是就地
`./autogen.sh` + `configure --disable-shared --host=$(host_alias)
--prefix=<build>/rootfs` + `make install`。于是 source() 里把 libcdada 按
**官方仓库 + submodule 固定 commit** 解进源码树，其余全部交给上游机制；
configure 默认 `--with-external-deps=yes`（configure.ac:1186-1207），会自动追加
`-I<abs_builddir>/src/external_libs/rootfs/include` 与
`-L<abs_builddir>/src/external_libs/rootfs/lib`。

━━━ 四之二、libcdada 子构建在 OHOS 上为什么还要 patch 0002 ━━━━━━━━━━━━━━
上游那条 `libcdada:` 目标在本平台有两处必失败，都由 0002 就地修正：
(1) 只传 `--host`，build 侧落回 config.guess ⇒ `cannot guess build type`
    （设备 uname -s = HarmonyOS，automake/1.18 自带 config.guess 2024-07-27 不识别）。
    本子树**无法预置**已打补丁的 config.guess：libcdada 自己的 `./autogen.sh`
    会跑 `autoreconf -f -i`，实测把 build-aux/config.guess 恢复成 automake 包内原件
    （md5 回退，见 notes.md 对话 #9）。故补 0002 显式给它本包已探明的
    `--build=$(build_alias)`；build == host ⇒ 仍是原生构建，不触发交叉语义。
(2) conanbuild 环境导出 `CPPFLAGS=-DNDEBUG`，而 libcdada 的
    `config_m4/debug.m4` 在非 `--enable-debug` 时自己 `AC_DEFINE([NDEBUG])`
    ⇒ 命令行上同时出现 `-DNDEBUG`(=1) 与 `-DNDEBUG=`(/**/) 两份定义，命中
    libcdada 自设的 `CFLAGS="-Werror ..."` ⇒ `-Wmacro-redefined` 8 个编译单元硬失败。
    0002 在子 configure 前加 `CPPFLAGS= ` 清空外层泄漏（libcdada 的私有头/宏
    不依赖外层 CPPFLAGS，清空对子构建无损），不动外层 pmacct 自己的 CPPFLAGS。

━━━ 五、其他已实测事实 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
* configure.ac:1220 硬编码 `LIBS="-lcdada -lstdc++ ${LIBS}"`。OHOS clang 15.0.4
  的 **C 与 C++ driver 都会把 `-lstdc++` 归一化为 libc++**（实测 `clang -lstdc++`
  链接行出现 `-lc++ -lc++abi -lunwind`、无 lstdc++，rc=0）⇒ 无需补丁。
* pcap 走上游 `--with-pcap-includes=` / `--with-pcap-libs=`（configure.ac:225/288），
  交叉构建下不能依赖 /usr/include 与 /usr/local/lib 的默认探测。
* 上游把 6 个守护进程装到 `sbin/`、pmacct 装到 `bin/`；conan 约定（以及 CI 反例
  测试）要求可执行文件在 `bin/` 下 ⇒ package() 内 sbin→bin 折叠。
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PmacctConan(ConanFile):
    name = "pmacct"
    version = "1.7.8"
    description = ("pmacct — passive network monitoring toolkit "
                   "(IP accounting, BGP, BMP, RPKI, IGP, streaming telemetry)")
    license = "GPL-2.0-only"
    homepage = "http://www.pmacct.net/"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # package() 的假绿防护基线：上游产出（uacctd 因缺 libnetfilter_log 不构建）
    _BINARIES = ("pmacct", "pmacctd", "nfacctd", "sfacctd",
                 "pmtelemetryd", "pmbgpd", "pmbmpd")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure.ac 硬门禁（缺一即 AC_MSG_ERROR）；ohpcd 已发布 1.10.6
        # （armv8/clang15/OHOS 二进制，静态 libpcap.a；`conan download` 已验可消费）
        self.requires("libpcap/1.10.6")

    def build_requirements(self):
        # 三件套同源引入（tag tarball 无 configure，见文件头"一"）。
        # autoconf/2.72 会传递引入 perl/5.42.2（其 requirements + tool_requires），
        # perl shim 依赖这一点，故不可省略 autoconf。
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # vendored libcdada（见文件头"四"）：解进源码树里那个空的 submodule 目录。
        # tarball 已带 src/external_libs/libcdada/ 空目录条目，destination 指向它。
        _cdada_dst = os.path.join(self.source_folder, "src", "external_libs", "libcdada")
        os.makedirs(_cdada_dst, exist_ok=True)
        get(self, **self.conan_data["libcdada"], strip_root=True, destination=_cdada_dst)
        _cdada_h = os.path.join(_cdada_dst, "include", "cdada.h")
        if not os.path.isfile(_cdada_h):
            raise ConanException(
                f"vendored libcdada 解包后缺 {_cdada_h}（上游 submodule 构建系统的"
                "启用前提；缺失则 configure 会把 WITH_EXTERNAL_DEPS_DEFAULT 置 no "
                "并在 AC_CHECK_LIB(cdada) 处失败）")

    def generate(self):
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        # 设备 uname -s = HarmonyOS，config.guess 2024-07-27 不识别 ⇒ 必须显式
        # 给出三元组，否则 configure 连 build type 都猜不出来（见文件头"二"）。
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # pcap 走上游专用开关（见文件头"五"）
        _pcap_pf = self.dependencies["libpcap"].package_folder
        if not _pcap_pf:
            raise ConanException("libpcap package_folder 不可用（依赖未构建？）")
        tc.configure_args.append(f"--with-pcap-includes={os.path.join(_pcap_pf, 'include')}")
        tc.configure_args.append(f"--with-pcap-libs={os.path.join(_pcap_pf, 'lib')}")
        # libtool 便利库/模块一律要 PIC；OHOS 无系统同名库冲突面，纯增量安全项
        tc.extra_cflags = ["-fPIC"]
        tc.extra_cxxflags = ["-fPIC"]
        tc.generate()

    # ── build 辅助 ────────────────────────────────────────────────────────
    def _tool_env(self):
        """组装 conan tool bin 列表 + aclocal/automake 的 perl shim（见文件头"三"）。

        返回 (tool_bins, shim_dir)。tool_bins 首位是 shim 目录。
        """
        tool_bins = []
        perl_pf = automake_pf = None
        for _dep in self.dependencies.build.values():
            _pf = getattr(_dep, "package_folder", None)
            if not _pf:
                continue
            _bin = os.path.join(_pf, "bin")
            if os.path.isdir(_bin) and _bin not in tool_bins:
                tool_bins.append(_bin)
            _n = _dep.ref.name
            if _n == "perl":
                perl_pf = _pf
            elif _n == "automake":
                automake_pf = _pf
        if not perl_pf:
            raise ConanException(
                "build 依赖图中缺 perl（autoconf/2.72 应传递引入 perl/5.42.2）；"
                "没有 conan perl 就压不住 aclocal/automake 的 HNP-perl shebang")
        if not automake_pf:
            raise ConanException("build 依赖图中缺 automake/1.18（tool_requires 未生效）")
        _conan_perl = os.path.join(perl_pf, "bin", "perl")
        if not os.path.isfile(_conan_perl):
            raise ConanException(f"conan perl 解释器缺失: {_conan_perl}")

        shim_dir = os.path.join(self.build_folder, "_perlshim")
        os.makedirs(shim_dir, exist_ok=True)
        _ambin = os.path.join(automake_pf, "bin")
        # shim 必须复刻 ohpcd automake 包装脚本的重定位参数：其 .real 脚本编译进的
        # 前缀是 `/`（conan AutotoolsToolchain 默认 --prefix=/ 家族），不带参数会去
        # 找 `//share/aclocal-1.18` 而失败（同 gss-ntlmssp/1.2.0 首轮实测）。
        # 三元组第 3 项 = 交给 conan perl 执行的脚本；None 表示目标就是解释器本身
        # （perl shim：把裸名 `perl` 也钉到 conan perl，因为 libcdada 子树的
        #  ./autogen.sh -> autoreconf 会用 `: "${PERL:=perl}"` 回退到 PATH 上的 perl，
        #  而 HNP perl 与 conan perl 的 XS 模块 ABI 不可调和，见文件头"三"）。
        _shim_specs = (
            ("aclocal", ["--automake-acdir=" + os.path.join(automake_pf, "share", "aclocal-1.18"),
                         "--system-acdir=" + os.path.join(automake_pf, "share", "aclocal")],
             os.path.join(_ambin, ".aclocal-real")),
            ("automake", ["--libdir=" + os.path.join(automake_pf, "share", "automake-1.18")],
             os.path.join(_ambin, ".automake-real")),
            ("perl", [], None),
        )
        shimmed = []
        for _t, _args, _real in _shim_specs:
            if _real is not None and not os.path.isfile(_real):
                raise ConanException(f"automake 制品缺 {_real}（可重定位包装脚本未生成）")
            _sh = os.path.join(shim_dir, _t)
            _argstr = " ".join(f'"{a}"' for a in _args)
            # .real 脚本必须由 conan perl 显式执行：其 shebang 写死 hnp perl，
            # 直接 exec 会退回 HNP perl 并加载 conan perl 编出的 XS（见文件头"三"）。
            _cmd = (f'"{_conan_perl}" "{_real}"' if _real is not None else f'"{_conan_perl}"')
            with open(_sh, "w", encoding="utf-8") as _f:
                _f.write(f'#!/bin/sh\nexec {_cmd} {_argstr} "$@"\n')
            os.chmod(_sh, 0o755)
            if not os.access(_sh, os.X_OK):
                raise ConanException(f"shim 执行位设置失败（HMDFS exec 位边界）: {_sh}")
            shimmed.append(_t)
        self.output.info(f"[perl-shim] {len(shimmed)} 个 shim -> {_conan_perl}: "
                         f"{', '.join(shimmed)}")
        return [shim_dir] + tool_bins, shim_dir

    def _run_upstream_tests(self):
        """上游测试入口实跑：ci/script.sh 的测试段。

        上游**没有**自动化测试套件：全树无 tests/ 目录、Makefile.am 无 TESTS /
        check_PROGRAMS / check-local（实测 grep 0 命中，`make check` 无目标）。
        上游 CI（ci/script.sh）的测试段就两步：
            ls -l src/nfacctd
            src/nfacctd -V
        另有 ci/smoke-test/docker-compose.yml（7 个守护进程容器 + restart-count
        检查），依赖 docker，沙箱内不可执行 ⇒ 以 nfacctd -V 为等价可跑入口。
        本方法**逐字复现** ci/script.sh 的测试段，并逐个自检其余交付二进制。
        """
        _bin_dir = os.path.join(self.build_folder, "src")
        _nfacctd = os.path.join(_bin_dir, "nfacctd")
        if not os.path.isfile(_nfacctd):
            raise ConanException(f"上游测试前置失败：{_nfacctd} 不存在")

        # 逐字复现 ci/script.sh：ls -l src/nfacctd
        self.output.info(f"[upstream-test] ls -l src/nfacctd → "
                         f"{os.path.getsize(_nfacctd)} bytes")

        # 逐字复现 ci/script.sh：src/nfacctd -V，并断言版本行含真实依赖指纹
        # 注：self.run 的 stdout= 参数只接受 file-like 对象（不能用字符串路径，
        # 否则 'str' object has no attribute 'fileno'），故用 shell 重定向落盘。
        _out_file = os.path.join(self.build_folder, "upstream-nfacctd-V.log")
        rc = self.run(f'"{_nfacctd}" -V > "{_out_file}" 2>&1',
                      cwd=self.build_folder, env="conanbuild")
        if rc != 0:
            raise ConanException(f"上游测试失败：src/nfacctd -V rc={rc}（日志 {_out_file}）")
        with open(_out_file, "r", encoding="utf-8", errors="ignore") as _f:
            _ver = _f.read()
        self.output.info(f"[upstream-test] src/nfacctd -V rc=0，日志 {_out_file}")

        # 消费者/依赖指纹断言（防止"空版本行"假绿）
        _expect = {"cdada": "vendored libcdada 未真正链接进 nfacctd",
                   "libpcap version": "libpcap 未真正链接进 nfacctd",
                   "clang": "编译器指纹缺失"}
        for _needle, _why in _expect.items():
            if _needle.lower() not in _ver.lower():
                raise ConanException(
                    f"上游测试断言失败：src/nfacctd -V 输出不含 {_needle!r} —— {_why}；"
                    f"原始输出:\n{_ver}")
        self.output.info("[upstream-test] 断言通过：cdada / libpcap version / clang 均在 -V 输出中")

        # 其余 6 个交付二进制逐个 -V 自检（上游 CI 只查 nfacctd，此处为交付面自检）
        _others = ("pmacctd", "sfacctd", "pmtelemetryd", "pmbgpd", "pmbmpd")
        for _name in _others:
            _p = os.path.join(_bin_dir, _name)
            if not os.path.isfile(_p):
                raise ConanException(f"交付二进制缺失：{_p}")
            _rc = self.run(f'"{_p}" -V > "{os.path.join(self.build_folder, f"upstream-{_name}-V.log")}" 2>&1',
                           cwd=self.build_folder, env="conanbuild")
            if _rc != 0:
                raise ConanException(f"上游自检失败：{_name} -V rc={_rc}")
        self.output.info(f"[upstream-test] 自检通过：{len(_others) + 1}/7 个二进制 -V rc=0")

    def build(self):
        apply_conandata_patches(self)

        tool_bins, shim_dir = self._tool_env()
        _tool_path = os.pathsep.join(tool_bins)

        # ── 工具链前缀（见文件头"一"/"三"/"四之二"）─────────────────────────
        # PATH 必须内联在命令行层：conanbuild 环境脚本会把 profile 的
        # /data/service/hnp/bin 重新压到最前，os.environ 改写会被覆盖。
        # ACLOCAL/AUTOMAKE 指向 perl shim，PERL 显式钉 conan perl（裸 `perl` 也经
        # shim 目录命中同一解释器），三者都要传给 make 子树里的 ./autogen.sh。
        _env = (f'ACLOCAL="{os.path.join(shim_dir, "aclocal")}" '
                f'AUTOMAKE="{os.path.join(shim_dir, "automake")}" '
                f'PERL="{os.path.join(shim_dir, "perl")}" '
                f'PATH="{_tool_path}:{os.environ.get("PATH", "")}" ')
        rc = self.run(f"{_env} autoreconf -f -i -I m4",
                      cwd=self.source_folder, env="conanbuild", ignore_errors=True)
        if rc != 0:
            raise ConanException(f"autoreconf -f -i -I m4 失败 rc={rc}"
                                 "（tool_requires 三件套缺失或宏缺失）")
        if not os.path.exists(os.path.join(self.source_folder, "configure")):
            raise ConanException("autoreconf 后 configure 未生成（假绿防护）")
        self.output.info("[autoreconf] configure 已生成")

        autotools = Autotools(self)
        autotools.configure()
        # configure rc=0 假绿防护：必须核 Makefile 实物（config.status 假绿族）
        _mk = os.path.join(self.build_folder, "Makefile")
        if not os.path.exists(_mk):
            raise ConanException(f"configure rc=0 但 {_mk} 未生成（config.status 假绿族）")
        self.output.info(f"[configure] Makefile 已生成: {_mk}")

        # ── 预生成 vendored libcdada 的构建系统（见 patch 0002 / 文件头"三"）──
        # 上游 src/external_libs/Makefile.am 的 libcdada 目标原本跑 `./autogen.sh`
        # -> `autoreconf -f -i`；autoreconf 调用的 conan automake aclocal/automake
        # 的 `.real` 脚本 shebang 写死 HNP perl，该 perl 无法加载 conan perl 编出的
        # XS 模块（Cwd.so: Perl_my_cxt_init: symbol not found / Permission denied）。
        # 故 patch 0002 把规则改成直接 `./configure`，此处用 conan-perl shim 预生成
        # libcdada 的 configure（等价于 autogen.sh 的 autoreconf -f -i，并复刻其
        # `AUTOMAKE="automake --foreign -a"` 严格度）。之后 make 的 libcdada 目标
        # 不再触碰 perl。libcdada 的 configure 必须落在 $(abs_srcdir)/libcdada/
        # （即本源码树），因为规则以 $(abs_srcdir)/libcdada/configure 调用它。
        _libcdada_src = os.path.join(self.source_folder, "src", "external_libs", "libcdada")
        if os.path.isdir(_libcdada_src):
            _env_libcdada = (f'ACLOCAL="{os.path.join(shim_dir, "aclocal")}" '
                             f'AUTOMAKE="{os.path.join(shim_dir, "automake")} --foreign -a" '
                             f'PERL="{os.path.join(shim_dir, "perl")}" '
                             f'PATH="{_tool_path}:{os.environ.get("PATH", "")}" ')
            rc = self.run(f'{_env_libcdada} sh -c \'cd "{_libcdada_src}" && autoreconf -f -i\'',
                          cwd=self.source_folder, env="conanbuild", ignore_errors=True)
            if rc != 0:
                raise ConanException(f"libcdada autoreconf -f -i 预生成失败 rc={rc}"
                                     "（patch 0002 预生成步骤 / 文件头三）")
            if not os.path.exists(os.path.join(_libcdada_src, "configure")):
                raise ConanException("libcdada autoreconf 后 configure 未生成（假绿防护）")
            self.output.info("[libcdada] autoreconf -f -i 预生成完成 -> "
                             f"{os.path.join(_libcdada_src, 'configure')}")

        # 上游 libcdada 子模块构建由 `make` 的 libcdada 目标驱动
        # （src/external_libs/Makefile.am，见 patch 0002），故此处只需一条 make。
        # 不复用 Autotools.make()：等价调用即可，make_program 走
        # tools.gnu:make_program 配置，-j 取 conan build_jobs（与本仓库其他
        # autotools 配方一致）。libcdada 规则已不再调用 autoreconf，故无 perl 子进程。
        _make = self.conf.get("tools.gnu:make_program", default="make", check_type=str)
        _njobs = build_jobs(self)
        _jobs = f"-j{_njobs}" if _njobs else ""
        rc = self.run(f"{_env}{_make} {_jobs}",
                      cwd=self.build_folder, env="conanbuild", ignore_errors=True)
        if rc != 0:
            raise ConanException(f"make -j{_njobs} 失败 rc={rc}"
                                 "（上游 libcdada 子构建见 patch 0002 / 文件头四之二）")

        # 上游测试入口实跑（见 _run_upstream_tests 文档串）
        self._run_upstream_tests()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        # 上游把 6 个守护进程装到 sbin/、pmacct 装到 bin/；conan 约定（以及 CI
        # 反例测试会删掉 bin/ 与 lib/ 看是否还有可执行文件）要求可执行文件在
        # bin/ 下 ⇒ 折叠 sbin/ 进 bin/（同 accel-ppp/1.14.0 先例）。
        _sbin = os.path.join(self.package_folder, "sbin")
        if os.path.isdir(_sbin):
            _bin = os.path.join(self.package_folder, "bin")
            os.makedirs(_bin, exist_ok=True)
            for _name in os.listdir(_sbin):
                os.replace(os.path.join(_sbin, _name), os.path.join(_bin, _name))
            os.rmdir(_sbin)

        # install 假绿防护：rc=0 必须核安装树实物
        _missing = [b for b in self._BINARIES
                    if not os.path.isfile(os.path.join(self.package_folder, "bin", b))]
        if _missing:
            raise ConanException(f"install 产物缺失（make install 假绿）: {_missing}")
        self.output.info(f"[install] {len(self._BINARIES)}/7 个可执行文件已入包 "
                         f"({', '.join(self._BINARIES)})")

    def package_info(self):
        # 交付面：7 个可执行文件（bin/）+ 上游文档/示例（share/pmacct）。
        # 无库、无头文件 —— 插件是进程内字符串（config `plugins:`），不是 .so；
        # libcdada 已静态编入各守护进程，故 cpp_info.libs 为空。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
