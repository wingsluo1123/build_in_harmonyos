# DRAFT-19001 — 宿主程序脚本插件包/纯数据包形态三方库（非 C/C++ 交付物）选型即止损

> 状态：草稿（knowledge/drafts/，待评审委员会审核 → 主编 `graph promote` 转正式条目）
> 作者：li_shuo <ls.fr@qq.com> · Agent 25DC · 2026-10-15

## 1. 问题模式（解决"一类问题"，非单库 workaround）

大量服务端生态的三方库以**宿主应用程序插件集合 / 静态数据文件**的形式发布：
- jitsi-meet-prosody（Prosody XMPP 服务器的 Lua 插件集，Debian 元包）
- asterisk 的 mod_conf / sounds / moh（音频数据包）
- FreeSWITCH / FusionPBX 的脚本模块
- GNOME Shell 扩展、KDE Plasma widgets 等运行时插件

它们的共同特征（本条目解决的"类"）：
1. **交付物 = 解释型脚本 + 配置/数据文件**，无任何 C/C++ 翻译单元，`conan create` 的"编译"概念不成立；
2. **运行强依赖宿主程序及其解释器生态**（Prosody+LuaJIT、Asterisk 内部 API、LuaRocks 依赖树），CI 环境无宿主运行时，无法执行实质测试（R34/R51 均不可能满足）；
3. **上游常以单体仓库（monorepo）或 Debian 元包形式发布**，主目录语言判定（如 jitsi-meet 主仓的 java/nodejs）与交付物子目录（`resources/prosody-plugins/*.lua`）不一致，容易误导选型。

## 2. 实证案例：jitsi-meet-prosody 1.0.9139

| 项 | 证据 |
|---|---|
| 上游仓库 | `https://github.com/jitsi/jitsi-meet`（tag `jitsi-meet_9139`；**不存在**独立 `jitsi/jitsi-meet-prosody` GitHub 仓库——Debian 包名 ≠ GitHub 仓库名） |
| 交付物 | `resources/prosody-plugins/` 下 67 个 `mod_*.lua` + 7 个 `.patch`；另有 `debian/jitsi-meet-prosody.*` 打包描述 |
| 可编译产物 | `*.c/*.h/*.cpp` 计数 = 0 |
| lang-preflight 判定 | 非 cpp（任务语言 cpp）→ exit 2，自动写终态 `env_unsupported` + `detected_language` + `language_evidence` |
| 结论 | R47：禁止硬着头皮适配；平台按 detected_language 转 `lang_hold` 挂起等生态（非失败） |

## 3. 判定流程（选型阶段，下载源码后立即执行）

```bash
# ① 官方源定位：Debian 包名 ≠ GitHub 仓库名，先确认真实源（R39）
#    jitsi-meet-prosody → github.com/jitsi/jitsi-meet tag jitsi-meet_9139

# ② 插件包特征探测
find $BUILD_SRC_DIR -name "*.lua" -o -name "*.py" -o -name "*.pl" | wc -l   # 脚本主体
find $BUILD_SRC_DIR \( -name "*.c" -o -name "*.cpp" -o -name "*.h" \) | wc -l  # = 0 即无编译面
ls $BUILD_SRC_DIR/debian/*.install 2>/dev/null   # 安装清单全是 /usr/share/、插件目录 → 数据/插件包

# ③ R47 强制语言预检
python3 $SKILL_ROOT/scripts/ohc-run.py lang-preflight <name> <ver> --src $BUILD_SRC_DIR
# exit 2 = 非任务语言 → 终态 env_unsupported，释放任务

# ④ 终态上报（协议 v0.8：detected_language + 三项 evidence 必填，缺失 = PROTOCOL_VIOLATION）
python3 $SKILL_ROOT/scripts/ohc-run.py result <name> <ver> --status env_unsupported \
    --detected-language lua \
    --ev-build-system "无构建系统（无 Makefile/CMakeLists/configure）" \
    --ev-manifest "debian/jitsi-meet-prosody.install 仅安装 *.lua 至 /usr/share/prosody" \
    --ev-source-stats "67 lua + 7 patch + 0 C/C++"
```

### monorepo 判定边界（本次实测的坑）
jitsi-meet 单体仓库含 java（jicofo）/nodejs/lua 多语言子树，`lang-preflight` 按 manifest（build.gradle/pom.xml）判出 `java`。**判定范围应聚焦交付物子目录**（`resources/prosody-plugins/` → lua），但两种判定殊途同归：都非 C/C++ → 终态不变。类似场景（DRAFT-E586 libyal）证明 manifest 判定可能产生假信号——以**交付物安装清单（debian/*.install 或 install 目标）**为最终裁决依据。

## 4. 禁止策略

| 禁止 | 原因 |
|---|---|
| ❌ 语言预检 exit 2 后继续进 conan 主流程（R47） | 无编译步骤可执行，W3/CI 必红，预算白耗 |
| ❌ 伪造 C/C++ stub 测试或空壳 test_package（PF3/R34） | 脚本插件无编译期可验证产物，属伪适配，评审一票否决 |
| ❌ 在 patches/ 中以 `__OHOS__` 宏"激活" Lua 代码（PF5/R8） | 宏对 Lua 无语义，纯装饰性平台标记 |
| ❌ 把 LuaRocks/宿主 Prosody 依赖声明为 conan requires 捎带适配（PF4/R36） | 解释器生态不在 conan 包模型内，下游永远无法消费 |

## 5. 价值与通用性

- **一类问题**：覆盖所有"宿主插件包/数据包"形态三方库的选型判定与止损动作（prosody/asterisk/freeswitch/gnome-shell…），并给出 monorepo 假信号的边界裁决规则；
- **可执行**：特征探测命令 + lang-preflight + result 上报模板可直接照抄；
- ** prescan 联动**：kv 中含 `prescan_pattern`（`mod_*.lua`、`resources/*-plugins/`、`usr/share/` 安装清单特征），promote 后 PreScanner 自动派生 `PSCAN-KB-DRAFT-19001` 规则，立项评估阶段即可命中预警——知识增长即扫描能力增长。
