# E429 — CI 预下载把 conandata.yml 注释里的裸 URL 当第二个源码，并污染 sources.url

## 错误特征

本地 CI（`ci/conan/build_and_test.sh`，`finish` 的 W3 步骤内执行）报：

```
ERROR: verhaal/025: Error in source() method, line 67
	get(self, **self.conan_data["sources"], strip_root=True)
	NotADirectoryError: [Errno 20] Not a directory:
	  '…/.build-cache/predl_cache/06d9b097_verhaal/archive/v025.tar.gz'
```

特征：**同一份配方 `conan-verify`（G2 `conan create`）通过，但本地 CI 的
`conan create` 失败**；报错路径形如
`predl_cache/<hash8>_<basename>/<原 URL 的其余路径>`，且该路径在磁盘上是一个
**文件**（不是目录）。

## 触发条件

- 构建系统: 任意（与配方无关，纯 CI 侧行为）
- 阶段: `source()`（W3/本地 CI 的 Pre-download 之后）
- 前提：`conandata.yml` 的**注释**里出现了完整的 `http(s)://` URL，
  且该 URL 是 `sources.url` 的**前缀**

## 根因分析

`ci/conan/build_and_test.sh` 的预下载逻辑分三步：

1. 用宽松正则扫描 **整个 conandata.yml 全文**（不区分注释/字段）：
   `(?:^|\s)(?:url:?\s*)?["\']?-?\s*(https?://[^\s"\']+)`
   注释行里的裸 URL 也会被当作一个「源码 URL」命中。
2. 对每个命中 URL 下载，缓存为 `predl_cache/{md5(url)[:8]}_{basename}`，
   然后做**字符串替换**：`content.replace(url, 'file://' + local_path)`。
3. 若某一命中 URL 是 `sources.url` 的前缀（典型：注释写上游首页
   `https://host/user/repo`，而源码是 `https://host/user/repo/archive/v1.tar.gz`），
   短 URL 先被替换，长 URL 的前半段随之变成
   `file://…/{hash8}_repo/archive/v1.tar.gz` —— 指向一个**不存在的目录路径**，
   conan `get()` 遂抛 `NotADirectoryError`。

本例：注释 `# 上游官方源: https://git.sr.ht/~gregkh/verhaal (tag v025, …)`，
命中并缓存为 `06d9b097_verhaal`，把真实 tarball URL 污染成
`file://…/06d9b097_verhaal/archive/v025.tar.gz`。

注意 `finish` 的 trap 在退出时会把 conandata 还原为官方 URL，
所以**事后直接看 conandata 是看不出来的**，只能从 W3 日志定位。

## 解决方案

### 推荐方案

`conandata.yml` 的注释中**不写完整 http(s) URL**，改为无 scheme 的摘要写法：

```yaml
# conandata.yml — verhaal 025
# 上游官方源: git.sr.ht/~gregkh/verhaal (tag v025)     ← 无 scheme，不被正则命中
# R39/PF7: 只写上游官方源 URL，镜像回退由 CI 自动处理

sources:
  url:
    - "https://git.sr.ht/~gregkh/verhaal/archive/v025.tar.gz"   ← 唯一完整 URL
  sha256: "269584a5…"
```

自检：`grep -nE 'https?://' conandata.yml` 应**只命中 sources.url 那一行**。

### 禁止做法

- ❌ 修改 `sources.sha256` / 缩短 URL 迁就正则（改错了对象，预下载行为不变）
- ❌ 用 `--no-preflight` / 跳过 W3 绕过（W3 是阻塞门禁，跳过等于不带验证建 PR）
- ❌ 直接手改 `predl_cache` 内的缓存文件（下次 run 仍会被重新污染）
- ❌ 只在本地删掉 `.build-cache/` 重跑（治标；注释里的 URL 仍在）

## 验证

```bash
# 1) conandata 中只剩唯一官方 URL（无注释裸 URL）
grep -nE 'https?://' archives/<l>/<pkg>/<ver>/conandata.yml

# 2) W3 本地 CI 通过（不再出现 predl_cache 目录路径报错）
ohc-run.py finish <pkg> <ver> published      # → .ci-result.json exit_code=0
```

## 关联条目

- 相关: E434（PF9 软件级路径已知误报，同属「CI/门禁与归档布局的口径差异」）
- 相关: R39/PF7（conandata 只写官方源 URL）
