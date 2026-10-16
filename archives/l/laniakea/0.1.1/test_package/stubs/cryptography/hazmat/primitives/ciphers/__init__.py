# -*- coding: utf-8 -*-
"""cryptography.hazmat.primitives.ciphers 桩 —— Cipher 仅 import 期符号。"""


class Cipher:
    """AES 加解密器桩：真实加解密需 Rust 绑定，构造即报错。"""

    def __init__(self, algorithm, mode, backend=None):
        raise NotImplementedError(
            "cryptography.hazmat.primitives.ciphers.Cipher is not available on "
            "this platform (OHOS test env); real AES operations require the "
            "cryptography Rust extension which the OHOS loader rejects."
        )
