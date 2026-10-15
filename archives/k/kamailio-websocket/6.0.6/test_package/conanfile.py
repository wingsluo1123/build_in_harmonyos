#!/usr/bin/env python3
"""Conan test_package — kamailio-websocket L1 消费者视角测试。

websocket.so 由 kamailio 二进制运行时 dlopen（WS/WSS 握手需运行中的 kamailio +
SIP 场景），故按产物结构做实质校验：ELF 架构、OpenSSL 静态链入证据（SHA1/
EVP_sha1/OPENSSL_init_crypto/OPENSSL_cleanup 符号 + NEEDED 无 libssl/libcrypto）、
libunistring 静态链入（u8_check 符号）、模块入口符号（mod_register）、
许可证文件与宿主路径泄漏检查。
"""
import os
import sys

from conan import ConanFile
from conan.tools.env import Environment


class KamailioWebsocketTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34 实质验证：对打包产物 websocket.so 做真实检查
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        module = os.path.join(package_folder, "lib", "kamailio", "modules", "websocket.so")
        assert os.path.isfile(module), f"websocket.so not found at {module}"
        self.output.info(f"websocket.so found: {module}")

        checker = os.path.join(self.source_folder, "check_websocket.py")
        env = Environment()
        env.define("KAMAILIO_WEBSOCKET_MODULE", module)
        env.define("KAMAILIO_WEBSOCKET_PACKAGE_FOLDER", package_folder)
        with env.vars(self).apply():
            self.run(f'"{sys.executable}" "{checker}"')
