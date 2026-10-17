#!/usr/bin/env python3
"""Conan recipe — btrfs-compsize 1.5（上游 compsize）

compsize 统计一组 btrfs 文件在压缩 / reflink / 部分覆盖 extent 下的实际磁盘占用，
输出 none/zlib/zstd/... 各压缩类型的使用量与有效压缩比。

上游为纯 C 程序（compsize.c + radix-tree.c），自带 kerncompat.h / radix-tree.* /
endianness.h，仅一个 Makefile，无 autotools / cmake / meson、无第三方依赖。

适配要点：

1. **btrfs 头文件（核心）**。上游无条件 `#include <btrfs/ioctl.h>` 与
   `<btrfs/ctree.h>`（发行版由 libbtrfs-dev 提供）。OHOS sysroot 不带 `btrfs/`
   目录，但**自带内核 uapi**：`<linux/btrfs.h>`（BTRFS_IOC_TREE_SEARCH_V2、
   struct btrfs_ioctl_search_key / _header）与 `<linux/btrfs_tree.h>`
   （struct btrfs_file_extent_item、BTRFS_EXTENT_DATA_KEY、BTRFS_FILE_EXTENT_*）。
   本配方在 generate() 生成两个薄 shim 头 `btrfs/ioctl.h`、`btrfs/ctree.h` 转包
   uapi，并以 `-I` 暴露给编译；同时以 `-DBTRFS_FLAT_INCLUDES=1` 让上游
   radix-tree.h 选用其自带的本地 kerncompat.h（而非 `<btrfs/kerncompat.h>`）。
   零外部依赖、零需链接的原生库（ioctl 由 libc 提供）。

2. **纯 Makefile 应用型配方（E392）**：`make CC=<cc> CPPFLAGS=... -j1`，CC 取自
   conf `tools.build:compiler_executables`（R33，不读裸环境变量）。

3. **无 btrfs 文件系统亦可构建/运行**：`compsize --help` 打印用法并 exit 0；
   对空目录输入打印 "No files." 并 exit 1。test_package 以这两条确定性 oracle
   验证，无需 root、无需真实 btrfs（README 所述 ioctl 需 root 的路径不触发）。
"""
import gzip
import os
import shlex

from conan import ConanFile
from conan.tools.files import get, copy, save, mkdir
from conan.tools.layout import basic_layout


class BtrfsCompsizeConan(ConanFile):
    name = "btrfs-compsize"
    version = "1.5"
    description = "compsize — report compression/reflink space usage of files on a btrfs filesystem"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/kilobyte/compsize"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _make_btrfs_shims(self):
        """生成 <btrfs/ioctl.h> 与 <btrfs/ctree.h> 薄 shim，转包 OHOS 内核 uapi。"""
        inc = os.path.join(self.generators_folder, "btrfs-shim", "btrfs")
        mkdir(self, inc)
        save(self, os.path.join(inc, "ioctl.h"), "#include <linux/btrfs.h>\n")
        save(self, os.path.join(inc, "ctree.h"), "#include <linux/btrfs_tree.h>\n")

    def generate(self):
        self._make_btrfs_shims()

    def build(self):
        shim_root = os.path.join(self.generators_folder, "btrfs-shim").replace("\\", "/")
        cppflags = f"-I{shim_root} -DBTRFS_FLAT_INCLUDES=1"

        # R33: 编译器来自 Conan conf，绝不读裸 shell 环境变量。
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        # R9: 一律 -j1。
        self.run(
            f"make CC={shlex.quote(cc)} CPPFLAGS={shlex.quote(cppflags)} -j1",
            cwd=self.source_folder,
        )

    def package(self):
        copy(self, "compsize", self.source_folder, os.path.join(self.package_folder, "bin"))
        # 上游 install 目标把 man 页 gzip 到 share/man/man8/compsize.8.gz；用 python
        # gzip 复刻，避免依赖 worker 上的 gzip 可执行文件。
        man_src = os.path.join(self.source_folder, "compsize.8")
        if os.path.exists(man_src):
            man_dir = os.path.join(self.package_folder, "share", "man", "man8")
            os.makedirs(man_dir, exist_ok=True)
            with open(man_src, "rb") as fin, gzip.open(
                os.path.join(man_dir, "compsize.8.gz"), "wb"
            ) as fout:
                fout.write(fin.read())

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
