# 上游环境文件的宿主特性 #ifdef 门控在非默认配置组合下静默丢测试面：sandbox.env 的 SDL 门控吞掉 usbkbd stdin 条目 → dm_test_usb_keyb 必失败

- **草稿 ID**: DRAFT-11418-uboot-sandbox-env-sdl-gated-stdin
- **来源**: u-boot 2026.07 HarmonyOS PC 适配（非 SDL 构建下 sandbox.env 的 SDL 门控吞掉 usbkbd stdin 条目 → dm_test_usb_keyb 必失败；KDBG 仪器化定位 + setenv 反向验证；最终交付经制品仓 sdl2 依赖接入回到上游 SDL=y 同形，门控自然命中、专用补丁退役）
- **分类**: testing / sandbox / config-matrix / console-input
- **状态**: 本地草稿（路径 B 知识库扩展申请中）
- **关联**: 与 DRAFT-11418-uboot-sandbox-sdl2-registry-dep 同源（同为"构建偏离上游配置形态"导致的测试面静默消失：一个丢 stdin 键盘面、一个丢 video/cedit/expo 面）；初版对应适配补丁 0016（`#elif defined(CONFIG_USB_KEYBOARD)` 门控解耦），最终随 sdl2 接入退役（方案留档为无 SDL 宿主的备选）

## 问题 / 错误签名

- **`dm_test_usb_keyb` live 遍失败**：`test/dm/usb.c:449, dm_test_usb_keyb(): 1 == tstc(): Expected 0x1 (1), got 0x0 (0)`——emul 键盘经 `sandbox_usb_keyb_add_string()` 注入 scancode 后 `tstc()` 仍为 0。
- **flat 遍级联失败**：`test/dm/usb.c:433 ... uclass_get_device_by_name(UCLASS_USB_EMUL, "keyb@3") ... got -5 (-ENOENT)`（live 失败 longjmp 后 DM 状态未走完 `usb_stop()` 清理的次生现象）。
- **复现**：无 SDL2 宿主（OHOS 初版状态，`CONFIG_SANDBOX_SDL` 收敛为 n）构建的 sandbox 二进制上必现；上游 CI（SDL=y）全绿。最终交付经制品仓 sdl2 接入回到 SDL=y 同形后该面自动恢复（见关联草稿）。

## 根因

1. **env 文件里的主机特性门控**：`board/sandbox/sandbox.env` 中把键盘加入 stdin 多路复用列表的条目位于 `#ifdef CONFIG_SANDBOX_SDL` 内：
   ```
   stdin=serial
   #ifdef CONFIG_SANDBOX_SDL
   stdin+=,cros-ec-keyb,usbkbd
   #endif
   ```
   无 SDL2 宿主上该条目整条消失 → 编译进二进制的**默认环境** stdin 只剩 `serial`。这不是 defconfig 开关问题：`CONFIG_SANDBOX_SDL` 由 Kconfig `depends` 收敛，env 文件的 `#ifdef` 与之独立——"环境文件的 #ifdef 门控与 defconfig 开关是两套独立事实"。
2. **键盘进 stdin 名单的第二步被门控短路**：`common/usb_kbd.c` 的 `probe_usb_keyboard()` 分两步——(a) `stdio_register()` 注册名为 `usbkbd` 的 stdio 设备；(b) `strstr(env_get("stdin"), "usbkbd")` 为真才调用 `iomux_doenv(stdin, stdinname)` 重跑多路复用指派。第 (b) 步的字符串门恒假 → 键盘**已注册但永不进 `console_devices[stdin]`**。
3. **tstc() 只轮询 stdin 名单**：`tstc()` 遍历 `console_devices[stdin]` 逐设备调 testc；`usb_kbd_testc()` 从未被调用，emul 里注入的 scancode 无人读取 → 断言必败。同理 `getc()` 等一切 stdin 路径失效——这不只是测试问题，非 SDL 宿主的交互式键盘输入面整体丢失。

## 修复方案（最终态：回上游同形优先）

该问题的正解不是改 env 文件，而是让构建回到上游 CI 同形配置：

**① 首选（本交付最终态）**：接入制品仓 sdl2 依赖（`conanfile.py` 增加 `self.requires("sdl2/2.30.10")` + PATH/SDL_CONFIG/KCFLAGS 三件套接线，详见 DRAFT-11418-uboot-sandbox-sdl2-registry-dep）→ `CONFIG_SANDBOX_SDL=y` → sandbox.env 的 `#ifdef CONFIG_SANDBOX_SDL` 分支自然命中，`stdin+=,cros-ec-keyb,usbkbd` 回归，`dm_test_usb_keyb` 无需任何补丁全绿；连带收益：一切"配置形态相关"行为与上游 CI 逐字节同形。

**② 备选（确无 SDL 可用时，本交付初版曾采用、后退役）**：`board/sandbox/sandbox.env` 的 SDL 分支之外补 USB_KEYBOARD 分支：

```diff
 stdin=serial
 #ifdef CONFIG_SANDBOX_SDL
 stdin+=,cros-ec-keyb,usbkbd
+#elif defined(CONFIG_USB_KEYBOARD)
+stdin+=,usbkbd
 #endif
```

- SDL 构建（上游 CI）行为逐字节不变；非 SDL + `CONFIG_USB_KEYBOARD=y` 构建恢复与上游 CI 等价的键盘输入面（cros-ec-keyb 属 EC 配件面，不随本分支引入）。
- 保留门控语义正确性：门控的应是"宿主能力/配件通道"（SDL 特有的 cros-ec-keyb/usbkbd 组合），usbkbd 本身只依赖 `CONFIG_USB_KEYBOARD`。

## 验证

1. **KDBG 仪器化（定位）**：对 `usb_kbd.c` 的 probe/register 与 `usb-uclass.c` 的匹配路径加打印，普通启动 `usb start; coninfo` 全链正常：
   `KDBG usb_init cold` → `KDBG usb_match bus=1 dev=4 drv=usb_kbd` → `KDBG kbd_probe` → `KDBG puk registered` → **`KDBG puk stdin='serial'`**（唯一断点：名单不含 usbkbd）。
2. **setenv 反向验证（同二进制）**：`u-boot -d test.dtb -c "setenv stdin serial,usbkbd; ut dm dm_test_usb_keyb; exit"` → live+flat 两遍全过（`failures: 0`）；对照组（不 setenv）失败 :449。证明修复点唯一且充分。
3. **最终态闭环（制品仓 sdl2 接入，回 SDL=y 上游同形）**：默认 env 下真机全量逐子测试 919/919 全绿（`dm_test_usb_keyb` 在内），`printenv stdin` 含 usbkbd。初版 #elif 路径亦曾端到端验证（干净重建 + 仅该变更 → 默认 env 下 `ut dm dm_test_usb_keyb` `failures: 0`）——两条路径均可修复，最终取"上游同形"以保测试面全额回归。

## 教训 / 泛化

- **"上游 CI 的绿"只覆盖 CI 自己的配置组合**：env/config 文件里的主机特性 `#ifdef` 使不同宿主构建出不同默认环境，测试面随之静默增减且零告警。triage 第一步应 diff"CI 构建配置 vs 本地构建配置"在 env/Kconfig 上的差集；修复取向优先"回到上游同形"（补依赖/补配置），自造补丁是次选。
- **"已注册"与"已进名单"是两件事**：console 设备注册（stdio_register）与 stdin 多路复用指派（iomux_doenv）分离，中间夹一个 env 字符串门——排查输入类问题时先读 `printenv stdin` 与 console 设备表，再怀疑驱动。
- **ut 框架会吸收测试体内的 console 输出**：`test_pre_run` 阶段的打印可见，测试体内部的打印不可见；由"日志无某打印"推断"该代码未执行"会误判分支（本项实踩：曾据此误判 `usb_init()` 提前返回，实际是输出捕获假象）。需要在测试路径中取证时，改用可观测状态（env、设备表、返回值）而非 printf。
