# -*- coding: utf-8 -*-
"""cryptography.hazmat.primitives.padding 桩 —— PKCS7 仅 import 期符号。"""


class PKCS7:
    """PKCS7 填充桩：真实填充/去填充需 Rust 绑定，构造即报错。"""

    def __init__(self, block_size):
        raise NotImplementedError(
            "cryptography.hazmat.primitives.padding.PKCS7 is not available on "
            "this platform (OHOS test env); real padding requires the "
            "cryptography Rust extension which the OHOS loader rejects."
        )
