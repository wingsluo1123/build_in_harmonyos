# 上游烘焙常量=行为语义锚：被静默收敛的测试面里藏着源码重构回归（u-boot expo 文本行光标位置；零修改测试文件下恢复源码行为语义）

- **草稿 ID**: DRAFT-11418-uboot-expo-cursor-at-text-end
- **来源**: u-boot 2026.07 HarmonyOS PC 适配（SDL 门控测试面经制品仓 sdl2 接入后，逐子测试一次性暴露 16 项存量失败——15 项夹具缺失 + 1 项本回归；本项为最后一项：`cedit_render_lineedit` 期望帧 5283 实得 5270）
- **分类**: upstream-regression / test-surface / expo / video-console
- **状态**: 本地草稿（路径 B 知识库扩展申请中）
- **关联**: 暴露该回归的测试面接入见 DRAFT-11418-uboot-sandbox-sdl2-registry-dep（同一 SDL 测试面：接入即照出"面未跑时不可见"的全部存量分歧）

## 问题 / 错误签名

- 真机（SDL 面在位）单元测试失败：
  `ut bootstd cedit_render_lineedit` → `test/boot/cedit.c:413, Expected 0x14a3 (5283), got 0x1496 (5270)`
- 失败点是"打开既存文本 `my-machine` 的文本行"这一帧的像素断言：该测试把渲染帧经 `video_compress_fb`（bz2）压缩后的**字节长度**与烘焙常量比较——前两帧（5336/5363）命中、第三帧（5283）偏差 13 字节。
- 隐蔽性：该测试面 `depends on VIDEO_SANDBOX_SDL`，宿主无 SDL2 时被 Kconfig 按 depends **静默收敛**（构建成功、零告警；上游 CI 形态同样不执行该面）——回归发生在上游 CI 不跑的测试面里，跨越多个发行版本无人察觉。

## 根因

1. **行为分歧点**：`scene_textline_render_deps()`（boot/scene_textline.c）打开分支在文本绘制完成后执行
   `vidconsole_entry_restore(cons, &scn->entry_save)`——把控制台状态**回卷**到 `scene_textline_open()` 时刻的存档；彼时 `vidconsole_set_cursor_pos()` 已把笔位钉在**字段起点**（x=250）。随后 `vidconsole_set_cursor_visible(cons, true, ..., scn->cls.num)` 的定位走 `index < pos_ptr ? pos[index] : xcur` 分支（index=10 ≥ pos_ptr=0）取 `xcur` → 光标画在**字段起点**（帧长 5270）。
2. **烘焙帧的语义**：期望值 5283 对应的帧是**光标画在既存文本末尾**（x=329＝绘完 10 个字形后的实时笔位）。测试引入提交 c43791c4 的提交信息明言 *The cursor should start at the end*，且该常量在各发行标签间未变（烘焙后无 rebake）——即引入时源码行为=末尾、其后场景重构改变了行为（`dim.x→bbox.x0` 一族的机械重构），属**源码回归**而非测试过期。
3. **为什么修复取源码侧**：定性证据链 = ①测试引入提交的意图判词（光标在末尾）；②烘焙帧的逐像素内容（光标在末尾）；③常量跨发行版未变（无 rebake 记录）。交付约束"上游测试文件零修改"下唯一正确方向=恢复源码行为语义。

## 定位方法（帧压缩长度非单射——本项关键教训）

- bz2 压缩长度是**非单射**：不同帧可同长、近邻值差几字节毫无像素几何含义——单凭 5270 vs 5283 猜"少了什么"不可证。
- 正确路径：**dump 原始帧**（在 `BZ2_bzBuffToBuffCompress` 的正常终止块挂钩子，`os_write_file()` 写文件——**绕 u-boot 控制台**，否则打印本身会画进 LCD 使被断言帧被观测者效应污染）→ 与上游 dtc/工具链产物逐像素比对；辅以**参数扫描**（临时以环境变量覆写光标 x）确认 5283 恰对应"光标在末尾"的定值。
- 钩子一律 `assert 锚点命中次数==1`+幂等标记，重放脚本化（.cmd 回放编译单个 .o + 重链接）。

## 最小修复方案（一行）

```c
/* scene_textline_render_deps() 打开分支（boot/scene_textline.c） */
-  ret = vidconsole_entry_restore(cons, &scn->entry_save);
+  /*
+   * Start a new entry rather than restoring the state saved at
+   * open time: the pen is already at the end of the existing
+   * text, which is where the cursor should be shown
+   */
+  ret = vidconsole_entry_start(cons);
```

- `entry_start()` 清位置历史（pos_ptr=0）但**不回卷笔位**——`set_cursor_visible` 取 live xcur＝刚绘完文本的实时笔位＝末尾，帧逐字节＝5283。
- **勿连带改**逐键编辑路径 `scene_textline_send_key()` 的 `entry_restore → cread_line_process_ch → entry_save` 配对（每键自存档-恢复，语义独立且正确）；`scene_textline_open()` 写入的 `entry_save` 保持原样。

## 验证（2026-10-10 真机）

- 修复后 `cedit_render_lineedit` **failures: 0**：四帧 destLen 5336/5363/5283/5170 全中（含此前未达的第四帧）。
- 回归零扰动：`cedit_render` 12 帧逐字节不变、空场打开帧 4851 不变；逐子测试全链 919/919（`conan create` 全链 4826 秒；见 sdl2 草稿的测试面口径）。
- 官方 conan-verify 八门禁 Verdict: PASS（2026-10-10 复跑）。

## 教训 / 泛化

- **烘焙常量是行为语义的锚**：测试往往把"完整帧的压缩长度"当断言——常量不只锁格式，还锁像素语义（本例=光标画在文本末尾）。遇"源码行为 vs 烘焙常量"分歧，先查测试引入提交的提交信息（意图判词）再定性：源码回归→改源码并全量回归其余常量；测试过期→上报上游，勿本地静默重烘。
- **"构建通过"与"测试面在位"是两回事**：依赖门控（Kconfig `depends on` + 宿主缺件探针）可让整片测试面静默消失，源码回归因此长期不可见；接入/恢复测试面的动作本身是资产——一次性照出全部存量分歧（本例 16 项）。
- **压缩长度非单射**：以长度差反推内容必错；必须 dump 原始标物（帧）逐字节/逐像素比对，且仪器化须绕开被测面本身（控制台打印会画进 LCD 帧——观测者效应）。
- **最小修复优先**：一行改动+零连带语义（逐键路径、open 存档不动），配"其余全部烘焙常量逐字节不变"的回归证据，比任何宏大重构更有说服力。
