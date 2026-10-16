# -*- coding: utf-8 -*-
"""nacl.signing 桩 —— SigningKey/VerifyKey 仅 import 期符号。

laniakea.msgstream.signing 顶层 ``import nacl.signing`` 即触发
真实 PyNaCl 的 libsodium 扩展（nacl._sodium.abi3.so），OHOS 真机
加载器拒绝（CI #91660 实测 Permission denied）。test_package 的
signedjson 断言用 mock 签名键（alg="mock"），不调用 nacl 真实
签名，因此仅需 import 期符号可解析即可。真实 ed25519 签名/验签
能力被调用即抛 NotImplementedError（不伪造）。
"""


class SigningKey:
    """ed25519 签名密钥桩：真实签名需 PyNaCl libsodium 扩展，构造即报错。"""

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "nacl.signing.SigningKey is not available on this platform "
            "(OHOS test env); real ed25519 signing requires the PyNaCl "
            "libsodium extension which the OHOS loader rejects."
        )

    @classmethod
    def generate(cls, *args, **kwargs):
        raise NotImplementedError(
            "nacl.signing.SigningKey.generate is not available on this "
            "platform (OHOS test env); real ed25519 signing requires the "
            "PyNaCl libsodium extension which the OHOS loader rejects."
        )


class VerifyKey:
    """ed25519 验签密钥桩：真实验签需 PyNaCl libsodium 扩展，构造即报错。"""

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "nacl.signing.VerifyKey is not available on this platform "
            "(OHOS test env); real ed25519 verification requires the PyNaCl "
            "libsodium extension which the OHOS loader rejects."
        )
