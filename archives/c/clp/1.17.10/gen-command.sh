#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --name clp --version 1.17.10 --build-system autotools --source-url https://github.com/coin-or/Clp/archive/refs/tags/releases/1.17.10.tar.gz --sha256 0d79ece896cdaa4a3855c37f1c28e6c26285f74d45f635046ca0b6d68a509885 --test-lang cpp --pc-cflags 'coinutils=-I${includedir}/coin' --requires coinutils/2.11.13,zlib/1.3.1,coinor-osi/0.108.11 --libs Clp,ClpSolver,OsiClp --pkgconfig-name clp --pkgconfig-deps --out <输出根目录>
