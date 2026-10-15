#!/usr/bin/env python3
"""Conan recipe — jamulus 3.9.1 (Qt5 低延迟音乐合奏服务器, HarmonyOS PC aarch64).

- 上游: https://github.com/jamulussoftware/jamulus (tag r3_9_1)
- 构建: qmake + make, CONFIG+=serveronly headless（无 GUI 服务器模式）
- 依赖: qt/5.15.19（提供 qmake 与 Qt5Network/Xml/Concurrent 模块）;
  opus 编解码为上游 vendored 源码（libs/opus），无外部依赖
- 说明:
  * serveronly 模式裁掉客户端 GUI 与音频后端（JACK/ALSA/ASIO 均不参与编译），
    QT 仅需 network/xml/concurrent，SERVER_ONLY + HEADLESS 宏走 QCoreApplication 路径
  * 制品仓 qt 包不含 lrelease 宿主工具（全缓存实测）；实测 CONFIG+=lrelease 的
    lrelease.prf 在本配置下未构成硬失败 → 最终配方零补丁（与 W3 实测形态一致），
    build() 预生成合法空 .qm（Qt5 qm 头 v3），界面回退英文（上游主语言）
  * qmake 交叉编译探测编译器走 PATH 解析、不读 CC/CXX → run 命令内联 PATH 前缀
  * make install 用 STRIP=true 覆盖 strip（HMDFS 上 strip 后 ELF 不可执行，
    acetoneiso/knowthelist 同款坑）
"""
import os
import shutil
import struct

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, get, export_conandata_patches
from conan.tools.layout import basic_layout


class JamulusConan(ConanFile):
    name = "jamulus"
    version = "3.9.1"
    description = "jamulus — Qt5 low-latency internet music ensemble server"
    license = "GPL-2.0"
    homepage = "https://jamulus.io"
    url = "https://github.com/jamulussoftware/jamulus"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt5: qmake + serveronly 所需 network/xml/concurrent 模块
        self.requires("qt/5.15.19")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _build_env(self):
        """构建环境：qmake 工具链注入（knowthelist 同模式）。

        使用 Environment().vars(self).apply() 上下文，不用 save_script("conanbuild")
        ——后者会覆盖 Conan 自身聚合 env 脚本导致自引用无限递归（qmake SIGSEGV）。
        """
        qt = self.dependencies["qt"]
        env = Environment()
        # PATH 前置 qt bin（qmake/moc/rcc）与工具链 clang 目录
        env.prepend_path("PATH", os.path.join(qt.package_folder, "bin"))
        env.prepend_path("PATH", "/data/service/hnp/bin")
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(qt.package_folder, "lib"))
        return env

    def _run_prefix(self):
        """内联 PATH 前缀（knowthelist 先例：qmake 探测编译器走 PATH 解析，
        部分 CI worker 的 Environment().vars().apply() 注入不可靠，双保险）。"""
        qt = self.dependencies["qt"]
        return "PATH=%s/bin:/data/service/hnp/bin:$PATH " % qt.package_folder

    def _generate_qm(self):
        """预生成合法空 .qm（Qt5 qm 头 v3，0 context/0 message）。

        lrelease 不可用（qt 包未随附），.qm 由本方法预生成；src/resources.qrc 通过
        <file alias> 嵌入 src/translation/*.qm —— rcc 要求文件存在。
        空翻译文件可被 QTranslator::load() 接受，界面回退英文（上游主语言）。
        """
        header = struct.pack(">IHHIII", 0x3A1C7D16, 3, 0, 0, 0, 0)
        translation_dir = os.path.join(self.source_folder, "src", "translation")
        if not os.path.isdir(translation_dir):
            return
        generated = 0
        for name in sorted(os.listdir(translation_dir)):
            if not name.endswith(".ts"):
                continue
            qm_path = os.path.join(translation_dir, name[:-3] + ".qm")
            with open(qm_path, "wb") as fh:
                fh.write(header)
            generated += 1
        self.output.info("generated %d empty .qm translation files (no lrelease in qt pkg)" % generated)

    def build(self):
        apply_conandata_patches(self)
        self._generate_qm()

        qt = self.dependencies["qt"]
        qmake = os.path.join(qt.package_folder, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise RuntimeError("qmake not found in qt package: %s" % qmake)
        src_dir = self.source_folder
        if not os.path.isfile(os.path.join(src_dir, "Jamulus.pro")):
            raise RuntimeError("Jamulus.pro not found in %s" % src_dir)

        # serveronly: 裁掉客户端 GUI/JACK；headless: QT -= gui，仅装 target
        # PREFIX=/usr: 安装到 <INSTALL_ROOT>/usr/bin，package() 再归一化
        with self._build_env().vars(self).apply():
            self.run(self._run_prefix() + 'qmake "CONFIG+=serveronly" "CONFIG+=headless" "PREFIX=/usr" Jamulus.pro',
                     cwd=src_dir)
            self.run(self._run_prefix() + "make -j1", cwd=src_dir)

    def package(self):
        src_dir = self.source_folder
        # make install INSTALL_ROOT -> package/usr/bin; STRIP=true 覆盖 strip 步骤
        # （HMDFS 上 strip 后二进制不可执行，knowthelist/acetoneiso 同款坑）
        with self._build_env().vars(self).apply():
            self.run(self._run_prefix() + 'make install INSTALL_ROOT="%s" STRIP=true' % self.package_folder,
                     cwd=src_dir)
        usr = os.path.join(self.package_folder, "usr")
        if os.path.isdir(usr):
            for sub in ("bin", "share", "lib", "etc"):
                sub_src = os.path.join(usr, sub)
                if os.path.isdir(sub_src):
                    sub_dst = os.path.join(self.package_folder, sub)
                    os.makedirs(sub_dst, exist_ok=True)
                    for entry in os.listdir(sub_src):
                        shutil.move(os.path.join(sub_src, entry), os.path.join(sub_dst, entry))
            shutil.rmtree(usr, ignore_errors=True)

        # 确保可执行位（INSTALL_ROOT 安装的二进制兜底确认）。
        # 产物名：qmake 默认 TARGET 取 .pro 文件名 → bin/Jamulus（大写）
        for binary_name in ("Jamulus", "jamulus"):
            binary = os.path.join(self.package_folder, "bin", binary_name)
            if os.path.isfile(binary):
                os.chmod(binary, 0o755)

    def package_info(self):
        # 应用包：无库文件供下游链接，仅 bin 目录
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
