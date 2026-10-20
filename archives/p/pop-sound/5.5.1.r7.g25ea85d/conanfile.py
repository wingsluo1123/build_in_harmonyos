#!/usr/bin/env python3
"""Conan recipe for pop-sound 5.5.1.r7.g25ea85d — Pop 声音主题（纯数据资源包）。

上游: https://github.com/pop-os/gtk-theme （sounds/ 子目录）
版本串: `git describe --long --tags --abbrev=7` = v5.5.1-7-g25ea85d
         → 提交 25ea85d97126992024b03bfb4e4c3b0711c749ed

上游 meson（sounds/meson.build，12 行）只做两件事，没有任何编译、没有编译器、
没有 dependency()：

    configure_file(input: 'src/index.theme.in', output: 'index.theme',
                   configuration: {ThemeName: 'Pop'},
                   install_dir: '<prefix>/share/sounds/Pop')
    install_subdir('src/stereo', install_dir: '<prefix>/share/sounds/Pop')

本配方等价复刻这两步：`build()` 里做 configure_file 的模板替换并逐条自检，
`package()` 交付 `share/sounds/Pop/{index.theme,stereo/**}`。不依赖 meson/ninja
（CI 环境无 meson），等价性由 notes.md 记录的 meson 实跑对比（逐字节一致）背书。

License: GPL-3.0-or-later（音效本体按上游 COPYING；主题元数据按 LICENSE_CCBYSA）
"""

import os
import tarfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, download, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout

# 上游 sounds/src/stereo/{alert,action,notification}/ 下的音效条目：
# 21 个实体 .oga + 4 个同目录相对符号链接（README.md 的 "alias > entity" 记法）。
# 符号链接在 OHOS 上可正常创建（名字互不为大小写变体，不存在 pop-icon 的自指问题）。
ALIASES = {
    "action/screen-capture.oga": "camera-shutter.oga",
    "notification/message-new-email.oga": "message.oga",
    "notification/power-unplug.oga": "power-plug.oga",
    "notification/theme-demo.oga": "system-ready.oga",
}
CONTEXTS = ("alert", "action", "notification")
OGG_MAGIC = b"OggS"


class PopSoundConan(ConanFile):
    name = "pop-sound"
    version = "5.5.1.r7.g25ea85d"
    description = ("Pop sound theme — freedesktop sound theme for Pop!_OS / GNOME "
                   "(21 events + 4 aliases, Ogg Vorbis)")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/pop-os/gtk-theme"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 纯数据包：无 settings、无编译器、产物与架构无关（与 pop-icon / papirus-icon 同形态）。
    package_type = "unknown"

    no_copy_source = True

    _theme = "Pop"
    _theme_subdir = os.path.join("share", "sounds", "Pop")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        src = self.conan_data["sources"][self.version]
        archive = os.path.join(self.source_folder, "gtk-theme.tar.gz")
        download(self, src["url"], archive, sha256=src["sha256"])

        extract_to = os.path.join(self.source_folder, "_extract")
        os.makedirs(extract_to, exist_ok=True)
        with tarfile.open(archive, "r:gz") as tf:
            members = tf.getmembers()
            for m in members:
                # 手工剥离顶层目录（gtk-theme-<sha>/），等价 strip_root=True
                if "/" in m.name:
                    m.name = m.path = m.name.split("/", 1)[1]
                else:
                    m.name = m.path = ""
            tf.extractall(extract_to, members=[m for m in members if m.name], filter="data")

        for entry in os.listdir(extract_to):
            os.replace(os.path.join(extract_to, entry), os.path.join(self.source_folder, entry))
        os.remove(archive)
        os.rmdir(extract_to)

        apply_conandata_patches(self)

    def build(self):
        # ① configure_file 等价：index.theme.in → index.theme（@ThemeName@ → Pop）
        template = os.path.join(self.source_folder, "sounds", "src", "index.theme.in")
        if not os.path.isfile(template):
            raise ConanException("upstream sounds/src/index.theme.in missing")
        with open(template, encoding="utf-8") as fh:
            rendered = fh.read().replace("@ThemeName@", self._theme)
        index_theme = os.path.join(self.build_folder, "index.theme")
        with open(index_theme, "w", encoding="utf-8") as fh:
            fh.write(rendered)

        # ② install_subdir 等价：音效本体逐条自检（缺文件比构建失败更隐蔽：
        #    装出来的主题会静默丢事件）
        stereo = os.path.join(self.source_folder, "sounds", "src", "stereo")
        if not os.path.isdir(stereo):
            raise ConanException("upstream sounds/src/stereo missing")

        entities = 0
        for ctx in CONTEXTS:
            ctx_dir = os.path.join(stereo, ctx)
            if not os.path.isdir(ctx_dir):
                raise ConanException(f"upstream context directory missing: {ctx}")
            for name in sorted(os.listdir(ctx_dir)):
                if not name.endswith(".oga"):
                    raise ConanException(f"unexpected non-.oga entry: {ctx}/{name}")
                rel = f"{ctx}/{name}"
                path = os.path.join(ctx_dir, name)
                if os.path.islink(path):
                    if rel not in ALIASES:
                        raise ConanException(f"unexpected symlink: {rel}")
                    if os.readlink(path) != ALIASES[rel]:
                        raise ConanException(f"alias target changed: {rel} -> {os.readlink(path)}")
                    continue
                with open(path, "rb") as fh:
                    head = fh.read(4)
                if head != OGG_MAGIC:
                    raise ConanException(f"not an Ogg container: {rel} (magic={head!r})")
                entities += 1

        if entities != 21:
            raise ConanException(f"expected 21 entity .oga files, got {entities}")
        self.output.info(f"pop-sound: 21 entities + {len(ALIASES)} aliases verified, "
                         f"index.theme rendered ({len(rendered)} B)")

    def package(self):
        theme_dir = os.path.join(self.package_folder, self._theme_subdir)
        copy(self, "*", src=os.path.join(self.source_folder, "sounds", "src", "stereo"),
             dst=os.path.join(theme_dir, "stereo"))
        copy(self, "index.theme", src=self.build_folder, dst=theme_dir)

        # 上游 `install_subdir` 默认 follow_symlinks=True：4 个别名在安装结果里是实体
        # 文件（meson 实测 stage 下 26 个普通文件、0 个链接）。这里保持一致，
        # 同时避免目标文件系统（OHOS /storage 等）对符号链接支持差异导致别名丢失。
        for rel, target in ALIASES.items():
            alias_path = os.path.join(theme_dir, "stereo", rel)
            if os.path.islink(alias_path):
                with open(os.path.join(os.path.dirname(alias_path), target), "rb") as fh:
                    data = fh.read()
                os.unlink(alias_path)
                with open(alias_path, "wb") as fh:
                    fh.write(data)

        lic_dir = os.path.join(self.package_folder, "licenses")
        for name in ("COPYING", "LICENSE_CCBYSA"):
            copy(self, name, src=self.source_folder, dst=lic_dir)

    def package_info(self):
        # 纯数据资源包：无库、无头文件、无可执行文件（不创建 commands.json）。
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = [self._theme_subdir]

        theme_dir = os.path.join(self.package_folder, self._theme_subdir)
        self.buildenv_info.define("POP_SOUND_THEME_DIR", theme_dir)
        self.runenv_info.define("POP_SOUND_THEME_DIR", theme_dir)

        # 与 pop-icon 一致：把 share/ 前置进 XDG_DATA_DIRS，freedesktop 声音主题
        # 查找（<datadir>/sounds/<theme>）才能发现本主题。
        share_dir = os.path.join(self.package_folder, "share")
        existing = os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share")
        self.buildenv_info.define("XDG_DATA_DIRS", f"{share_dir}:{existing}")
        self.runenv_info.define("XDG_DATA_DIRS", f"{share_dir}:{existing}")
        self.output.info(f"POP_SOUND_THEME_DIR={theme_dir}")
