# conandata.yml 用 SourceForge `/…/download` URL 会让 conan get() 报 BadZipFile

> Draft: `DRAFT-SOURCEFORGE-DOWNLOAD-REDIRECT-URL-BADZIPFILE-IN-CONAN-GET`
> Stem: `sourceforge-download-redirect-url-badzipfile-in-conan-get` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-SOURCEFORGE-DOWNLOAD-REDIRECT-URL-BADZIPFILE-IN-CONAN-GET
- **严重度**: 2
- **类别**: source|conan-recipe|networking
- **触发工具**: conan
- **阶段**: source

## 错误特征

```
gocr/0.50pre-patched-2: Calling source() in /…/p/gocr…/s
gocr/0.50pre-patched-2: Sources correctly downloaded from https://sourceforge.net/projects/osra/files/gocr-patched/gocr-0.50pre-patched-2.tgz/download
gocr/0.50pre-patched-2: Uncompressing download to .
ERROR: gocr/0.50pre-patched-2: Error in source() method, line 90
	get(self, **self.conan_data["sources"], strip_root=True)
	BadZipFile: File is not a zip file
```

## 根因分析

`conan.tools.files.get()` 依据 URL 的 **basename** 推断压缩格式。SourceForge 文件页给出的
`…/files/<path>/<file>.tgz/download`，basename 是 `download`（无扩展名），conan 无法识别为 tar，
于是走 zip 分支 → `BadZipFile`。

日志中 "Sources correctly downloaded" 已经出现，说明下载本身没问题——
这是**格式判定**失败，不是网络/校验问题。

## 推荐方案

**方法**: `use-direct-sourceforge-download-host-with-extension`

```yaml
sources:
  # ✅ 官方直链主机，保留 .tgz 扩展名（sha256 与原 URL 相同）
  url: "https://downloads.sourceforge.net/project/osra/gocr-patched/gocr-0.50pre-patched-2.tgz"
  sha256: "3ff73f03845878a4f08585b25d1e2b690e3f2d03bb4df1bbebb2ae2ead25287a"
```

- `downloads.sourceforge.net` 是 SourceForge 的官方下载主机，不属于 R39/PF7 禁止的第三方代理域（gh-proxy / ghfast / cnb.cool 等）。
- 若确实只能拿到无扩展名 URL，则在 `source()` 里显式 `download(self, url, filename)` 再用 `unzip`/`untar`，
  不要依赖 `get()` 的格式推断。

## 验证

```bash
$ python3 -c "import urllib.request as u;print(u.urlopen('https://downloads.sourceforge.net/project/osra/gocr-patched/gocr-0.50pre-patched-2.tgz').status)"
200
$ conan create archives/g/gocr/0.50pre-patched-2 -pr:h=ci/conan/profiles/ohos-aarch64 …
gocr/0.50pre-patched-2: Uncompressing gocr-0.50pre-patched-2.tgz to .
（后续 configure/make 正常）
```
