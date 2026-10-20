from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os
import shutil
import subprocess


class LibBasicobjectsConan(ConanFile):
    name = "libbasicobjects"
    version = "0.2.0"
    description = (
        "Basic data objects library from the SSSD ding-libs collection: "
        "a growable byte buffer (simplebuffer) used for serialized IO"
    )
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/SSSD/ding-libs"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libbasicobjects is supported only on Linux/OHOS")

    def layout(self):
        basic_layout(self)

    def source(self):
        # conandata sources 为有序候选组列表(每组 url+sha256 自洽):
        # 组1 = GitHub 官方发行包(带预生成 configure/aclocal.m4/Makefile.in,
        # 不依赖构建机 autotools);组2 = codeload tag archive(打包字节流不同,
        # 无预生成 configure,由 build() 的 autoreconf 兜底)。逐组尝试,任一
        # 组下载+校验成功即用,全部失败再抛错。
        last_error = None
        for sources in self.conan_data["sources"]:
            try:
                get(self, **sources, strip_root=True)
                return
            except Exception as e:
                last_error = e
                self.output.warning(f"source URL 组失败,尝试下一组: {e}")
        raise ConanException(f"所有源 URL 均失败: {last_error}")

    def _platform_configure_args(self):
        args = [
            # OHOS musl 无 GNU gettext 实现(path_utils.h 无条件引用 libintl
            # 声明);本库 API 纯 ASCII,关闭 NLS(知识库桶4 rec)。
            "--disable-nls",
            # 预生成 configure 的 depfiles 引导在受限执行环境(HMDFS/沙箱)
            # 下不可靠,依赖跟踪对本单一 C 文件库无收益。
            "--disable-dependency-tracking",
        ]
        if str(self.settings.os) == "OHOS":
            # 上游 bundled config.guess(2018)不识别 HarmonyOS 内核三元组,
            # 显式指定 Linux 三元组(config.sub 已原生支持 aarch64)。
            args += [
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ]
        return args

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._platform_configure_args())
        tc.generate()

    @property
    def _make_args_str(self):
        # OHOS 真机/受限沙箱:make recipe 默认 SHELL=/bin/sh 及 MKDIR_P=
        # install-sh 直接 execve 会被拒(Permission denied / 退出码 126),
        # 统一改用 PATH 内解析出的绝对路径。标准 CI Worker 上等价无害。
        # 并行度限 2:autotools 单编译任务经 make→bash→libtool→clang 多层
        # 进程链,深调用栈(如 ohc conan-verify)下 -j8 会触发沙箱进程配额,
        # clang 被静默终止(make 只见 Error 1)。
        args = ["-j2"]
        bash = shutil.which("bash")
        if bash:
            args.append(f"SHELL={bash}")
        mkdir = shutil.which("mkdir")
        if mkdir:
            args.append(f"MKDIR_P={mkdir} -p")
        return " ".join(f'"{a}"' for a in args)

    def _ensure_configure(self):
        if os.path.isfile(os.path.join(self.source_folder, "configure")):
            return
        # codeload tag archive 组无预生成 configure:用构建机 autotools 现场生成
        autoreconf = shutil.which("autoreconf")
        if not autoreconf:
            raise ConanException(
                "源码无预生成 configure 且构建机缺少 autoreconf(需 autoconf+automake+libtool)"
            )
        self.output.info("无预生成 configure,执行 autoreconf -fiv ...")
        subprocess.run([autoreconf, "-fiv"], cwd=self.source_folder, check=True)

    def _configure_shell(self):
        # OHOS 真机/HMDFS:直接 execve shebang 脚本被拒(Permission denied,
        # 退出码 126),configure 必须经解释器显式执行;优先 profile 的
        # CONFIG_SHELL,次选 PATH 解析的 bash。
        shell = os.environ.get("CONFIG_SHELL") or shutil.which("bash")
        if not shell:
            raise ConanException("找不到可用 shell 执行 configure")
        return shell

    def _run_with_retry(self, description, cmd):
        """受限真机沙箱下 configure/make 偶发 'Interrupted system call'
        (EINTR,与 /bin/sh 间歇 Permission denied / posix_spawn EAGAIN 同族,
        见 fdk-aac 任务实测):确定性重试,最多 3 次。"""
        last_error = None
        for attempt in range(1, 4):
            try:
                self.run(cmd, env="conanbuild")
                return
            except ConanException as e:
                last_error = e
                self.output.warning(f"{description} 第 {attempt} 次失败,重试: {e}")
        raise last_error

    @property
    def _stage_prefix(self):
        """configure 的 --prefix 指向构建树内 stage 目录。

        conan 的 AutotoolsToolchain 在 build 阶段取不到 package_folder,
        默认 --prefix=/ 会让 libtool 给 UT 嵌入 RUNPATH=//lib(无效)。
        stage 目录让 shared 变体的 simplebuffer_ut 拿到可用 RUNPATH
        (stage/lib),部署 .so 后 UT 即可加载同批构建的库。
        """
        return os.path.join(self.build_folder, "stage")

    def _stage_libs(self):
        """把构建产物 .so 复制到 stage/lib(供 UT 的 RUNPATH 加载)。"""
        stage_lib = os.path.join(self._stage_prefix, "lib")
        os.makedirs(stage_lib, exist_ok=True)
        libs_src = os.path.join(self.build_folder, ".libs")
        for name in os.listdir(libs_src):
            if ".so" in name:
                shutil.copy2(os.path.join(libs_src, name), stage_lib)

    def _run_configure(self):
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure):
            raise ConanException(f"configure 不存在: {configure}")
        shell = self._configure_shell()
        # conan 的 Autotools.configure() 直接 execve configure 脚本,在
        # OHOS 真机/HMDFS 上被拒(shebang execve 限制);此处改为经显式
        # shell 在 build 目录(VPATH 外置构建)执行,并沿用
        # AutotoolsToolchain 的标准参数集(bindir 等 ${prefix} 派生参数 +
        # 平台参数),--prefix 重写为 stage 目录。经显式 shell 运行的
        # configure 会把该 shell 写入 Makefile 的 SHELL(@SHELL@ =
        # CONFIG_SHELL),make recipe 因此天然绕开 /bin/sh。
        # 参数用单引号包裹,防 ${prefix} 被 shell 展开。
        tc = AutotoolsToolchain(self)
        args = []
        for a in tc.configure_args:
            if a.startswith("--prefix="):
                args.append(f"--prefix={self._stage_prefix}")
            else:
                args.append(a)
        args += self._platform_configure_args()
        quoted = " ".join(f"'{a}'" for a in args)
        self._run_with_retry(
            "configure",
            f'cd "{self.build_folder}" && "{shell}" "{configure}" {quoted}',
        )

    def _deploy_package_layout(self):
        """把构建树产物部署到 conan 包布局。

        不走 `make install`:ding-libs 是伞形构建,install 目标会尝试安装全部
        子库(libpath_utils/libdhash/...),而本配方仅交付 libbasicobjects。
        shared 变体下 simplebuffer_ut 的 libtool RUNPATH 即指向 package/lib,
        先部署后测试使上游 UT 可直接执行。
        """
        libs_src = os.path.join(self.build_folder, ".libs")
        if not os.path.isdir(libs_src):
            raise ConanException(f"构建产物目录不存在: {libs_src}")

        copy(self, "*.so*", libs_src, os.path.join(self.package_folder, "lib"))
        copy(self, "*.a", libs_src, os.path.join(self.package_folder, "lib"))
        copy(
            self,
            "simplebuffer.h",
            os.path.join(self.source_folder, "basicobjects"),
            os.path.join(self.package_folder, "include"),
        )
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))

        # configure 生成的 basicobjects.pc:prefix 重写为相对 pkgconfig 目录,
        # 与包内实际布局(lib/include)一致,避免宿主机路径泄漏。
        pc_src = os.path.join(self.build_folder, "basicobjects", "basicobjects.pc")
        if not os.path.isfile(pc_src):
            raise ConanException(f"pkg-config 元数据未生成: {pc_src}")
        with open(pc_src, "r", encoding="utf-8") as f:
            pc = f.read()
        lines = []
        for line in pc.splitlines():
            if line.startswith("prefix="):
                lines.append("prefix=${pcfiledir}/../..")
            else:
                lines.append(line)
        save(self, os.path.join(self.package_folder, "lib", "pkgconfig", "basicobjects.pc"), "\n".join(lines) + "\n")

    def _fix_maintainer_timestamps(self):
        """回拨 autotools 输入文件时间戳。

        0001 patch 会更新 version.m4 的 mtime(变新),使其晚于发行包内
        预生成的 aclocal.m4/configure(2022) → make 触发 automake
        maintainer 重建规则,调用缺失的 aclocal-1.16 → Error 127。
        把 m4 输入(configure.ac/version.m4/m4/*.m4)统一回拨到发行期之前,
        预生成文件重新成为最新,重建规则不再触发。
        """
        old = 1000000000  # 2001-09,早于一切发行文件
        candidates = [os.path.join(self.source_folder, "configure.ac"),
                      os.path.join(self.source_folder, "version.m4")]
        m4_dir = os.path.join(self.source_folder, "m4")
        if os.path.isdir(m4_dir):
            candidates += [os.path.join(m4_dir, f) for f in os.listdir(m4_dir)]
        for path in candidates:
            if os.path.isfile(path):
                os.utime(path, (old, old))

    def build(self):
        apply_conandata_patches(self)
        self._fix_maintainer_timestamps()
        self._ensure_configure()
        self._run_configure()
        # 目标级构建:仅编译 libbasicobjects.la 及上游单测 simplebuffer_ut
        # (simplebuffer_ut 依赖 libbasicobjects.la,自动连带构建)。全量
        # `make all` 会编译 ding-libs 全部子库,其中 libpath_utils 引用的
        # GNU gettext 在 OHOS musl 上不可用(见 _platform_configure_args
        # 注释)。make 经 make 变量注入绝对路径 SHELL/MKDIR_P,规避受限
        # 环境对 /bin/sh 与 install-sh(shebang 脚本)的 execve 拒绝。
        self._run_with_retry(
            "make(simplebuffer_ut)",
            f'cd "{self.build_folder}" && make {self._make_args_str} simplebuffer_ut',
        )

        # shared 变体:UT 的 RUNPATH=stage/lib,先部署 .so 再执行
        self._stage_libs()

        self._deploy_package_layout()

        # CI L1 门禁:build() 内执行上游官方测试套件。simplebuffer_ut 为
        # 上游 TESTS 注册的官方单测(automake `make check` 的 basicobjects
        # 条目):alloc→add_raw/add_cr/add_str→get_len/get_buf→write→free
        # 全路径断言,退出码非 0 即失败。直接执行 .libs 下的真 ELF,绕开
        # libtool /bin/sh wrapper(受限环境 execve 拒绝 shebang 脚本)。
        ut = os.path.join(self.build_folder, ".libs", "simplebuffer_ut")
        if not os.path.isfile(ut):
            ut = os.path.join(self.build_folder, "simplebuffer_ut")
        if not os.path.isfile(ut):
            raise ConanException("上游官方单测 simplebuffer_ut 未构建")
        self.output.info("执行上游官方单测 simplebuffer_ut ...")
        self.run(f'"{ut}" -v', env="conanbuild")

    def package(self):
        self._deploy_package_layout()

    def package_info(self):
        self.cpp_info.libs = ["basicobjects"]
        self.cpp_info.set_property("pkg_config_name", "basicobjects")
