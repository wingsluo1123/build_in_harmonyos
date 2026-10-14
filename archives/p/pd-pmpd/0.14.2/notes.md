# pd-pmpd 0.14.2 适配笔记

## 上游构成

`pd-pmpd_0.14.2.orig.tar.gz` 是 Cyrille Henry 的 Pure Data 物理建模对象库
**pmpd**（Physical Modelling for Pure Data），包含 32 个类：`mass`/`mass2D`/
`mass3D`、`link`/`link2D`/`link3D`、`pmpd`/`pmpd2d`/`pmpd3d` 与信号版
`pmpd~`/`pmpd2d~`/`pmpd3d~`、`i*`（interactor）、`t*`（train）等。上游使用
CMake 构建，每个类产出一个共享对象。

## 构建

- **Pd API 头**：制品仓 `puredata/0.54.1` 是 *application*，不暴露 `m_pd.h`。
  配方在 `source()` 额外拉取同版本 `pure-data 0.54-1` 源码树，并把
  `PUREDATA_INCLUDE_DIRS` 指向其 `src`。
- **对象文件名**：上游 CMake 默认给对象加多架构后缀（`.linux-arm64-32.so`），
  Pd 的标准加载器认的是 `.pd_linux`，故通过 `PUREDATA_SUFFIX=.pd_linux` 覆盖。
- `git_info.cmake` 在非 git 源码树上优雅降级（返回 `...-NOTFOUND`），无需改源。
- 纯 C，零三方依赖；CMake 构建产出 **32** 个 `.pd_linux`。

## 产物

| 路径 | 说明 |
|------|------|
| `lib/pd-externals/*.pd_linux` | 32 个 pmpd 外部对象 |
| `lib/pd-externals/*-help.pd` | 帮助补丁 |
| `lib/pd-externals/pmpd-meta.pd` | 库元数据 |

## 测试

上游无自动化测试套件（只有帮助补丁与 `examples/` 示例补丁）→ 上游 N=0。

消费者测试 `test_package/test_pd_pmpd.sh`（2 项断言）用**真机 OHOS `pd`** 无头
加载安装后的外部对象，驱动确定性的 `[mass]` 位置输出：

- `[mass]` + `setX 0` + `bang` → X 位置 `0`
- `[mass]` + `setX 5` + `bang` → X 位置 `5`

真机 `conan create`：`CREATE_RC=0`，消费者 2/2。

> 备注：`pd` 用 `timeout 20` 结束，避免 `; pd quit;` 与输出竞争丢行。
