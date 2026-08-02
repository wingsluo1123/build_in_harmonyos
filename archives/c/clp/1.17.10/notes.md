# clp 1.17.10 适配笔记

## 基本信息
- 软件: clp (COIN-OR Linear Programming)
- 版本: 1.17.10
- 构建系统: autotools
- 依赖: CoinUtils/Osi（未发布到制品仓，不声明 conan 依赖，依赖系统预装，R36）

## 关键问题
### E072: config.sub 不识别 ohos 三元组
替换 config.sub/config.guess 为支持 ohos 的版本

### 依赖说明
Clp 编译期需要 CoinUtils（ClpSimplex.hpp include coin/*.hpp）；Osi 是 OsiClp 子项目的依赖。
CoinUtils/Osi 未发布到制品仓（archives/c/coinutils/ 有 2.11.13 配方但未发布），
故 conanfile.py requirements() 不声明依赖，构建依赖系统预装环境。

## 编译命令
./configure --prefix=$DEFAULT_PREFIX CC=clang CXX=clang++ --enable-static --disable-shared
make -j1
make install
