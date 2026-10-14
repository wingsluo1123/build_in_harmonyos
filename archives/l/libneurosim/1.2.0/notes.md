# libneurosim 1.2.0 适配笔记

## 定位
- 上游 INCF/libneurosim v1.2.0，神经模拟连接生成库（connection_generator）
- 构建系统: autotools（configure.ac，tarball 无预生成 configure，需 autogen.sh）
- 产物: libneurosim（-lneurosim）

## 构建要点
- source 后先 `./autogen.sh` 生成 configure
- configure 参数：`--without-mpi --with-python=no`（可选依赖默认不启用）
- 自带 libltdl 子目录（SUBDIRS = libltdl neurosim libpyneurosim）

## 测试
- 上游无自动化测试套件（无 make check 目标）
- test_package 消费者用例（4 断言）验证库可被第三方编译/链接/调用

## 遇到的问题与解决方案
| # | 问题 | 解决方案 |
|---|------|----------|
| 1 | tarball 无预生成 configure | build() 先跑 ./autogen.sh |

## 验证
- 本地 `conan create . --profile=ohos-aarch64`：消费者用例通过
