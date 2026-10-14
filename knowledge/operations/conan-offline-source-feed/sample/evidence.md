# 样例证据：japa 0.9.4 离线源喂包实测（2026-10-13）

## 环境

- conan 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`
- 源码包: `https://kokkinizita.linuxaudio.org/linuxaudio/downloads/japa-0.9.4.tar.bz2`，内容 sha256 `b7dc2566bfa9139bbac93a404d60d0b1e0bfadfe1315bb46d17f6d9d376407c2`
- 复现脚本: `repro.sh`（日志重定向文件，无管道 head）

## 阶段 A：不启用方案（实测三连失败）

### A1. 残留 download_urls 指向死端口（japa-create1.log）

```
japa/0.9.4: Checking backup: http://127.0.0.1:8731/
ERROR: japa/0.9.4: Error in source() method, line 76
	get(self, **self.conan_data["sources"], strip_root=True)
	NotFoundException: Sources for https://kokkinizita.linuxaudio.org/.../japa-0.9.4.tar.bz2 not found in remote backup http://127.0.0.1:8731/
```

### A2. file:// scheme（japa-create2.log）

```
japa/0.9.4: WARN: network: Error downloading file file:///storage/.../japa-dl/b7dc...c2:
'No connection adapters were found for 'file:///storage/.../japa-dl/b7dc...c2''
```

### A3. file:// 改 http 但缺 .json 元数据（japa-create3/create4.log）

sha256 文件已可 `curl -I` 200，conan 仍报：

```
ERROR: japa/0.9.4: Error in source() method, line 76
	NotFoundException: Sources for ... not found in remote backup http://127.0.0.1:8732/
```

根因（conan 2.29.1 源码 `conan/internal/rest/caching_file_downloader.py:104-107`）：

```python
self._file_downloader.download(backup_url + sha256, download_path, ...)
self._file_downloader.download(backup_url + sha256 + ".json", download_path + ".json", ...)
```

—— **sha256 包与 .json 元数据必须成对提供**，缺 json 整体按 NotFoundException 判负。

## 阶段 B：启用方案（japa-create5.log，RC=0）

修复动作：

```sh
# 1. 源码包按内容 sha256 命名 + 成对 json（references 指回官方 URL）
cp japa-0.9.4.tar.bz2 <dir>/b7dc...c2
printf '{"references": {"japa/0.9.4": ["<官方URL>"]}, "timestamp": 1760322000}' > <dir>/b7dc...c2.json
# 2. 本地 http.server 服务该目录
python3 -m http.server 8732 --bind 127.0.0.1 --directory <dir>
# 3. download_urls 指向 http://127.0.0.1:8732/（不用 file://）
```

结果：

```
JAPA_SMOKE_PASS load=2 process=1 skipped=3 failed=0
RC=0
```

## 结论

- 命中共性：backup 源 sha256+json 成对要求 + file:// 无 adapter + TEMP 配置残留，三条全部在 japa 适配中实测复现并修复。
- 方案（HTTP 喂源 + 成对元数据）使 conan create 从 source() 阶段三连失败变为全流程通过。
- 该问题与具体三方库无关：任何 `source()` 需要拉包、且处于离线/弱网环境的适配任务都可能命中。
