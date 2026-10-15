# E429 — 上游 sdist 只发测试代码不发测试数据；且“运行期/测试期依赖”必须按实证判定

## 错误特征
1. 跑上游测试时直接：
   ```
   FileNotFoundError: Can't find pdbs test files in (.../tests/pdbs, pdbs)
   ```
   但 `tests/*.py` 明明都在——**数据目录没随 sdist 发布**。
2. 误判依赖归属：凭“这是科学计算库”就给产物加 `numpy` 运行期依赖，而实际
   `install_requires` 为空、包内模块不 import numpy。

## 触发条件
- 构建系统: 无（纯 Python 包，sdist 安装）
- 阶段: testing（`build()` 内跑上游套件）

## 根因分析
1. **测试数据未进 sdist**：项目常把“测试代码”与“测试数据”分开处理（`MANIFEST.in` 只 include
   包目录），于是 pip 装的 sdist 里 `tests/pdb`、`tests/results` 缺失。测试代码用
   `TEST_DIR / "pdbs"` 之类路径去找数据，缺失即 `FileNotFoundError`——**报错位置在测试代码里，
   根因却在打包**。
2. **依赖归属的直觉陷阱**：propka 的 `setup.py` 只写 `tests_require=["numpy","pytest"]`，
   包内模块不 import numpy；Debian 侧 `debian/control` 用 `python3-numpy <!nocheck>` 标注，
   与之一致。若按“科学计算库=要 numpy”写 `requires`，产物会多一个不必要的运行期依赖。

## 解决方案

### 推荐方案
1. **先量清 sdist 里有什么**：
   ```bash
   tar tzf <sdist> | grep -E 'tests?/' | head
   ls <sdist>/tests/          # 数据目录（pdbs/ results/ testdata/）是否存在
   ```
2. **缺数据就按上游仓库同 tag 归档补齐**：在 `conandata.yml` 的 `test_assets` 里钉死
   `https://codeload.github.com/<owner>/<repo>/tar.gz/refs/tags/<tag>` + **sha256**，
   build() 内取到独立目录、**仅测试用不进产物**；配方里加**守卫**（数据目录不存在就直接
   `ConanInvalidConfiguration`，绝不“没数据也算通过”）。**包产物仍来自 sdist 源码树**，
   并在 manifest/notes/PR 正文如实披露该口径差异。
3. **依赖归属按实证定**：
   - 运行期：读上游 `install_requires`（或 pyproject `dependencies`）+ `grep -rl 'import <dep>' <pkg>/`；
   - 测试期：读 `tests_require` / `extras["test"]`；
   - 交叉验证：发行版打包元数据（Debian 的 `<!nocheck>` 标注 = 仅在测试时需要）。
4. 测试期依赖走 pip 到 `<build>/test-deps`（**不进产物**），**平台私有源优先**（原生扩展需要
   OHOS 架构轮子）+ 每源重试 1 次。

### 禁止做法
- ❌ 缺测试数据就断言“上游测试跑不了/放弃该库”（先对照上游仓库，多半只是没打进 sdist）
- ❌ 为了让测试“能跑”而伪造数据或跳过依赖数据的用例
- ❌ 凭库类别往产物里塞运行期依赖

## 验证
```bash
# 数据是否随 sdist 发布
tar tzf propka-3.5.1.tar.gz | grep -c 'tests/pdb/'     # → 0（缺）
# 运行期是否真的需要 numpy
grep -rl 'import numpy' <sdist>/propka/                 # → 空
grep -n install_requires <sdist>/setup.py               # → 空
# 补齐数据后真跑
PYTHONPATH=<sdist>:<repo-tag>:<test-deps> python3 -m pytest <repo>/tests -q   # → 49 passed
```

## 关联条目
- 相关: E429（同一草稿 id 下的其它适配条目：conan 依赖遮蔽 / test_requires 的 test 上下文 /
  sdist 时间戳归一化 / 离线子集 marker / console_scripts 入口 / src 布局 / Perl 的 make 与 blib）
