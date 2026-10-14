# sng — Scriptable Network Graphics

sng 把 PNG 与可编辑的文本描述（SNG 语言）互相转换：`sng < image.png` 把 PNG 的各个 chunk 反编译成文本，
`sng < image.sng` 把文本编译回 PNG。颜色可以写 RGB 三元组或 X11 颜色名（如 `"dark slate gray"`），
颜色名通过 `rgb.txt` 解析。上游为 Eric S. Raymond 维护，3 个 C 文件，手写 Makefile，依赖 libpng（→ zlib）。

## OHOS 适配要点

- 只构建 `sng` 目标：默认 `all` 还会调 asciidoctor 生成 man/HTML，构建机上没有；改装包内预渲染的 `sng.1`
- 手写 Makefile 把 `LDFLAGS` 写死为 `-lpng`，会丢掉 Conan 依赖的 `-L`；配方把 Conan 生成的 LDFLAGS 放到 make 命令行
- 颜色表：`RGBTXT` 编译期写死（默认 `/usr/share/X11/rgb.txt`），缺文件时 `sng` 直接 fatal；
  配方依赖已发布的 `rgb/1.1.1`，把其 `rgb.txt` 复制进本包 `share/X11/rgb.txt`，`RGBTXT` 指向该文件
- 上游回归脚本 `sng_regress` 硬编码 `/tmp`（OHOS 只读）和 `diff -c`（toybox 无 `-c`），按最小补丁改为 `$TMPDIR` / `diff -u`
- OHOS 内核拒绝未签名 ELF：`sng` 用 `binary-sign-tool` 自签
