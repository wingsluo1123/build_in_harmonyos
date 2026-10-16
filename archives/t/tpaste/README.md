# tpaste

`tpaste` 是把标准输入粘贴到 <https://tpaste.us> 的单行 POSIX sh 脚本，实际工作由 `curl -sSF 'tpaste=<-'` 完成：

```sh
echo hello | tpaste      # 输出粘贴后的 URL
```

## 源码来源

tpaste 没有独立的上游发布包。0.8 是 Alpine Linux 包版本：脚本由 aports 中
`main/tpaste/APKBUILD` 的 `package()` 用 `printf` 生成（许可证 GPL-2.0-only，运行依赖 `curl`）。

- 官方出处（固定 commit）：<https://gitlab.alpinelinux.org/alpine/aports/-/blob/3f28b79bb6e626953e3786be38349719ebd1789d/main/tpaste/APKBUILD>
- 配方下载同一 commit 的 `APKBUILD`（GitHub 上的官方只读镜像 `alpinelinux/aports`，内容 sha256 与 GitLab 一致；
  gitlab.alpinelinux.org 对 Conan 的 User-Agent 返回 418），并校验 sha256；
  构建时按其 `package()` 模板生成脚本。

## HarmonyOS PC 适配

- 脚本与架构无关，没有补丁，无需交叉编译；产物为 `bin/tpaste`（mode 755）。
- 运行依赖 `curl/8.15.0`（Conan `requires`）。
- 依赖外部 HTTPS 服务 tpaste.us：服务可用性不在适配范围内，消费者用例使用假 curl，不访问网络。
