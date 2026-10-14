# -*- coding: utf-8 -*-
"""cryptography.hazmat.backends 桩 —— 提供 default_backend import 期符号。"""


def default_backend():
    """真实 AES 后端选择需 cryptography 的 Rust 绑定，调用即报错。"""
    raise NotImplementedError(
        "cryptography.hazmat.backends.default_backend is not available on this "
        "platform (OHOS test env); real AES operations require the cryptography "
        "Rust extension which the OHOS loader rejects."
    )
