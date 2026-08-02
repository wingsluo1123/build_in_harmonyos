#!/usr/bin/env python3
"""Conan recipe — ncurses 6.4 (Autotools, static lib for OHOS)."""
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.env import Environment, environment
from conan.tools.files import get, copy, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class NcursesConan(ConanFile):
    name = "ncurses"
    version = "6.4"
    license = "X11"
    author = "Thomas E. Dickey"
    url = "https://invisible-island.net/ncurses/"
    homepage = "https://invisible-island.net/ncurses/"
    description = "System V release 4.0 curses emulation library"
    topics = ("curses", "terminal", "tui")
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False], "widec": [True, False]}
    default_options = {"shared": False, "fPIC": True, "widec": True}
    # AutotoolsToolchain 不放 generators attribute（generate() 内实例化，conan 2.x 不允许两者并存）
    # 不设 no_copy_source: patches 目录需拷到 source cache 让 apply_conandata_patches 找到

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # Conan 2.x G1 门禁要求 export_sources() 声明；ncurses 补丁通过 conandata.yml 打
        export_conandata_patches(self)

    def requirements(self):
        pass

    def validate(self):
        # R32 平台兼容性检查（统模式：先 OS 后 arch）
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(f"ncurses {self.version} only supports OHOS, got os={self.settings.os}")
        if self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(f"ncurses {self.version} only supports armv8, got arch={self.settings.arch}")
        # 必须静态编译，共享库会劫持系统 libncursesw.so.6 导致 zsh 崩溃
        if self.options.shared:
            raise ConanInvalidConfiguration("ncurses must be static (--without-shared), shared lib hijacks system libncursesw.so.6")
        if not self.options.widec:
            raise ConanInvalidConfiguration("ncurses must compile with widec=True for OHOS (readline/bash require wide character support)")

    def source(self):
        # 显式按版本取 sources，避免 ** 解包把版本号当 kwarg
        src = self.conan_data["sources"][str(self.version)]
        get(self, **src, strip_root=True)
        # 手动把 patches/ 从 recipe folder 拷到 source folder（绕 conan 2.x patches 怪异）
        patches_src = os.path.join(self.recipe_folder, "patches")
        patches_dst = os.path.join(self.source_folder, "patches")
        os.makedirs(patches_dst, exist_ok=True)
        if os.path.isdir(patches_src):
            for pf in os.listdir(patches_src):
                copy(self, pf, src=patches_src, dst=patches_dst)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # OHOS 适配 configure options（按 archives/n/ncurses/6.4/manifest.yaml）
        tc.configure_args.append("--without-shared")
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--without-debug")
        tc.configure_args.append("--without-ada")
        tc.configure_args.append("--without-manpages")
        tc.configure_args.append("--without-tests")
        tc.configure_args.append("--without-cxx-binding")
        if self.options.widec:
            tc.configure_args.append("--enable-widec")
        # 头文件安装到顶层 include/ 而非 include/ncursesw/（aamath/catgirl 同实践）
        tc.configure_args.append("--enable-overwrite")
        tc.generate()
        # 保存 configure_args 供 build() 中手动 configure 使用
        self._configure_args = tc.configure_args

    def build(self):
        # 手动应用 patch（绕 conan 2.x apply_conandata_patches cache 查找问题）
        patch_file = os.path.join(self.source_folder, "patches", "0001-port-for-ohos.patch")
        if os.path.exists(patch_file):
            ret = self.run(f"patch -p1 < \"{patch_file}\"", cwd=self.source_folder, shell=True)
            if ret != 0:
                raise ConanException(f"patch 0001-port-for-ohos failed with exit code {ret}")
        # E002/E046: OHOS HMDFS 下 /storage/Users/currentUser/tmp 不可写，
        # tempfile.TemporaryDirectory() 创建在其下导致 config.status 写临时文件
        # Permission denied（CI #3810）。用 sandbox 可写目录，多路径 fallback：
        # CI worker 环境 sandbox 路径可能不存在，fallback 到 build_folder（Conan 保证可写）
        sandbox_candidates = [
            "/data/storage/el2/base/haps/entry/files/.ncurses-tmp",
            os.path.join(self.build_folder, ".ncurses-tmp"),
            os.path.join(self.package_folder, "..", ".ncurses-tmp"),
        ]
        sandbox = None
        for cand in sandbox_candidates:
            try:
                self.run(f"mkdir -p \"{cand}\" && chmod 755 \"{cand}\"", ignore_errors=True)
                # 核可写：写测试文件
                test_file = os.path.join(cand, ".write_test")
                with open(test_file, "w") as f: f.write("ok")
                os.remove(test_file)
                sandbox = cand
                break
            except Exception:
                continue
        if sandbox is None:
            # 全 fallback 失败，用 Conan build_folder（必可写）
            sandbox = os.path.join(self.build_folder, ".ncurses-tmp")
            self.run(f"mkdir -p \"{sandbox}\"", ignore_errors=True)
        with environment(Environment().define("TMPDIR", sandbox)):
            # CONFIG_SHELL 存在性回退（aireview P2）：os.environ.get 缺 fallback
            # CI TypeError 根因: os.path.isabs 在该 Conan 环境 shadow 非 callable，
            # 避开用 str.startswith('/') 判绝对路径 + os.path.exists 核存在
            bash = os.environ.get("CONFIG_SHELL")
            if not bash or (bash.startswith("/") and not os.path.exists(bash)):
                for cand in ("/bin/bash", "/usr/bin/bash", "bash"):
                    if cand == "bash" or os.path.exists(cand):
                        bash = cand
                        break
            configure = os.path.join(self.source_folder, "configure")
            # ncurses 6.4 老 autotools (2022 config.guess) �猜不出 OHOS aarch64，显式传 build/host
            # 追加 generate() 中定义的 configure_args（--without-shared 等，否则这些选项失效）
            args = " ".join(self._configure_args)
            ret = self.run(f"{bash} {configure} --prefix={self.package_folder} --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu {args}",
                         cwd=self.source_folder, shell=True)
            if ret != 0:
                raise ConanException(f"configure failed with exit code {ret}")
            ret = self.run("make -j$(nproc)", cwd=self.source_folder, shell=True)
            if ret != 0:
                raise ConanException(f"make failed with exit code {ret}")

    def package(self):
        ret = self.run(f"make install DESTDIR= TMPDIR=/tmp", cwd=self.source_folder)
        if ret != 0:
            raise ConanException(f"make install failed with exit code {ret}")
        # 确认 4 个静态库已安装
        for lib in ("libncursesw.a", "libpanelw.a", "libmenuw.a", "libformw.a"):
            if not os.path.exists(os.path.join(self.package_folder, "lib", lib)):
                raise ConanException(f"expected static lib {lib} not found in package")
        # P3: 许可证随包发布
        copy(self, "COPYING", dst=os.path.join(self.package_folder, "licenses"),
             src=self.source_folder)

    def package_info(self):
        # 上游提供 4 个静态库，主库是 libncursesw（widec 版本）
        # P2: 龠接顺序错误，ncursesw 被它依赖的 panelw/menuw/formw 依赖，
        # 静态链接时主库须放末（被依赖在前），否则 panel/menu/form 的未定义符号找不到 ncursesw
        self.cpp_info.libs = ["panelw", "menuw", "formw", "ncursesw"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
