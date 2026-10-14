# -*- coding: utf-8 -*-
"""gi（PyGObject）桩 —— OHOS 测试环境专用，仅满足 import 期符号。

laniakea.archive.appstream（被 archivecli.publish 顶层 import → lk-archive
触发）与 webswview 视图顶层 ``import gi`` / ``gi.require_version('AppStream',
'1.0')`` / ``from gi.repository import AppStream`` —— 需系统级 GObject
Introspection 绑定（libgirepository + AppStream 库），OHOS 无、pip 无法安装。

本桩只提供 import 期符号：``require_version()`` 为 no-op，
``gi.repository.AppStream`` 为占位命名空间；真实 AppStream 功能
（如 ``AppStream.Metadata()``）被调用即抛 NotImplementedError，不伪造
元数据解析能力（与 apt_pkg 桩同思路，详见 notes.md 已知限制）。
"""


def require_version(namespace, version):
    """gi.require_version 桩：no-op（仅满足 import 期，不校验命名空间/版本）。"""
    return None
