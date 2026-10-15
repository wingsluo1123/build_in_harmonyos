# Plyvel

Plyvel 是 LevelDB 的 Python 接口，支持二进制键值、排序迭代、快照、原子批写、前缀数据库及 Python 比较器回调。

运行依赖由 Conan 管理的 Python 与 LevelDB 共享库。构建使用 setuptools，测试使用 pytest；发布源码包内含 Cython 预生成 C++，无需现场生成代码。

HarmonyOS PC 使用原生 AArch64 CPython ABI，分别配置 C/C++ 扩展链接器，显式链接 libpython，按 LevelDB 的 no-RTTI 构建方式编译比较器子类，并在最终路径签名扩展。HMDFS 无法建立只读目录时，上游对应测试按实际能力跳过；该限制不等于测试通过。逐版本统计及验证边界见版本目录。

上游：https://github.com/wbolster/plyvel；安装说明：https://plyvel.readthedocs.io/en/latest/installation.html。
