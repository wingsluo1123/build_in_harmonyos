# QSoas

QSoas 是面向科学数据处理、拟合和脚本化分析的 Qt 应用程序，支持 mruby 脚本以及通过
JSON 行协议调用外部数值函数。

## HarmonyOS PC 适配

3.3 版本使用 qmake 和已发布的 `qt5/5.15.19`、`mruby/3.3.0`、`gsl/2.8` 制品构建。
适配提供确定性构建元数据、可迁移 qmake 视图、缺失可选 Qt 模块的明确能力边界，并为外部
函数事务加入覆盖启动、写入和完整响应的单调总截止时间。ZIP 是上游按系统头文件选择的
可选能力；现有 libzip 与 Qt 制品的 zlib 版本闭包冲突，未计入本次交付。

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 3.3 | built | HarmonyOS PC armv8 首次适配 |

## 参考资料

- 上游项目：<https://github.com/fourmond/QSoas>
- 项目主页：<https://qsoas.org/>
