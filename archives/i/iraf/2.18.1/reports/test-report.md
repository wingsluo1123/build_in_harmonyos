# IRAF 2.18.1 测试报告

本报告对应源码 `7646521e2988cc49ae145a47569724d56f76b572` 和 W3 run `facfbb4c44c842209dd0479d00662fd9`。
完整 W3 RC0/2081秒，默认3600秒预算；框架和源码绑定见 build-report.md。

## 原始上游

未改 test/run_tests 或 test/*.md。136个独立命令块，加经典CL对cl.md的7次重复，共143次调用。

```text
Test summary: 133 passed, 2 skipped, 1 xfailed
Test summary: 7 passed
```

合计 **140 passed、2 skipped、1 xfailed、0 failed**。
普通有效测试140/140（100%）；完整清单140/143（97.90%），xfail/skip不计passed。
1个故意错误输出示例为上游xfail，1个无限循环和1个macintel选择为上游skip，均保留原oracle。
两条完整summary及总数143由配方检查，超时/缺项/实际failed使构建失败。

## 安装消费者

**16/16场景、33/33检查、0跳过**：22个shell判定、6个生产声明/宏context、5个SSH检查。
真实安装包运行CL/ECL、图像/FITS往返、SPP编译、错误恢复、表数据、tiimage全64像素及保护文件操作。
context直接包含生产头并链接实际libos.a，不在测试端补returns_twice；SSH为本地受控fixture。

```text
PASS 1: installed IRAF version
PASS 2: ECL arithmetic
PASS 3: classic CL arithmetic
PASS 4: image creation and statistics
PASS 5: FITS round trip
PASS 6: installed SPP -> Ratfor -> Fortran -> C -> AArch64 compiler chain
PASS 7: ECL error recovery preserves the following statement
IRAF_CONTEXT=6/6
PASS 8: installed libos production declarations/macros: context status 42, 0 -> 1, and -7
PASS 9: installed compiler propagates a real F2C error
IRAF_SSH_CHANNEL=5/5
PASS 10: SSH stream, stderr, descriptor closure, invalid input and exec errors
PASS 11: compiler -N uses writable scratch and copies the linked program
PASS 12: ECL initialization concatenation uses the VOS temporary directory
PASS 13: tmerge appends all four source values
PASS 14: tiimage copies every pixel of a 2D image into a table array
PASS 15: tiimage rejects a mismatched pixel type
PASS 16: protected files survive deletion until explicitly unprotected
IRAF_CONSUMER_SCENARIOS=16/16 IRAF_CONSUMER_ASSERTIONS=33/33
```

## 重定位与独立缓存

- 安装树复制至新前缀，隐藏原包目录后再次通过16场景/33检查，原目录身份和包摘要恢复不变。
- 仅cache save/restore导入IRAF已构建包；新CONAN_HOME起初没有zlib，--build=never实际安装声明的运行期zlib。
  隐藏整个原构建缓存后，同套16场景/33检查通过，原缓存恢复且包/输入摘要不变。

这两组重复验证不累计到测试总数。SDK编译器和外部依赖保留各自合法位置，未申报整机目录任意搬迁。
24项能力探测回归及历史机制实验另列，不混入143次上游或33项消费者统计。
