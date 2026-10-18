#!/usr/bin/env python3
"""Conan test_package — wmjupiter 1.21.

wmjupiter 是 X11 dockapp（application 包，无库可链接），R34 要求测试**真实执行
被测二进制**。上游没有测试套件（tag 归档仅 9 个条目、Makefile 只有 all/install
两个目标），故在 test_wmjupiter.sh 中自行构造 A/B 两类共 24 条断言：

  A 类（7 条）—— 无需 X server 即可稳定判定的真实失败路径：

  * `wmJupiter`（无参）：main() 第一步就是 initXwindow(argc, argv)
    （wmJupiter.c:319），其中 XOpenDisplay 失败时
    `fprintf(stderr, "%s: can't open display %s\n", argv[0], XDisplayName(...))`
    后 exit(1)。鸿蒙 PC 与 CI 都没有 X display，这就是本包交付口径下的
    "真实失败形态"（wmcalc/0.7、wmcdplay/1.1 同款申报）。
  * `wmJupiter -display :<N>`：initXwindow 的 argv 扫描循环把 `-display` 的值
    送给 XDisplayName()，所以报错串里必须原样出现该 display 串（`:<N>`）——
    该串来自 argv 解析的结果而非脚本回显，可判定参数处理循环真实执行。
    N 由脚本按 PID 分散取（300 段），与本脚本对端自用的 20-219 段不相交，
    避免写死某号时撞上残留的 X11 监听（那时客户端会连上并永久等 setup 应答）。

  A 类同时就是动态链接证明：产物 NEEDED 含 libXpm.so.4 / libX11.so.6 /
  libXext.so.6（readelf -d 一手取证），任一条解析不到都会在进入 main 之前
  由 loader 报 "error while loading shared libraries"，不会打印上面那句。

  B 类（17 条）—— 完整消费者用例（rule12 鸿蒙特有测试）：由 x11_headless.py
  实现的**协议级 headless X11 对端**（自行应答 setup / QueryExtension /
  ListExtensions / CreateWindow / ChangeProperty / CreatePixmap / CreateGC /
  PutImage / CopyArea 等 X11 线协议请求，非 Xvfb、不设 DISPLAY=:0、不 dlopen
  —— E530 三条禁令均未触犯）在 127.0.0.1 上临时监听，再驱动真实二进制
  wmJupiter 走完整流程。四段式：构造输入（端口=6000+显示号）→ 真实执行
  （wmJupiter 连上对端、解码 XPM、建窗、注册 WM 属性、PutImage/CopyArea 推帧）
  → 产出（对端累积的服务端窗口/属性/帧缓冲状态 + 客户端退出码）→ 校验
  （B1-B17 断言逐项比对真实产出的服务端状态）。

脚本按 xeyes/xidle/wmcalc 已过门禁的口径执行：用注入的 SHELL/CONFIG_SHELL
（设备实测 /bin/bash 与 /usr/bin/python3 均 MISSING，只有 /bin/sh=toybox ash）
跑 POSIX sh 脚本，不用 `set -eu`、不用 pipefail。
"""
import os

from conan import ConanFile


class WmjupiterTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["wmjupiter"]
        binary = os.path.join(package.package_folder, "bin", "wmJupiter")
        script = os.path.join(self.recipe_folder, "test_wmjupiter.sh")
        shell = (os.environ.get("SHELL") or os.environ.get("CONFIG_SHELL")
                 or "/bin/sh")
        if not os.path.isfile(shell):
            shell = "/bin/sh"
        self.run(f'"{shell}" "{script}" "{binary}"', env="conanrun")
