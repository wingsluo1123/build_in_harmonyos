#!/usr/bin/env python3
"""Conan recipe for userv 1.2.3 — user services client and daemon (OHOS).

上游主页: https://www.chiark.greenend.org.uk/~ian/userv/
官网源码: chiark.greenend.org.uk（1.2.3 的官方 tarball 只在匿名 FTP 上，本仓改用
          Debian 源码池里同版本的原始源码包，等价性证据见 conandata.yml / notes.md）
构建系统: 自带 configure（autoconf 生成）+ 手写 Makefile.in（不是 automake 工程）
产物:     bin/userv    客户端（上游以 setuid root 装到 /usr/bin）
          bin/uservd   守护进程（上游装到 /usr/sbin，本配方统一放 bin/，见下第 3 条）
          res/userv/   /etc/userv 配置骨架（上游 system.default / system.override 示例）

OHOS 适配要点（逐条对照上游 1.2.3 源码，不是猜测）:

1. 刻意不使用 AutotoolsToolchain。
   Conan 的 AutotoolsToolchain 在 Release/RelWithDebInfo/MinSizeRel 下会把 -DNDEBUG
   放进 CPPFLAGS（AutotoolsToolchain.ndebug），而 userv 把这个宏当作"构建配置错误"：
     * client.c:1335   #ifdef NDEBUG / # error Do not disable assertions in this
                       security-critical code !
     * overlord.c:273  #ifdef NDEBUG / abort();  /* 运行期直接 abort */
   CI profile 是 build_type=Release，正好命中该分支。虽然 userv 的 Makefile 用
   `CPPFLAGS=@DEBUGDEFS@ $(XCPPFLAGS)` 覆盖了环境里的 CPPFLAGS、未必真把 -DNDEBUG
   传进编译，但依赖这种"侥幸"不可接受：一旦生效，编译期直接 #error，运行期直接 abort。
   改为 VirtualBuildEnv + 从 Conan conf 取 CC/CFLAGS，同样满足 R33
   （不使用 CI 上可能为空的 shell 变量 CC/CFLAGS）。

2. `make install` 的 INSTALL_FLAGS 默认是 `-o root -g 0`（Makefile.in:35-36），
   CI 以普通用户（currentUser）运行时 install 会以
   "cannot change ownership of ..." 失败，因此在 make 命令行覆盖 INSTALL_FLAGS=。

3. uservd 默认装到 $(sbindir)（= /usr/sbin）。CI 的 L2/L5 门禁只扫描 bin/，
   且 Conan 标准可执行目录是 bin/，因此 make install 时传 sbindir=/bin，
   两个可执行文件都落在 <pkg>/bin/ 下（同 archives/d/duo-unix 的处理方式）。

4. /etc/userv 的配置骨架用 etcdir=/res 收到 <pkg>/res/userv/：Conan 包不应往系统
   /etc 写文件，配置本身也是宿主机相关（system.default/system.override 由系统集成方提供）。
   注意 bindir/sbindir/etcdir 一律传绝对路径，避免 $(DESTDIR)$(var) 直接拼接时缺斜杠。

5. userv 构建期需要 md5sum（上游 INSTALL「SYSTEM REQUIREMENTS / Programs」明确列出，
   只用于构建期）：Makefile 的 pcsum.h 目标用 `cat ... | $(MD5SUM)` 生成
   client/daemon 之间的协议校验和，而 configure 的 AC_CHECK_PROGS 只认
   md5sum/md5/gmd5sum，找不到就留空 → 构建必失败。因此 build_requirements() 里声明
   coreutils/9.10（ohpcd 已发布，OHOS/armv8/clang15 二进制内含 md5sum，已核对），
   并在 generate() 里显式把它的 bin 目录 prepend 到 PATH（不依赖 Conan 对 tool_requires
   的隐式 PATH 合成，原因见 generate() 注释与本机实测记录 notes.md §六）。

6. 上游 1.2.3 没有 make check 校验集（Makefile.in:113-114 只 echo 一行说明），
   官方测试位于 tarball 的 tests/（Debian autopkgtest，needs-root + 系统级 setuid 安装 +
   常驻守护进程），无法在 Conan 构建沙箱内运行，清点与裁剪理由见 notes.md；
   build() 仍然调用 make check（上游官方入口），真实断言由 test_package 承担（R34）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class UservConan(ConanFile):
    name = "userv"
    version = "1.2.3"
    description = ("userv — user services client and daemon: a Unix system facility to let "
                   "one program invoke another when only limited trust exists between them")
    license = "GPL-3.0-or-later"
    homepage = "https://www.chiark.greenend.org.uk/~ian/userv/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 无外部库依赖：只用 POSIX libc（socket/setreuid/syslog/fnmatch 等）
        pass

    def build_requirements(self):
        # 构建期需要 md5sum 生成 pcsum.h（上游 INSTALL 明确要求，见文件头第 5 条）
        self.tool_requires("coreutils/9.10")

    def layout(self):
        basic_layout(self)
        # userv 的 Makefile 只支持源码树内构建（pcsum.h / spec.sgml 等目标都用相对路径），
        # 与 archives/z/zlib/1.3.1 相同的处理：把 build 目录指到源码目录本身。
        self.folders.build = "."

    def validate(self):
        # userv 依赖 setreuid/syslog/AF_UNIX 等 POSIX 接口（R32：平台判断用元组写法）
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"{self.ref} supports POSIX systems (Linux/OHOS) only")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33：编译器和编译选项一律来自 Conan profile/conf，不依赖 shell 里的 CC/CFLAGS。
        # 这里不用 AutotoolsToolchain 的原因见文件头第 1 条（-DNDEBUG）。
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cflags = list(self.conf.get("tools.build:cflags", default=[], check_type=list))
        # userv 只产出可执行文件，取 exelinkflags；Conan 没有 tools.build:ldflags 这个 conf
        # （本机 conan create 实测报 'does not exist in configuration list'）
        ldflags = list(self.conf.get("tools.build:exelinkflags", default=[], check_type=list))
        if not cflags:
            cflags = ["-O2"]  # configure 自带的 -g 无意义；OPTIMISE 也会再归一到 -O2

        # profile [buildenv]（PATH / SHELL / CONFIG_SHELL）由 VirtualBuildEnv 落成脚本
        VirtualBuildEnv(self).generate()

        env = Environment()
        env.define("CC", compilers.get("c", "clang"))
        env.define("CXX", compilers.get("cpp", "clang++"))
        env.define("CFLAGS", " ".join(cflags))
        env.define("LDFLAGS", " ".join(ldflags))
        # 上游构建期需要 md5sum（生成 pcsum.h，见文件头第 5 条）。这里显式把
        # coreutils 的 bin 放到 PATH 最前，不依赖 VirtualBuildEnv 对 tool_requires 的
        # 隐式 PATH 合成：本机 conan create 实测，当 profile [buildenv] 已经定义 PATH 时，
        # 该隐式合成会被 compose 逻辑丢掉（toolpathprobe 探针：require.run=True、
        # bindirs 存在，但最终 PATH 里没有 coreutils）。
        # 附带好处：pcsum.h 的流水线用到的 cat/cmp/install 也来自 OHOS 打过补丁的
        # GNU coreutils 9.10（其 0005~0012 补丁专门修 OHOS 管道上的 fstat/lseek EACCES）。
        coreutils = self.dependencies.build["coreutils"]
        env.prepend_path("PATH", os.path.join(coreutils.package_folder, "bin"))
        # 脚本名不能取 "conanbuild"/"conanrun"：这两个名字是 Conan 的聚合入口文件，
        # 会被聚合步骤覆盖，并且聚合脚本会 source 到自己（本机实测：环境变量全部丢失）。
        env.vars(self).save_script("conanbuildenv-userv")

    def build(self):
        apply_conandata_patches(self)
        # R5：OHOS 上不一定有可用的 /bin/sh。CONFIG_SHELL/SHELL 由 profile [buildenv] 注入，
        # 但它们只出现在 self.run 的子进程环境里，不在 Conan 进程的 os.environ 里，
        # 所以写成 shell 参数展开、在运行时求值并校验可执行位。
        # 真机实测（2026-10-13 影子 CI 第一轮，Error 127）：影子 CI 设备把 CONFIG_SHELL 设为
        # $HOME/usr/local/bin/bash，而 /data/service/hnp/bin/bash 在该设备上并不存在 ——
        # 硬编码任何一个绝对路径都会在另一台机器上失败，因此这里不写死。
        # userv 的 configure 是 Autoconf 2.69 生成的，它自己也会用 $CONFIG_SHELL 重新 exec。
        config_shell = ('config_shell="${CONFIG_SHELL:-${SHELL:-sh}}"; '
                        '[ -x "$config_shell" ] || config_shell=sh')
        self.run(f'{config_shell}; "$config_shell" ./configure --prefix=/')
        # R9：OHOS 上并行构建受限，固定 -j1（pcsum.h 依赖 Makefile/config.status，也不宜并行）
        self.run("make -j1")
        # 上游官方检查入口（1.2.3 只打印「There is no validation suite for this package.」，
        # 退出码 0）。保留调用是为了让 CI L1c 能看到上游入口的执行痕迹，真实断言在
        # test_package/ 中，见 notes.md「上游测试清点」。
        self.run("make check")

    def package(self):
        # INSTALL_FLAGS= 覆盖上游默认的 `-o root -g 0`（CI 非 root，chown 会失败）
        # sbindir=/bin 把 uservd 也放进 Conan 标准 bin/；etcdir=/res 把 /etc/userv
        # 配置骨架收进 res/。三者都用绝对路径，避免 DESTDIR 拼接缺斜杠。
        self.run(f'make install DESTDIR="{self.package_folder}" '
                 f'INSTALL_FLAGS= sbindir=/bin etcdir=/res')
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["res"]
