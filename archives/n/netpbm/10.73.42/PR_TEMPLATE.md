## 编译信息

- **软件**: netpbm 10.73.42
- **构建系统**: custom-perl（上游 `configure.pl` 为交互式脚本，不支持 `--prefix`）
- **编译日期**: 2026-10-15

## 编译方式

上游 `configure.pl` 为交互式 Perl 脚本，不适合 CI 无人值守调用。配方在 `build()` 内以
上游 `config.mk.in` 为底稿生成 `config.mk` 并追加覆写块（`CC/CXX/LD` 取自 Conan toolchain，
`TIFFLIB/JPEGLIB/PNGLIB/ZLIB` + `*HDR_DIR` 指向 Conan 依赖包，`NETPBMLIBTYPE=unixshared`、
`STATICLIB_TOO=Y`、`OMIT_NETWORK=Y`），随后 `make` + `make package`。

## 制品文件

- `bin/`：353 个条目 / 328 个可执行工具
- `lib/libnetpbm.so.11.73` + dev 软链 `libnetpbm.so` + 静态库 `libnetpbm.a`
- `include/`：`netpbm/pam.h` 等公共头文件
- `misc/`、`man/`

## 启用的可选功能

- 可选图像库：libpng / libjpeg-turbo / libtiff / zlib **全部启用**（PNG/JPEG/TIFF 读写可用）

## 测试验证

- 消费者测试（`test_package/test.c`）：真实调用 `libnetpbm` API 写入并回读 PPM(P6)，
  对 RED 平面逐像素断言，`ctest` 1/1 通过
- 上游官方套件（`test/Execute-Tests` 驱动 115 个 `*.test`）：111 项可测中 106 项通过、
  5 项失败已逐项定性为非本包缺陷（外部可选依赖缺失 / 8 位量化末位差异），4 项由上游判为
  NOT TESTABLE
- 详见表 `reports/test-report.md` 与 `notes.md`「上游测试用例实测（R51 三步法）」

## 提交文件

- `archives/n/netpbm/manifest.yaml`
- `archives/n/netpbm/10.73.42/conanfile.py`
- `archives/n/netpbm/10.73.42/conandata.yml`
- `archives/n/netpbm/10.73.42/manifest.yaml`
- `archives/n/netpbm/10.73.42/notes.md`
- `archives/n/netpbm/10.73.42/test_package/`
- `archives/n/netpbm/commands.json`
- `knowledge/drafts/DRAFT-netpbm-10.73.42-*.{kv,md}`

## 参考

- 上游: https://netpbm.sourceforge.net/

---

Co-authored-by: OpenDesk <opendesk@openharmony.cn>
