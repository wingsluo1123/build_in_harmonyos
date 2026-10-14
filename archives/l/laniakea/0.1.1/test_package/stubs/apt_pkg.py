# -*- coding: utf-8 -*-
"""apt_pkg 桩（OHOS 测试环境专用，仅满足 import 期符号）。

laniakea 多个模块（laniakea.db.archive / laniakea.reporeader /
laniakea.archive.* / laniakea.utils.gpg / archivecli.validate /
spears.spearsengine / synchrotron.syncengine）在模块顶层 ``import apt_pkg``
（Debian 专属 C 绑定，python-apt 提供）。OHOS 无该绑定，本桩只提供
import 期用到的符号名（Hashes/TagFile/TagSection/version_compare），
**任何真实解析能力被调用即抛 NotImplementedError**，不伪造 Debian
专属行为。真实 apt_pkg 解析在 OHOS 不可用（已知限制，见 notes.md）。
"""


class Hashes:
    """apt_pkg.Hashes 桩：真实计算需 C 绑定，调用即报错。"""

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "apt_pkg.Hashes is not available on this platform (OHOS); "
            "Debian-specific hashing is out of scope for the stubbed module."
        )


class TagSection:
    """apt_pkg.TagSection 桩：Debian 控制段解析需 C 绑定。"""

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "apt_pkg.TagSection is not available on this platform (OHOS); "
            "Debian control/changes parsing requires the real python-apt binding."
        )


class TagFile:
    """apt_pkg.TagFile 桩：Debian 仓库文件流式解析需 C 绑定。"""

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "apt_pkg.TagFile is not available on this platform (OHOS); "
            "Debian repository file parsing requires the real python-apt binding."
        )


def version_compare(a, b):
    """apt_pkg.version_compare 桩：Debian 版本比较需 C 绑定。"""
    raise NotImplementedError(
        "apt_pkg.version_compare is not available on this platform (OHOS); "
        "Debian package version comparison requires the real python-apt binding."
    )


def init(*args, **kwargs):
    """apt_pkg.init 桩（无操作，仅保证 import 链不中断）。"""
    return None


def init_config(*args, **kwargs):
    """apt_pkg.init_config 桩（无操作）。"""
    return None


def config(*args, **kwargs):
    """apt_pkg.config 桩（无操作）。"""
    return None
