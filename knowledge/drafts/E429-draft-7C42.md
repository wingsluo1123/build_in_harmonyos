# E429（草稿）— 以 Alpine APKBUILD 为唯一上游的脚本包（无 tarball）

## 错误特征
- `ohc-run.py init-build tpaste 0.8 --url=<APKBUILD raw URL>` → `解压失败: not a gzip file`
- 直接用 `gitlab.alpinelinux.org/.../-/raw/<commit>/main/<pkg>/APKBUILD` 作 conandata URL，在 Conan 的 User-Agent 下返回 `HTTP Error 418: I'm a teapot`（本机实测 urllib UA 200、`Conan/2.29.1` UA 418）。

## 触发条件
- 构建系统: shell（无构建系统）
- 阶段: init-build / source()
- 软件特征: Alpine 包版本（如 tpaste 0.8），脚本由 `APKBUILD` 的 `package()` 用 `printf` 生成，没有上游发布包。

## 根因分析
1. `init-build` 假定源码是 tar 压缩包，单文件源无法解压。
2. gitlab.alpinelinux.org 的前置反爬对非 curl 的 User-Agent 返回 418（与 E347 同源）。
3. 这类包的"源码"就是 APKBUILD 本身，Alpine distfiles（E335 的方案）里没有对应文件。

## 解决方案
### 推荐方案
- `init-archive <软件> <版本> <url> shell` 代替 `init-build` 建骨架。
- conandata 取 GitHub 官方只读镜像 `alpinelinux/aports` 的同 commit raw 文件（内容 sha256 与 GitLab 一致，本次实测 `5a50dbf2...`），并校验 sha256。
- 配方 `build()` 解析 APKBUILD 的 `pkgver`（必须等于 conan version）与 `url`，按 `package()` 的 printf 模板生成脚本，`sh -n` 语法检查；`package()` 装到 `bin/` 并置 755。
- `test_package` 用确定性的假 curl 做消费者用例，并逐字节比对生成脚本与 `printf` 预期输出。

### 禁止做法
- ❌ 凭记忆手写脚本内容并声称来自上游。
- ❌ 使用个人 fork / 代理镜像作为源。

## 验证
```bash
python3 -c "import urllib.request as u;print(u.urlopen(u.Request('https://gitlab.alpinelinux.org/alpine/aports/-/raw/3f28b79bb6e626953e3786be38349719ebd1789d/main/tpaste/APKBUILD',headers={'User-Agent':'Conan/2.29.1'})).status)"   # 418
conan create archives/t/tpaste/0.8 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 关联条目
- 相关: E347（同域 418，预置下载缓存）、E335（tarball 场景改用 distfiles）、E271（单文件资产被当作压缩包）
