# -*- coding: utf-8 -*-
"""cryptography.hazmat.primitives.ciphers.modes 桩 —— CBC 仅 import 期符号。"""


class CBC:
    """CBC 模式桩：真实加解密需 Rust 绑定，构造即报错。"""

    def __init__(self, iv):
        raise NotImplementedError(
            "cryptography.hazmat.primitives.ciphers.modes.CBC is not available on "
            "this platform (OHOS test env); real AES operations require the "
            "cryptography Rust extension which the OHOS loader rejects."
        )
