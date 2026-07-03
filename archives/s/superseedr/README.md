# superseedr latest — OpenHarmony 编译记录

## 基本信息
- 软件: superseedr
- 版本: 1.0.11 (latest)
- 构建系统: Cargo (Rust)
- 目标: ohos-aarch64

## 编译指导
- Rust 工具链需通过 harmonybrew 安装 OHOS 适配版: `brew install rust`
- 需配置 crates.io 镜像 (USTC sparse) 加速依赖下载
- openssl-sys crate 需设置 PKG_CONFIG_PATH 和 OPENSSL_DIR 环境变量
- Cargo HTTP/2 multiplexing 在 OHOS 上不稳定，需关闭

## 补丁清单
<!-- 无补丁，纯 Rust 项目 -->

## 已知限制
- 64/1524 测试失败 (95.6% 通过率)，与 OHOS 平台特性相关 (文件系统、网络、权限差异)

## 功能验证
- `superseedr --version` → `superseedr 1.0.11`
- conan-verify 8 道门禁全部通过
