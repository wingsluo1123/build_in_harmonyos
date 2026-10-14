# -*- coding: utf-8 -*-
"""zmq.auth 桩 —— keytool.py 顶层 ``import zmq.auth`` 仅需此包可导入。

keytool.py（lk-keytool --version 链）顶层 import zmq.auth，但
--version 路径不调用 ``load_certificate``（真实证书解析能力需
pyzmq 的 Curve/CA 实现，含 libzmq 扩展，OHOS 真机加载被拒，
CI #91763 同类问题）。真实能力被调用即抛 NotImplementedError。
"""


def load_certificate(*args, **kwargs):
    """Curve 证书加载桩：真实能力需 pyzmq 实现，调用即报错。"""
    raise NotImplementedError(
        "zmq.auth.load_certificate is not available on this platform "
        "(OHOS test env); real ZeroMQ curve certificate loading requires "
        "the pyzmq implementation which the OHOS loader rejects."
    )
