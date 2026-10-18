#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""osmin 消费者测试（R34：真实执行被测包产物，非空壳断言）。

osmin 是 Qt6 Quick 图形应用，没有 --version/--help 之类的命令行开关；其内置
无头分支 `osmin -service`（src/osmin.cpp:69 定义、:154 分派）走 QCoreApplication
+ QRemoteObjectHost 本地套接字，不依赖显示设备与 DBus，是同一产物的第二个真实
消费者入口。

测试分两步：
  1. 产物 bin/osmin 存在，且为 OHOS/aarch64 的 64 位 ELF（直接解析 ELF 头，
     不额外依赖 file/readelf 等工具）；
  2. 执行 test_package/run_osmin_service_test.sh：以可写 HOME 真实启动无头服务，
     要求进程完成 Qt 初始化并进入事件循环存活到超时（rc=0/124/143）、数据目录
     被真实创建、启动日志无动态库加载失败与崩溃标记。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run

_ELF_MAGIC = b"\x7fELF"
_ELFCLASS64 = 2
_EM_AARCH64 = 0xB7

_SERVICE_TEST = "run_osmin_service_test.sh"


class OsminTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindir = self.dependencies["osmin"].cpp_info.bindir
        binary = os.path.join(bindir, "osmin")
        if not os.path.isfile(binary):
            raise ConanException(f"未找到被测产物: {binary}")

        with open(binary, "rb") as handle:
            header = handle.read(20)
        if header[:4] != _ELF_MAGIC or header[4] != _ELFCLASS64:
            raise ConanException(f"{binary} 不是 64 位 ELF 文件")
        if int.from_bytes(header[18:20], "little") != _EM_AARCH64:
            raise ConanException(f"{binary} 不是 aarch64 架构")

        if not can_run(self):
            self.output.info("当前为跨架构环境，跳过执行测试（仅校验产物形态）")
            return

        script = os.path.join(self.source_folder, _SERVICE_TEST)
        log = os.path.join(self.build_folder, "osmin-service.log")
        home = os.path.join(self.build_folder, "testhome")
        # 收尾清理：临时 HOME 与启动日志都落在构建目录里，测试结束即删除，
        # 避免在源码树留下残留（CI 垃圾文件门禁）。
        try:
            self.run(f'sh "{script}" "{binary}" "{log}" "{home}"', env="conanrun")
        finally:
            shutil.rmtree(home, ignore_errors=True)
            if os.path.isfile(log):
                os.remove(log)
