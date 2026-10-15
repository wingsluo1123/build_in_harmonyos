# E8741 — npm 分发的单文件 bash 脚本被 lang-preflight 判为 nodejs

## 错误特征
```
detected_language: nodejs
language_evidence: build_system=npm, manifest="package.json 含 main/scripts/engines/bin", source_stats="无源文件可统计"
```
默认任务语言 `cpp` 时，`lang-preflight` 会据此自动写 `env_unsupported` 终态（exit 2）。

## 触发条件
- 源码仓库只有一个无扩展名的 bash 脚本（如 `xcv`，首行 `#!/bin/bash`）、`README.md`、`package.json`；
- `package.json` 含 `bin` 键（仅为 npm 分发而写），没有任何 JS 源码；
- 阶段：适配开工前的语言预检（R47）。

## 根因分析
`lang_detect._manifest_scan` 只要 `package.json` 含 `main/scripts/engines/bin` 之一就判 `nodejs/npm`。
源码统计 `_EXT_LANG` 仅按扩展名归类（`.sh`/`.bash`→bash，且 bash 本来就不计入主体占比），
无扩展名的 bin 脚本统计为空，没有任何信号能纠正 manifest 的判断。

## 解决方案

### 推荐方案
1. 只读预判：`detect_language(<src>)` 记下输出；`head -1` 脚本确认 shebang，`find` 确认无 JS 源码；
2. 以检测器判定值显式声明任务语言再跑预检：`lang-preflight <软件> <版本> --src <src> --lang nodejs`，放行后继续适配（大赛接受 Shell 库）；
3. 把只读输出与 Shell 依据写入 `notes.md`，在 SKILL_FEEDBACK 记录检测器缺陷。
默认口径若已误写 `env_unsupported`：最终回执用 `result … --force` 覆盖，并在 `--summary` 里说明是语言预检误落终态。

### 禁止做法
- ❌ 伪报 `--lang cpp`（违反如实申报）；
- ❌ 以“语言不是 C/C++”为由上报 `env_unsupported` 收手（Shell 适配被大赛接受）。

## 验证
```bash
python3 -c "import sys; sys.path.insert(0,'scripts'); from ohc.lang_detect import detect_language; print(detect_language('<src>'))"
head -1 <src>/<脚本>      # #!/bin/bash
```

## 关联条目
- 相近草稿：DRAFT-libok-0.6.5-langpreflight-clib-packagejson-misdetect（C 库 + package.json scripts），
  DRAFT-dshlibs-0.109-lang-preflight-pure-script-package-misdetect（bash 包 + install-only Makefile 判 c）。
  本条差异：触发信号是 package.json 的 `bin` 键 + 无扩展名脚本，导致判 nodejs 且统计为空。
