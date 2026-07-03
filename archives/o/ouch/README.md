# ouch latest — OpenHarmony 编译记录

## 基本信息
- 软件: ouch
- 版本: 0.8.0 (latest)
- 构建系统: Cargo (Rust)
- 目标: ohos-aarch64

## 编译指导
- Rust 工具链需通过 harmonybrew 安装 OHOS 适配版
- Rust 链接器默认 -lstdc++ 但 OHOS 只有 libc++，需创建 libstdc++.so 链接器脚本重定向到 libc++ (E212)
- GitHub 下载慢可使用 ghfast.top 镜像

## 已知限制
- tar_hardlink 测试失败: OHOS 硬链接创建权限被拒绝

## 功能验证
- `ouch --version` → `ouch 0.8.0`
- conan-verify 8 道门禁全部通过
