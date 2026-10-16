# indi-nexdome

**NexDome 个人天文台圆顶的 INDI 驱动**（上游：https://github.com/indilib/indi-3rdparty）

`indi-nexdome` 是 INDI 生态中的第三方驱动，由 `indiserver` 拉起，通过 INDI XML
协议（stdin/stdout）向任意 INDI 客户端（KStars、Xephem 等）暴露 NexDome 2.4 m
个人天文台圆顶的旋转与开合控制。产物为可执行驱动 `indi_nexdome` 及设备描述文件
`indi_nexdome.xml`。

## OHOS 适配要点

1. **INDI API 迁移**：源码基于 INDI 1.9.x，需把已移除的数组式属性名
   （`DomeParamN`/`DomeAbsPosN`/`DomeShutterS`/`ShutterParkPolicyS`）迁移到
   libindi 2.x 的 `INDI::Property` API（与上游 master 的移植一致）。
2. **C++17**：libindi 2.x 头文件使用 `std::any`，须按 C++17 编译。
3. **静态链接 INDI**：本平台无法 dlopen libindi 的共享对象，须静态链接其归档；
   且驱动目标必须排在 INDI 静态库之后（`.init_array` 顺序），否则全局设备对象
   会先于 INDI 静态初始化构造而段错误。
4. **RPATH/codesign**：禁用 build/install RPATH，避免 install 改写破坏 OHOS ELF
   的 `.codesign`；运行时依赖经 `LD_LIBRARY_PATH` 解析。

## 依赖

- libindi/2.2.2.1（INDI 框架：`INDI::Dome` 基类与驱动 main）
- libnova/0.16
- zlib/1.3.1.1

## Homepage

https://indilib.org

## License

LGPL-2.0-or-later

## Category

astronomy
