# -*- coding: utf-8 -*-
"""nacl（PyNaCl）桩 —— OHOS 测试环境专用，仅满足 import 期符号。

laniakea.msgstream.signing 顶层 ``import nacl.signing``（ed25519
签名），但 test_package 的 signedjson 断言使用 **mock 签名键**
（alg="mock"），不调用 nacl 真实签名能力；5 个 CLI --version 链
同样不触发 nacl 签名。

OHOS 社区源的 PyNaCl wheel 含 ``nacl._sodium.abi3.so``（libsodium
C 扩展），在 OHOS 真机加载器（ld-musl）上以 ``Permission denied``
被拒（CI #91660 实测，与 cryptography 同类问题），故测试环境以
纯 Python 桩替换真实绑定：只提供 import 期符号
（``nacl.signing.SigningKey`` / ``VerifyKey``），任何真实签名/
验签能力被调用即抛 NotImplementedError，不伪造 ed25519 行为。
真实 PyNaCl 由消费环境按需提供（本桩仅服务 test_package）。
"""
