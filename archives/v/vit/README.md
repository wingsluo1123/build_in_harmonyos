# vit

Taskwarrior 的全屏终端界面：任务列表浏览、按项目/标签/日期筛选、快捷键操作，支持自定义主题与列。
上游：<https://github.com/vit-project/vit>

| 版本 | 说明 |
|------|------|
| [2.3.4](2.3.4/notes.md) | 当前适配版本（HarmonyOS PC / ohos-aarch64） |

## 这个包提供什么

- `bin/vit` —— 命令行入口（`vit --help` → `usage: vit [options] [report] [filters]`）
- `python/vit/` —— 界面、格式化器与颜色映射等模块；随包依赖 tasklib、urwid
- `licenses/LICENSE`

## 适配要点（细节见 2.3.4/notes.md）

1. **补丁 0001（可移植性）**：上游 `vit/util.py` 在**导入期**无条件调用 `curses.setupterm()`，
   无 terminfo 数据库的环境（容器/CI/无终端）会连 `import vit` 都失败 → 补丁改为 try/except 降级为空序列，
   只有真正清屏退化为无操作，**同时修复运行时**。
2. **上游 10 个用例真跑**：`test/` → 本地 `10 passed`（**10/10，100%**）。
3. **消费者校验走真实逻辑**：直接调用 `ListBatcher` 分批与颜色映射两条核心路径，
   而不是只断言文件存在。
4. **运行期**：完整界面需要 `task`（Taskwarrior）提供数据；构建与测试不依赖它。
