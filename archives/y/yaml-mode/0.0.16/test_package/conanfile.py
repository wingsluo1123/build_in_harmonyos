#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""yaml-mode 0.0.16 test_package —— 纯数据包,无需编译。

两级验证:

① **完整消费者用例(平台 rule12)**:`consumer_ym.py` 按 Emacs 加载 elisp 包的
   真实取数方式把交付的 yaml-mode.el 消费一遍 —— 交付路径契约
   (share/emacs/site-lisp/yaml-mode/yaml-mode.el)→ 版本头对账(Version: 0.0.16)
   → elisp 顶层结构解析(defcustom/defface/defun/defconst/defvar + 关键符号)
   → defconst 正则表提取与 elisp→python 保守转换 → 用转换成功的正则对随包
   交付的 9 个上游 YAML 测试样例逐行做语法分类(这正是 yaml-mode 每次
   buffer 变更时 font-lock 做的事情)。
   本脚本是**独立第二实现**(纯 Python,不依赖 emacs;上游 ERT 测试依赖
   emacs,CI 无 emacs)。

② **适配自检(M 条,非上游用例)**:`test_layout.py` —— 14 个交付文件逐项
   字节数、数据本体 sha256、清单 digest 对账、目录纯净、溯源齐备、
   无隐藏文件(JC5)、无构建产物(.elc 明确不交付)、无零字节文件。

上游测试状态:test/yaml-mode-test.el 含 4 个 ert-deftest,依赖 emacs 运行,
CI 无 emacs 无法执行;以 ① 的第二实现完成同一验证动作,详见 MANIFEST.yml。
"""
import os
import sys

from conan import ConanFile


class YamlModeTestConan(ConanFile):
    # 纯数据包:无编译、无 settings(载荷与架构无关)
    test_type = "explicit"
    # Windows 宿主 + OHOS 交叉 profile 会同时生成 .bat/.sh 两套 env 脚本,
    # 统一走 bash(msys2)侧,避免 self.run 在混用两套脚本时报
    # "Cannot wrap command with different envs"。Linux(CI)上无影响。
    win_bash = True

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["yaml-mode"].package_folder.replace("\\", "/")

        # ① 完整消费者用例(平台 rule12)
        consumer = os.path.join(self.source_folder, "consumer_ym.py").replace("\\", "/")
        self.run("%s %s %s" % (sys.executable.replace("\\", "/"), consumer, package_folder))

        # ② 适配自检(M 条,非上游用例)
        layout = os.path.join(self.source_folder, "test_layout.py").replace("\\", "/")
        self.run("%s %s %s" % (sys.executable.replace("\\", "/"), layout, package_folder))
