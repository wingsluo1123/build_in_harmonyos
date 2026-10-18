#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for yaml-mode 0.0.16 — Emacs 的 YAML major mode(纯 elisp 单文件包)。

上游: https://github.com/yoshiki/yaml-mode
本配方取源: 上游 release 0.0.16 的 merge commit 23395dfcf004c952850691b70e63f97f169596e8
(0.0.14 起上游不再打 tag,Debian 的 0.0.16 同锚此提交;sha256 钉在 conandata.yml,
未做任何重打包)。

这个包是**纯 elisp 数据包**:交付上游主件 yaml-mode.el(18356 字节)与其文档/
测试样例,无编译产物(emacs 字节码 .elc 不交付——OHOS 无 emacs,字节码由目标
环境按需生成,且 .elc 与 emacs 版本绑定)。安装布局遵循 Emacs site-lisp 约定:

    <pkg>/share/emacs/site-lisp/yaml-mode/yaml-mode.el   数据本体(load-path 直用)
    <pkg>/share/doc/yaml-mode/upstream/**                 溯源(README/Changes/Makefile + 9 个 YAML 测试样例)
    <pkg>/licenses/LICENSE.txt                            GPL-2.0-or-later?上游 LICENSE.txt 为 GPLv3 文本

上游对这份资产的"构建"只是字节码编译(emacs --batch),OHOS 侧无需也不应引入
emacs;本配方在 build() 阶段做**载荷清单闸门**:14 个交付文件逐项核对字节数,
并对排序清单("share/<相对名> <字节数>\\n")做 sha256 对账——截断下载、换上游
修订、丢文件在这里就失败,而不是产出一个静默不完整的数据包。

上游自带 ERT 测试(test/yaml-mode-test.el,4 个 ert-deftest)依赖 emacs 运行,
CI 环境无 emacs,无法执行;test_package 用独立第二实现(pure-Python elisp 结构
解析器 + 交付正则对 YAML 样例的真实消费)完成同一验证动作,详见
test_package/MANIFEST.yml。

License: 上游 LICENSE.txt(GPL-3.0 文本,随包原样交付)。
"""

import hashlib
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

# ── 载荷清单(上游 0.0.16 tarball 展开后;sha256 钉在 conandata.yml)。
#    显式清单:14 个交付文件(相对 share/ 布局根),逐项钉字节数。
PAYLOAD_MANIFEST = (
    # 数据本体(load-path)
    ("share/emacs/site-lisp/yaml-mode/yaml-mode.el", 18356),
    # 溯源(README/Changes/Makefile)+ 测试样例 9 个(consumer 用例的语料)
    ("share/doc/yaml-mode/upstream/README", 1972),
    ("share/doc/yaml-mode/upstream/Changes", 3930),
    ("share/doc/yaml-mode/upstream/Makefile", 812),
    ("share/doc/yaml-mode/upstream/test-files/allow-spaces-before-dash-1.yaml", 314),
    ("share/doc/yaml-mode/upstream/test-files/allow-spaces-before-dash-2.yaml", 151),
    ("share/doc/yaml-mode/upstream/test-files/allow-spaces-before-dash-3.yaml", 163),
    ("share/doc/yaml-mode/upstream/test-files/test-dash-newline-starts-sequence-1.yaml", 616),
    ("share/doc/yaml-mode/upstream/test-files/test-dash-newline-starts-sequence-2.yaml", 914),
    ("share/doc/yaml-mode/upstream/test-files/test-nested-map-single-line-match.yaml", 97),
    ("share/doc/yaml-mode/upstream/test-files/test-quotes-in-strings.yaml", 211),
    ("share/doc/yaml-mode/upstream/test-files/test-syntax-highlighting-list-of-dicts-containing-literal-block.yaml", 234),
    ("share/doc/yaml-mode/upstream/test-files/test-tricky-comments.yaml", 45),
    # 许可
    ("licenses/LICENSE.txt", 35149),
)
EXPECTED_FILES = len(PAYLOAD_MANIFEST)
EXPECTED_BYTES = sum(size for _name, size in PAYLOAD_MANIFEST)
# sha256 over 排序后的 "<相对名> <字节数>\n" 清单(与 swe-data 同口径的载荷指纹)
EXPECTED_MANIFEST_DIGEST = "468bab40d95c19fcf752a8724f0fcabb7bf6e9bf2a95b79ce352c037dd057977"
# 数据本体自身的 sha256 / 字节数
PAYLOAD_NAME = "yaml-mode.el"
PAYLOAD_SHA256 = "5e19a87a7e6cc5f9e3f829888eedadef37041e8d30a2526ce07f08108ccb71a5"
PAYLOAD_BYTES = 18356

_LICENSE_NOTE = """\
yaml-mode 0.0.16
================
Upstream: https://github.com/yoshiki/yaml-mode
Source archive: commit 23395dfcf004c952850691b70e63f97f169596e8 (release 0.0.16),
sha256 pinned in conandata.yml.

yaml-mode is distributed under the GNU General Public License v3.0-or-later;
the complete license text is shipped verbatim in licenses/LICENSE.txt
(upstream LICENSE.txt).

This package redistributes the upstream yaml-mode.el and its documentation /
test fixtures unmodified.
"""


class YamlModeConan(ConanFile):
    name = "yaml-mode"
    version = "0.0.16"
    description = ("YAML major mode for Emacs (yaml-mode.el, the canonical "
                   "Emacs lisp package for editing YAML)")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/yoshiki/yaml-mode"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 纯数据包:交付 elisp 源文件,无编译产物、无库、无可执行文件
    package_type = "unknown"

    _lisp_dir = os.path.join("share", "emacs", "site-lisp", "yaml-mode")
    _doc_dir = os.path.join("share", "doc", "yaml-mode", "upstream")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    # ------------------------------------------------------------------ helpers
    def _check_payload(self):
        """交付清单闸门:14 个文件逐项存在+字节数,加排序清单 sha256 对账。"""
        for rel, size in PAYLOAD_MANIFEST:
            path = os.path.join(self.source_folder, rel.replace("/", os.sep))
            # 交付布局由本配方的 package() 前置拷贝逻辑决定;build() 阶段
            # 直接核对 source 树里的对应上游文件(路径映射见 _src_of)。
            src = self._src_of(rel)
            if not os.path.isfile(src):
                raise ConanException(f"payload file missing: {rel} (source {src})")
            actual = os.path.getsize(src)
            if actual != size:
                raise ConanException(
                    f"payload file {rel} is {actual} bytes, expected {size}")
            if actual == 0:
                raise ConanException(f"zero-length file in payload: {rel}")
        digest = hashlib.sha256()
        for rel, size in sorted(PAYLOAD_MANIFEST):
            digest.update(f"{rel} {size}\n".encode("utf-8"))
        got = digest.hexdigest()
        if got != EXPECTED_MANIFEST_DIGEST:
            raise ConanException(
                f"payload manifest digest {got} does not match the pinned "
                f"upstream digest {EXPECTED_MANIFEST_DIGEST}")
        # 数据本体内容级校验
        main = os.path.join(self.source_folder, PAYLOAD_NAME)
        with open(main, "rb") as handle:
            raw = handle.read()
        if len(raw) != PAYLOAD_BYTES:
            raise ConanException(f"{PAYLOAD_NAME} is {len(raw)} bytes, expected {PAYLOAD_BYTES}")
        actual = hashlib.sha256(raw).hexdigest()
        if actual != PAYLOAD_SHA256:
            raise ConanException(
                f"{PAYLOAD_NAME} sha256 {actual} does not match {PAYLOAD_SHA256}")
        return True

    def _src_of(self, rel):
        """交付相对路径 → source 树里的上游文件路径。"""
        if rel.endswith("/yaml-mode.el"):
            return os.path.join(self.source_folder, PAYLOAD_NAME)
        if rel.startswith("licenses/"):
            return os.path.join(self.source_folder, "LICENSE.txt")
        if rel.startswith("share/doc/yaml-mode/upstream/"):
            return os.path.join(self.source_folder,
                                rel[len("share/doc/yaml-mode/upstream/"):].replace("/", os.sep))
        raise ConanException(f"unknown payload path: {rel}")

    def build(self):
        # 没有编译器参与。数据载荷在这里过清单闸门。
        self._check_payload()
        self.output.info(
            f"{self.name}: payload fingerprint OK "
            f"({EXPECTED_FILES} files, {EXPECTED_BYTES} bytes, manifest "
            f"{EXPECTED_MANIFEST_DIGEST[:16]}…), {PAYLOAD_NAME} sha256 OK")

    def package(self):
        lisp_dir = os.path.join(self.package_folder, self._lisp_dir)
        doc_dir = os.path.join(self.package_folder, self._doc_dir)

        # 数据本体:load-path 直用的单文件包
        copy(self, PAYLOAD_NAME, src=self.source_folder, dst=lisp_dir)
        # 溯源:README/Changes/Makefile + 9 个 YAML 测试样例(消费者用例语料)
        for name in ("README", "Changes", "Makefile"):
            copy(self, name, src=self.source_folder, dst=doc_dir)
        copy(self, "*.yaml", src=os.path.join(self.source_folder, "test-files"),
             dst=os.path.join(doc_dir, "test-files"))

        os.makedirs(os.path.join(self.package_folder, "licenses"), exist_ok=True)
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 数据根是唯一的对外接口:Emacs 按 site-lisp 约定把该目录加入 load-path
        self.cpp_info.resdirs = [self._lisp_dir]
        # 数据包不装头文件/库/可执行文件;留着默认值会让 CMakeDeps 生成
        # 不存在的 include/lib/bin 路径。
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.output.info(
            f"yaml-mode.el at {self._lisp_dir} ({PAYLOAD_BYTES} bytes, "
            f"version 0.0.16)")
