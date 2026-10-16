# -*- coding: utf-8 -*-
"""gi.repository 桩 —— 提供 AppStream 占位命名空间（import 期可导入）。

``from gi.repository import AppStream`` 依赖真实 PyGObject 的 AppStream
GObject 绑定（libappstream），OHOS 无。本模块提供占位命名空间对象，
使 import 链可解析；任何真实属性/功能访问（如 ``AppStream.Metadata()``、
``AppStream.FormatStyle.CATALOG``）即抛 NotImplementedError，不伪造
AppStream 元数据解析能力。
"""


class _AppStreamNamespace:
    """AppStream 占位命名空间：真实功能调用即抛 NotImplementedError。"""

    def __getattr__(self, name):
        raise NotImplementedError(
            f"gi.repository.AppStream.{name} is not available on this platform (OHOS); "
            "real AppStream metadata parsing requires PyGObject + libappstream."
        )


AppStream = _AppStreamNamespace()
