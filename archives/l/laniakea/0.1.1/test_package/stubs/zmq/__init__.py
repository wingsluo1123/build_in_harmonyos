# -*- coding: utf-8 -*-
"""zmq（pyzmq）桩 —— OHOS 测试环境专用，仅满足 import 期符号。

laniakea.msgstream.event_msg 顶层 ``import zmq``（laniakea 消息流
事件，`import laniakea` 链经 msgstream 触发），且函数签名注解
``zmq_context: zmq.Context`` / ``-> zmq.Socket`` 在 import 期即
求值；keytool.py 顶层 ``import zmq.auth``（lk-keytool --version 链）。
但 test_package 的 5 个 CLI --version 链与 signedjson（mock 键）
断言均不创建真实 ZeroMQ socket，不调用 zmq 能力。

OHOS 社区源的 pyzmq wheel（27.1.0）含 libzmq C 扩展（zmq.libzmq /
backend/cython），在 OHOS 真机加载器（ld-musl）上以
``Permission denied`` 被拒（CI #91763 实测，与 cryptography/PyNaCl
同类问题），故测试环境以纯 Python 桩替换真实绑定：只提供 import 期
符号（``zmq.Context``/``Socket`` 类、``DEALER``/``SUB``/``SUBSCRIBE``
常量、``curve_keypair``/``auth.load_certificate``），任何真实 socket
能力被调用即抛 NotImplementedError，不伪造 ZeroMQ 行为。
真实 pyzmq 由消费环境按需提供（本桩仅服务 test_package）。
"""


class Context:
    """ZeroMQ 上下文桩：真实 socket 能力需 libzmq C 扩展，构造即报错。"""

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "zmq.Context is not available on this platform (OHOS test env); "
            "real ZeroMQ sockets require the pyzmq libzmq extension which the "
            "OHOS loader rejects."
        )


class Socket:
    """ZeroMQ socket 桩：真实 socket 能力需 libzmq C 扩展，构造即报错。"""

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "zmq.Socket is not available on this platform (OHOS test env); "
            "real ZeroMQ sockets require the pyzmq libzmq extension which the "
            "OHOS loader rejects."
        )


# Socket 类型常量（与 libzmq 定义一致的整数值；仅 import 期绑定，
# 真实 socket 创建被上述 Context/Socket 桩以 NotImplementedError 拦截）。
DEALER = 4
SUB = 2
SUBSCRIBE = 1


def curve_keypair(*args, **kwargs):
    """Curve 密钥对生成桩：真实能力需 libzmq C 扩展，调用即报错。"""
    raise NotImplementedError(
        "zmq.curve_keypair is not available on this platform (OHOS test env); "
        "real ZeroMQ curve keypairs require the pyzmq libzmq extension which "
        "the OHOS loader rejects."
    )
