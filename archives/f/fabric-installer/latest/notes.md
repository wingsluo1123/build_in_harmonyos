# fabric-installer 编译记录

## 编译日期
2026-06-08 (初始适配), 2026-08-06 (Conan 配方适配)

## 软件类型
Shell脚本工具，无需编译

## 处理流程
1. 从Hyperledger Fabric官方仓库下载install-fabric.sh脚本
2. 打包为tar.gz格式
3. 创建归档目录
4. Conan 配方适配: 生成 conanfile.py + conandata.yml + test_package/

## 特殊说明
- 此软件为shell脚本，不需要传统的编译流程（configure/make）
- 直接打包分发即可使用
- 需要bash环境和网络访问能力来下载Fabric组件
- Conan 配方使用 download() 而非 get() 下载脚本（非压缩文件）
- 源码 URL 锁定到 fabric 仓库特定 commit，确保可复现性

## 版本信息
- Fabric默认版本: 2.5.16 (main branch)
- CA默认版本: 1.5.17
- Conan 版本: latest (源码 pin 到 commit 0c423ac47)

## 平台兼容性
- 支持所有Linux平台（x86_64, arm64）
- 支持macOS
- 支持Windows（通过Git Bash或WSL）

## Conan 配方
- package_type: application
- settings: os, arch (无需 compiler/build_type)
- source(): download() 下载 install-fabric.sh
- package(): 复制脚本到 bin/
- test_package: bash 语法检查 + --help 验证

---

**编译结束**: 2026-08-06
**最终状态**: built (conan-verify 通过, 待 CI 上传)
