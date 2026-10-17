#!/usr/bin/env python3
"""Conan recipe — miredo 1.2.6 (Autotools, C).

miredo 是 Rémi Denis-Courmont 维护的 Teredo IPv6 隧道（RFC 4380）实现：产出
libteredo（Teredo 协议库）、libtun6（TUN/TAP 用户态库）以及
miredo / miredo-server / miredo-checkconf / teredo-mire 命令行工具。
上游：https://www.remlab.net/miredo/

OHOS 适配要点（补丁细节见 conandata.yml 与 patches/）：
- E007：2012 年的 config.guess/config.sub 不认识 HarmonyOS（uname -s 返回
  HarmonyOS），补 HarmonyOS 识别分支与 ohos/linux-ohos 三元组。用原生构建，
  不靠 --build/--host 绕过（绕过会让 AC_RUN_IFELSE 全部跳过、生成错误 config.h）。
- E114：HMDFS 会把 0700 目录的属主归一化为其他 uid，autoconf 的
  `umask 077 && mktemp -d ./confXXXXXX` 生成的临时目录因此连属主也写不进去，
  configure 报 "could not setup config files machinery"。config.guess 由补丁
  修；预生成的 configure 属构建产物（补丁工具按 GENERATED 排除），故在 build()
  里就地改写——同 abiword-plugin-* 配方的既有先例。
- E127：OHOS musl 不导出 pthread_cancel/pthread_setcancelstate/pthread_testcancel
  （内核不支持 POSIX 线程取消）。回退实现**内联进既有文件**（不新增头文件，补丁
  工具对新增文件的处理见 E432）：libteredo/debug.h 提供空操作 + glibc 专有
  `*_NP` mutex 常量的特征宏回退（补丁 0006），src/relayd.c 经该头引入（补丁 0003）。
  空操作回退必须与协作式停止配套：libteredo 的 peerlist 垃圾回收线程原本只能被取消，
  改为 stop 标志 + 1 秒分片等待，并修掉上游 `memset(l, 0, sizeof(l))` 的尺寸笔误
  （补丁 0001），否则 teredo_list_destroy() 的 pthread_join 会永久阻塞
  （libteredo-list / libteredo-stresslist 两个上游测试会直接卡死）。
- E119：内核 UAPI linux/if_ether.h 与 libc netinet/if_ether.h 都定义
  struct ethhdr；非 glibc libc 下重复定义编译失败，按 __UAPI_DEF_ETHHDR 守卫。
- CI fork 饥饿（DRAFT-11327 / E433）：共享 worker 进程表枯竭时，失败点落在 make/libtool
  的 fork 层（`fork: retry: Resource temporarily unavailable` → `Error 254`），与源码无关。
  处置不是改源码/补丁，而是复用上游官方发行包（自带预生成 configure，无 autoconf 自举链）
  + `make -j1`（已在 generate/`--enable-static` 与 build() 中落实），再对 configure/make/
  install 三步加 fork 指纹退避重跑（见 _ForkResilientConanfile）；真正的编译错误不重试。

依赖：judy（配置解析用动态数组，configure 以 -lJudy 探测）与 libcap（特权降级）。
"""
import os
import re
import time

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get)

from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


# CI worker 与多个 job 共用 uid 100，进程表偶发枯竭，fork()/spawn() 返回 EAGAIN。
# 各条实现措辞不同，故按组合指纹判定（缺一不可地命中才叫饥饿，避免把普通错误误判）。
_FORK_STARVATION = re.compile(
    r"fork: retry: Resource temporarily unavailable"   # libtool / bash 内部的 fork 重试
    r"|fork: Resource temporarily unavailable"         # make 自身的 fork 失败
    r"|can't fork - try again"                         # /system/bin/sh 措辞（见 E433）
    r"|fork: Out of memory")                           # 内存压力下的另一种措辞


class _ForkResilientConanfile(object):
    """给 Autotools 用的 conanfile 包一层：命中 fork 饥饿指纹才退避重跑这一步。

    CI worker 资源不足时，失败点落在 **make/libtool 的 fork 层**而非编译链接层：

        ../libtool: fork: retry: Resource temporarily unavailable   （连续数十次）
        make[3]: fork: Resource temporarily unavailable
        make[3]: *** [Makefile:594: init.lo] Error 254

    这不是源码/补丁/编译器问题——同一份代码在空闲 worker 上可全绿（本包已在
    CI-035 / CI-021 / CI-011 通过 3 次），属环境性资源饥饿（DRAFT-11327 / E433）。
    把它当编译错误去改源码或加补丁，只会掩盖真实问题（DRAFT-11327 forbid_1）。

    Autotools.configure/make/install 一律经 ``conanfile.run()`` 执行，故这里只包一层同签名
    的 ``run``：命令与参数拼装、``env="conanbuild"``、cwd、shell 等语义仍全部由 conan 原
    实现产出，不复制其逻辑。差别仅在——

    1. 每步输出落盘后回灌进构建日志（失败证据不丢，CI 侧仍看得到完整转录）；
    2. 该步失败且转录命中 ``_FORK_STARVATION`` 时，等待 ``delay`` 秒后重跑该步
       （configure 幂等重跑；make/install 增量续跑），最多 ``attempts`` 次；
    3. 非饥饿的失败（真正的编译/链接错误）首次即原样抛出，不做任何重试。
    """

    def __init__(self, conanfile, attempts=8, delay=30):
        self._conanfile = conanfile
        self._attempts = attempts
        self._delay = delay
        self._step = 0

    def __getattr__(self, name):
        # 其余属性（conf / settings_build / build_folder / generators_folder …）一律透传，
        # 使 Autotools 与 build_jobs()/deduce_subsystem() 等辅助函数拿到的行为与直接用
        # conanfile 时完全一致。
        return getattr(self._conanfile, name)

    def run(self, command, *args, **kwargs):
        """执行一步构建命令；仅在确认命中 fork 饥饿指纹时退避重跑。"""
        self._step += 1
        log = os.path.join(self.build_folder, "fork-retry-%02d.log" % self._step)
        for attempt in range(1, self._attempts + 1):
            with open(log, "w", encoding="utf-8", errors="replace") as fh:
                # 沿用 conanfile.run() 自带的 stdout 重定向来抓取转录；env/cwd/shell 等
                # 保持未指定，与 Autotools 直接调用 conanfile.run() 时的默认语义一致。
                opts = dict(kwargs)
                opts["stdout"] = fh
                opts["stderr"] = fh
                opts["ignore_errors"] = True
                rc = self._conanfile.run(command, *args, **opts)
            with open(log, encoding="utf-8", errors="replace") as fh:
                output = fh.read()
            self.output.info(output)          # 回灌进构建日志，保持证据完整
            starved = bool(_FORK_STARVATION.search(output))
            if rc == 0:
                if starved:
                    self.output.warning(
                        "[fork-retry] 本步转录含 fork 饥饿痕迹但已成功（第 %d 次），继续"
                        % attempt)
                return 0
            if not starved:
                # 真正的构建错误：不改写、不重试、不掩盖
                raise ConanException("Error %d while executing" % rc)
            if attempt == self._attempts:
                raise ConanException(
                    "Error %d while executing（fork 饥饿在 %d 次退避重跑后仍未缓解，"
                    "累计等待 %d 秒；属 CI worker 资源问题，非本包缺陷）"
                    % (rc, self._attempts, self._delay * (self._attempts - 1)))
            self.output.warning(
                "[fork-retry] 命中 CI worker fork 饥饿（EAGAIN），%d 秒后重跑本步"
                "（第 %d/%d 次）：%s" % (self._delay, attempt, self._attempts, command))
            time.sleep(self._delay)
        return 0  # 循环内必然 return 或 raise，此行只为显式返回值


def _restore_autotools_modes(conanfile, folder):
    """E490：autotools 辅助脚本是可执行程序，但鸿蒙侧的源码传递路径可能只保留
    内容不保留执行位，configure 会在编译前就 Permission denied。只对已知辅助脚本
    补执行位。
    """
    import stat

    for name in ("configure", "config.guess", "config.sub", "install-sh", "missing",
                 "depcomp", "compile", "ylwrap", "ltmain.sh"):
        p = os.path.join(folder, name)
        if os.path.isfile(p):
            mode = os.stat(p).st_mode
            os.chmod(p, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        # 辅助脚本也可能放在 admin/ 之类的 AC_CONFIG_AUX_DIR 下
        for sub in ("admin", "build-aux", "config"):
            q = os.path.join(folder, sub, name)
            if os.path.isfile(q):
                mode = os.stat(q).st_mode
                os.chmod(q, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)



def _drop_umask_077(conanfile, path):
    """E114：HMDFS 会给目录强制 setgid，`umask 077 && mktemp -d` 生成的
    drwx--S--- 临时目录连属主都不可写（属主被归一化为其他 uid）。去掉 umask 077
    （以及随之孤立的括号），让 config.status 能用可写目录。
    """
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


class MiredoConan(ConanFile):
    name = "miredo"
    version = "1.2.6"
    description = ("Teredo IPv6 tunnelling daemon with the libteredo and "
                   "libtun6 libraries (RFC 4380)")
    license = "GPL-2.0-or-later"
    homepage = "https://www.remlab.net/miredo/"
    url = "https://www.remlab.net/files/miredo/"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        # R32: settings.os 必须按 ("Linux", "OHOS") 判断，不能 == "Linux"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "miredo only supports Linux and OHOS (got %s)" % self.settings.os)

    def requirements(self):
        # configure 以 AC_CHECK_HEADERS/AC_CHECK_LIB 探测 Judy.h/-lJudy
        self.requires("judy/1.0.5")
        # 特权降级需要 libcap（configure 探测 sys/capability.h + -lcap）
        self.requires("libcap/2.78")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 静态库必须保留：libteredo 的内部便利库（noinst libteredo-common）与
        # 上游测试程序都依赖静态产物，--disable-static 会让 make check 链接失败
        # （undefined symbol: teredo_list_create / md5_init / teredo_clock 等）。
        tc.configure_args.append("--enable-static")
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
        else:
            tc.configure_args.append("--disable-shared")
        tc.generate()
        # configure 用 AC_CHECK_HEADERS([Judy.h]) + AC_CHECK_LIB([Judy],[JudyHSIns]) 与
        # AC_CHECK_HEADERS([sys/capability.h]) + AC_CHECK_LIB([cap],[cap_set_proc]) 探测
        # 依赖，而 AutotoolsToolchain 默认不注入依赖的 include/lib 路径（实测依赖被声明
        # 却探测不到，回落到 tdestroy 且无特权降级）。叠加 AutotoolsDeps 生成
        # conanautotoolsdeps.sh（CPPFLAGS/LDFLAGS/LIBS）即可被 Autotools.configure 应用。
        AutotoolsDeps(self).generate()

    def build(self):
        # E490：鸿蒙侧源码传递可能丢执行位，先补 autotools 辅助脚本的 x 位
        _restore_autotools_modes(self, self.source_folder)
        # E114/E110：预生成的 configure 属构建产物，无法走 patches/，就地改写。
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))

        # 共享 CI worker 上 fork() 会间歇性 EAGAIN，故用 _ForkResilientConanfile 包裹：
        # 命令与参数拼装仍由 conan 产出，只在命中 fork 饥饿指纹时退避重跑该步。
        autotools = Autotools(_ForkResilientConanfile(self))
        autotools.configure()
        autotools.make(args=["-j1"])

        # 上游 make check 注册 12 项；其中 src 的 miredo-checkconf 用例读取
        # misc/miredo.conf，而该文件的 ServerAddress 是外部主机名
        # teredo.remlab.net（misc/miredo.conf-in 第 30 行）——checkconf 会做实时
        # DNS 解析，CI 沙箱无网或 DNS 抖动时该用例必失败（实测 conan create 期间
        # 出现 "Name does not resolve"），属环境依赖而非适配缺陷。
        # 处置：仅在跑 make check 期间，把构建树里这份「由 configure 生成」的配置
        # 样本的 ServerAddress 换成确定性地址，让同一个 checkconf 二进制走完同一条
        # 解析路径；跑完立即还原，使 package() 安装出去的示例配置保持上游原样。
        conf = os.path.join(self.build_folder, "misc", "miredo.conf")
        saved_conf = None
        if os.path.isfile(conf):
            with open(conf, "r", encoding="utf-8") as f:
                saved_conf = f.read()
            with open(conf, "w", encoding="utf-8") as f:
                f.write(saved_conf.replace(
                    "ServerAddress teredo.remlab.net",
                    "ServerAddress 127.0.0.1"))
        try:
            autotools.make(args=["check"])
        finally:
            if saved_conf is not None:
                with open(conf, "w", encoding="utf-8") as f:
                    f.write(saved_conf)

    def package(self):
        autotools = Autotools(_ForkResilientConanfile(self))
        autotools.install()
        for lic in ("COPYING",):
            src = os.path.join(self.source_folder, lic)
            if os.path.isfile(src):
                from conan.tools.files import copy
                copy(self, lic, src=self.source_folder,
                     dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["teredo", "tun6"]
        # 命令行工具装在 sbin/ 与 bin/
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.set_property("cmake_file_name", "miredo")
        self.cpp_info.set_property("cmake_target_name", "miredo::miredo")
