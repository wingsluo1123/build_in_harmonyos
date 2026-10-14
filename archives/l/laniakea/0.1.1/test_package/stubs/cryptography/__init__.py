# -*- coding: utf-8 -*-
"""cryptography 桩 —— OHOS 测试环境专用，仅满足 import 期符号。

laniakea.utils.traceback 顶层 ``from cryptography.hazmat...`` 导入
AES-CBC 加解密符号（用于加密 traceback 供公开日志），但该功能仅在
``format_encrypted_traceback`` / ``decrypt_traceback_string`` 中调用，
CLI --version 链与 test_package 断言均不触发。

OHOS 社区源的 cryptography wheel 含 Rust 扩展 ``_rust.abi3.so``，
在 OHOS 真机加载器（ld-musl）上以 ``Permission denied`` 被拒（CI
#91056 实测），故测试环境以纯 Python 桩替换真实绑定：只提供
import 期符号名（default_backend/PKCS7/Cipher/AES/CBC），任何真实
加密/解密能力被调用即抛 NotImplementedError，不伪造 AES 行为。
真实 cryptography 由消费环境按需提供（本桩仅服务 test_package）。
"""
