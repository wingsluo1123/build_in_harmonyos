#!/usr/bin/env python3
"""Conan recipe for debian-cloud-images 0.0.9 — Debian 云镜像「所需软件包」清单载体。

上游: https://tracker.debian.org/pkg/debian-cloud-images
      （Debian native 源包，源格式 `3.0 (native)`；二进制产物为**空元包**
       `debian-cloud-images-packages`，其 Depends 由打包期生成）
源码分发: Debian 归档 pool/main/d/debian-cloud-images/debian-cloud-images_0.0.9.tar.xz
      （本配方走清华 TUNA 镜像同一份文件，sha256 与官方 .dsc 的
       Checksums-Sha256 一致：48731025b5ed07bb04ed6313a96073854305f2fb7207a401e146915ef889dcf2）

源包只含 `package/debian/`，共 8 个文件 —— 没有任何编译型源码，交付三部分：

    debian/source.substvars        上游随源包发布的**已生成**依赖清单（本包数据本体，
                                   `debian-cloud-images-packages:Depends=` 字段，
                                   列出云镜像需要安装的全部软件包，含 [arch] 限定）
    debian/bin/make-substvars      清单生成器（Python3，仅用标准库 pathlib/sys）
    debian/{control,rules,changelog,copyright,source/format,source/lintian-overrides}
                                   打包元数据（可追溯来源与许可）

**纯数据包，无编译步骤**。生成器 make-substvars 需要 `../config_space/sid/package_config`
（该目录不属于源包组成），故本包直接交付上游已发布的那份清单；build() 只做本体自检
（清单载体与生成器必须在，且清单必须可解析出非空条目）。

License: GPL-2-or-later（见 debian/copyright）
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class DebianCloudImagesConan(ConanFile):
    name = "debian-cloud-images"
    version = "0.0.9"
    description = "Authoritative list of packages the Debian cloud images need"
    license = "GPL-2.0-or-later"
    homepage = "https://tracker.debian.org/pkg/debian-cloud-images"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 纯数据包：无编译、产物与架构无关；settings 保留四项仅用于交叉编译矩阵一致性。
    package_type = "unknown"
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    _SUBSTVARS_REL = os.path.join("debian", "source.substvars")
    _GENERATOR_REL = os.path.join("debian", "bin", "make-substvars")
    _FIELD = "debian-cloud-images-packages:Depends"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # 没有编译器参与；这里只做本体自检：清单载体与生成器必须都在，且清单必须
        # 能解析出至少一个包条目 —— 否则交付的是残包（R34：不得伪造编译产物）。
        substvars = os.path.join(self.source_folder, self._SUBSTVARS_REL)
        generator = os.path.join(self.source_folder, self._GENERATOR_REL)
        if not os.path.isfile(substvars):
            raise ConanException(f"{self._SUBSTVARS_REL} missing from upstream")
        if not os.path.isfile(generator):
            raise ConanException(f"{self._GENERATOR_REL} missing from upstream")

        entries = self._parse_depends(substvars)
        if not entries:
            raise ConanException(f"{self._FIELD} resolved to an empty package list")
        self.output.info(
            f"{self.name}: {len(entries)} package entries in {self._FIELD}")

    @staticmethod
    def _parse_depends(substvars_path):
        """从 substvars 文本中取出 `debian-cloud-images-packages:Depends=` 的条目列表。"""
        value = None
        with open(substvars_path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if line.startswith("debian-cloud-images-packages:Depends="):
                    value = line.split("=", 1)[1].strip()
                    break
        if value is None:
            raise ConanException("debian-cloud-images-packages:Depends= not found")
        return [item.strip() for item in value.split(",") if item.strip()]

    def package(self):
        debian_src = os.path.join(self.source_folder, "debian")
        # 逐字保留上游 debian/ 打包树（含已生成的 source.substvars 与生成器脚本），
        # 让消费方既能直接用成品清单、也能拿到可追溯的生成来源。
        copy(self, "*", src=debian_src,
             dst=os.path.join(self.package_folder, "share", self.name, "debian"))
        copy(self, "copyright", src=debian_src,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        substvars = os.path.join(self.package_folder, "share", self.name,
                                 self._SUBSTVARS_REL)
        self.buildenv_info.define("DEBIAN_CLOUD_IMAGES_SUBSTVARS", substvars)
        self.runenv_info.define("DEBIAN_CLOUD_IMAGES_SUBSTVARS", substvars)
        self.output.info(f"DEBIAN_CLOUD_IMAGES_SUBSTVARS={substvars}")
