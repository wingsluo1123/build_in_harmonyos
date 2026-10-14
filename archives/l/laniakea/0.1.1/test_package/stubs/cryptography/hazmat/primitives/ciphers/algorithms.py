# -*- coding: utf-8 -*-
"""cryptography.hazmat.primitives.ciphers.algorithms 桩 —— AES 仅 import 期符号。"""


class AES:
    """AES 算法桩：真实加解密需 Rust 绑定，构造即报错。"""

    def __init__(self, key):
        raise NotImplementedError(
            "cryptography.hazmat.primitives.ciphers.algorithms.AES is not "
            "available on this platform (OHOS test env); real AES operations "
            "require the cryptography Rust extension which the OHOS loader rejects."
        )
