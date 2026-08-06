# coinor-cgl 0.60.9 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 定位
- 产出 libCgl.so 等 1 个库，供链接与 dlopen。

## 关键适配
- 删除 lib/*.la：其中烤死 libdir 绝对路径，会把下游 libtool 引到 //lib/ 死路
- 修 configure 的 umask 077→022（HMDFS E011）
- 补转发型 .pc：osi-clp=clp（conan 只生成 recipe 声明的那一个）

## 状态
built（真机 conan create + test_package 通过）
