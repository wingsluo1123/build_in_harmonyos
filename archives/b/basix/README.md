# Basix

FEniCS 的有限元基函数、导数、插值和变换库。
官方仓库：https://github.com/FEniCS/basix。

适配版本0.11.0包含C++共享库和匹配CPython3.12的Python绑定。
Conan依赖为OpenBLAS0.3.34、nanobind2.13.0和robin-map1.4.1。
Python消费者需要自己的匹配NumPy运行环境；包内官方发行元数据保留此
依赖合同。原数学测试的固定运行输入用于验证，不作为应用运行环境的
自动安装承诺。

代码、原测试、支持域及交付边界见版本目录，平台CI和正式发布独立验收。
