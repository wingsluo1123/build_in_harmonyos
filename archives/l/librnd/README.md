# librnd

Modular 2D CAD framework that drives pcb-rnd and other Ringdove EDA applications.

- 上游：http://repo.hu/projects/librnd（源码 `svn://repo.hu/librnd/trunk`，无 Git）
- 版本：4.5.0（2026-07-05）
- 构建：自研 scconfig `./configure` + `make`（非 GNU autotools / CMake）
- OHOS 适配：关闭 GTK/lesstif/GD 等 GUI 依赖，以无头 batch 形态构建核心库；
  上游 `make test` 的 5 个自检套件在配方 `build()` 内真实执行。
