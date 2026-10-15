# 适配"缺件"先查平台制品仓：sandbox SDL 测试面 = 制品仓 sdl2 依赖 + PATH/SDL_CONFIG/KCFLAGS 三件套接线（OHOS 另配同名 ELF 包装器消解脚本 execve；替代自写存根/降级裁剪）

- **草稿 ID**: DRAFT-11418-uboot-sandbox-sdl2-registry-dep
- **来源**: u-boot 2026.07 HarmonyOS PC 适配（OHOS 无系统 SDL2；初版自写 headless 存根驱动保 bootstd 菜单类测试，经审查指出平台制品仓已有适配 sdl2 → 改为制品仓依赖接入，上游原生 sandbox_sdl 驱动与全部 SDL 门控测试面回归）
- **分类**: sandbox / kconfig / dependency-registry / porting
- **状态**: 本地草稿（路径 B 知识库扩展申请中）
- **关联**: 与 DRAFT-11418-uboot-sandbox-env-sdl-gated-stdin 同源（同一"无 SDL2 构建偏离上游配置形态"背景：一个丢 stdin 键盘测试面、一个丢 video/cedit/expo 测试面；后者的正确修复即本草稿的接入方案）

## 问题 / 错误签名

- sandbox 目标构建"成功"但 SDL 门控测试面整体静默消失：`test/dm/video.o`、`test/boot/{cedit,expo}.o` 不参与构建（test/dm/Makefile `obj-$(CONFIG_VIDEO_SANDBOX_SDL) += video.o`；test/boot/Makefile 以 CONFIG_VIDEO_SANDBOX_SDL 门控 expo.o/cedit.o），`test/pairs.txt` 无 `dm_2_dm_test_video_base` 行，`u-boot.sym` 无 video/cedit/expo 套件符号。
- 下游可见故障：bootstd 菜单类 6 子测试在 `uclass_first_device_err(UCLASS_VIDEO)` 处 -ENODEV（上游唯一 sandbox LCD 驱动即 SDL 驱动）。
- 复现：无系统 SDL2 的宿主（OHOS）直接构建必现；上游 CI（SDL=y）全绿——同一源码、不同宿主，测试面静默增减且零告警。

## 根因

1. **Kconfig 探测链**：`HOST_HAS_SDL`（arch/sandbox/Kconfig）`def_bool $(success, sdl2-config --version)`——探针在 Kconfig 解析期执行，要求 `sdl2-config` 在 PATH；`SANDBOX_SDL default HOST_HAS_SDL`；`VIDEO_SANDBOX_SDL depends on SANDBOX_SDL`（drivers/video/Kconfig）。探针失败 → syncconfig 按 depends 静默收敛为 n → SDL 门控的驱动与全部测试面整片消失，构建零告警（"构建成功"不蕴含测试面在位）。
2. **误判路径（本项实踩）**：把"宿主无系统 SDL2"当成"必须自写存根/裁面"——实现 headless 存根驱动自担渲染路径，40 项 SDL 门控子测试被裁。正确第一步：**查平台制品仓**（本平台 conan 远程 `ohpcd`）——`conan list "sdl2/*" -r ohpcd` 即见 `sdl2/2.30.10`（OHOS aarch64 静态适配，含自定位 `sdl2-config`）。平台生态内常见宿主库多数已有适配构建，制品仓优先于自造。

## 最小修复方案（三件套接线）

```python
# conanfile.py
def requirements(self):
    self.requires("sdl2/2.30.10")

# build()：sandbox defconfig 与主构建两次 make 调用共享同一 env
sdl2_pkg = self.dependencies["sdl2"].package_folder
sdl_env = (
    f'PATH="{sdl2_pkg}/bin:$PATH" '                 # ① Kconfig 探针命中（决定性开关）
    f'SDL_CONFIG="{sdl2_pkg}/bin/sdl2-config" '     # ② 链接 -L/-l 自定位
    f'KCFLAGS="-I{sdl2_pkg}/include" '              # ③ <SDL2/SDL.h> 包含路径
)
```

1. **PATH 前置 `<pkg>/bin`**：满足 Kconfig 解析期 `$(success, sdl2-config --version)` 探针——决定 `SANDBOX_SDL` 生死的开关，且探针失败是静默的。
2. **`SDL_CONFIG` 钉到包内脚本**：arch/sandbox/config.mk `SDL_CONFIG ?= sdl2-config` 的覆盖位；脚本自定位 prefix，`--libs` 给出 `-L<pkg>/lib -lSDL2` 供链接。
3. **`KCFLAGS="-I<pkg>/include"`**：`sdl2-config --cflags` 只输出 `-I<prefix>/include/SDL2`，而源码以 `<SDL2/SDL.h>` 形式包含——`-I<pkg>/include` 才是匹配路径（顶层 Makefile 将 KCFLAGS 并入 KBUILD_CFLAGS；syshdrs 文件规则自动把 `-I` 转 `-idirafter`，不扰动 libc 头优先级）。

接入后：上游原生 `sandbox_sdl` 驱动参与构建，bootstd 菜单类与 SDL 门控测试面全额回归；上游同形带来连带收益——`sandbox.env` 的 SDL 门控条目（cros-ec-keyb/usbkbd stdin）等一切"配置形态相关"内容自动回到上游 CI 行为（见关联草稿），自造补丁全部退役（0014 存根、0016 门控解耦随接入删除，补丁数 16→14）。

**OHOS 第二层障碍（命令式调用的脚本 execve）**：①②都以「命令」形式调用 sdl2-config——①是 Kconfig 解析期 popen 经 /bin/sh 的 PATH 查找，②是 config.mk 的 `$(shell $(SDL_CONFIG) --cflags/--libs)`——内核须直接 execve 脚本本体，而 OHOS 无 binfmt_script 恒 EACCES（探针仍静默 n，真机 .config 实证 SANDBOX_SDL 未置位；`sh sdl2-config` 写法亦不可行：busybox sh 对 `<script>` 操作数不做 PATH 查找）。①在 Kconfig 属上游文字、②是 Makefile 默认值，均不可改写 → 配方层编译同名 ELF 包装器（`_sdl2_config_shim`）：包装器 `execv("/bin/sh", ["sh", <真脚本全路径>, ...])` 由 sh 打开脚本执行，置 PATH 前位并钉进 SDL_CONFIG，构建期冒烟 `--version`。真机验证：包装器就位后探针翻 y（`CONFIG_SANDBOX_SDL=y`/`CONFIG_VIDEO_SANDBOX_SDL=y`）。详见 DRAFT-11418-uboot-ohos-no-script-execve。

**headless 安全性**：SDL 进构建 ≠ 需要显示——`show_lcd` 默认 false，上游 CI 本身就是 SDL=y headless 形态，测试全程无显示依赖。

## 防静默收敛守卫

探针失败无声（构建仍"成功"），交付侧必须硬锚校验：`test_package/test_uboot.sh` 第 0d 步以 `dm_2_dm_test_video_base` 锚定 `pairs.txt`（该用例上游无编译条件、随 video.o 同进同出——面在则链接器符号必在，面丢则 grep 必败），把"SDL 测试面被静默裁掉"变成显式失败。

## 验证

- 接线分层验证（2026-10-10 真机）：三件套（无包装器）下探针必败且静默——`sh -c 'sdl2-config --version'`（即 Kconfig `$(shell,...)` 的 popen 形态）真机直测 `Permission denied` rc=126、构建树 `.config` 实查 SANDBOX_SDL 未置位（复现命令在案）；「依赖解析成功 + 工具在 PATH」不蕴含命令式调用可用；ELF 包装器就位后 arch/sandbox/Kconfig 探测翻 y、`CONFIG_SANDBOX_SDL=y`/`CONFIG_VIDEO_SANDBOX_SDL=y` 落 .config（详见 execve 草稿）。
- 真机 `conan create` 全链（包装器就位版）：`CONAN_CREATE_RC=0`，总耗时 4826 秒；test_package 四步全过（10 项产物 + 5 工具冒烟 + 固件 + 第 0d 步 SDL 面在位校验），逐子测试 919/919（相对无 SDL 口径 879 净增 40 项 SDL 门控面：dm 视频套件 + cedit 6 + expo 8），`=== All tests passed ===`。
- 官方 conan-verify 八门禁 Verdict: PASS（2026-10-10 复跑）。

## 教训 / 泛化

- **适配"缺件"的第一反应：查平台制品仓**（`conan list -r <remote>`），再谈存根/降级。自造路径的双重代价：白工 + 与上游分叉（测试面被裁是隐性损失，事后才显形）。
- **Kconfig `$(success,...)` 探针类开关的失败是静默的**：syncconfig 按 depends 收敛、构建照常成功——"构建成功"不能作为测试面在位的证据，必须以符号/清单级硬锚（链接器列表符号、子测试清单）校验。
- **宿主库接线的三个接口各自独立**：PATH（解析期探针）、SDL_CONFIG（链接期旗标，含覆盖位）、KCFLAGS（源码包含路径形式）——缺一即断，且断点分布在"解析期静默 / 编译期 / 链接期"三个不同阶段，排查按阶段对号。
- **宿主工具接线的隐藏第四接口——「命令式调用」的执行语义**：探针与 `$(shell)` 走的是 PATH 命令查找（进程 execve），不是「文件存在性」；宿主无脚本 execve 时，工具就在 PATH 里也全灭且探针静默。接线的完备验证=构建期真实调用一次（包装器冒烟 `--version`），而非只核 PATH/文件。
