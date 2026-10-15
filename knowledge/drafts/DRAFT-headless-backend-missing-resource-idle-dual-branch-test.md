# headless/null 后端构建改变"缺资源报错"语义：test_package 无资源断言的双分支 + 有界超时设计

> 对应 KV：`knowledge/drafts/DRAFT-headless-backend-missing-resource-idle-dual-branch-test.kv`
> 实证来源：xroar 1.11 真机 shadow CI r8（2026-10-13）

## 一句话

同一个上游程序在"完整 UI 构建"与"headless/null 后端构建"下，**缺资源（ROM/
数据文件/设备）时的行为可以完全不同**：完整构建走"报错退出"，headless 构建
可能**绕过报错路径直接进入主循环空转**——按"应非零退出并打印错误"写的
test_package 断言会在 CI 上以超时假失败。无资源断言必须写成**双分支**并对
空转分支用**有界超时**观察。

## 使用说明

1. **识别风险形态**：上游有多种 UI/后端（null/dummy/stub 模块）且我们为
   OHOS 选了 headless 后端；main 流程里"资源加载失败 → 打印错误 → exit"的
   分支位于**依赖后端回调**的代码之后。
2. **设计断言**（消费者测试）：
   ```python
   try:
       r = run(bin, [], stdin=subprocess.DEVNULL, timeout=T, capture_output=True)
   except subprocess.TimeoutExpired:
       ok("headless 后端下进入空转（有界观察 T 秒）——核心已链接")
   else:
       out = (r.stdout or "") + (r.stderr or "")
       assert r.returncode != 0 and KEYWORD in out.lower()   # 完整构建分支
   ```
   - **stdin 一律 DEVNULL**：空转型主循环可能在读 stdin。
   - T 取短值（10–30s）：该分支的语义只是"核心已链接并能进入主循环"，
     不是功能测试。
3. **不许的做法**：把空转超时当测试失败（假阴性）；也不许因此删除断言、
   改用 readelf/字符串扫描冒充执行（违反 R34/L1e，会被破坏性反向验证抓出）。
4. **保持 L1e 可过**：断言整体仍必须真实执行被测产物——--version/--help/
   启动路径断言保留，破坏 bin/<exe> 后测试必须 rc!=0。

## 与既有草稿的区分（查重记录）

- `DRAFT-6380-nuvie-0.5-headless-interactive-binary-assertions`：nuvie 解决
  "上游**没有** --version/--help，如何找一条必然到达且自行退出的执行路径"
  （初始化失败早期 return）。本条解决"上游**有** CLI 入口、断言也过了，但
  **无资源裸运行**的语义随后端构建形态改变"——是已有 --version/--help 断言
  之外的第二条断言怎么写的问题。两者互补：nuvie 型入口选择用其法，无资源
  断言用本条双分支。
- `DRAFT-ohos-pytest-timeout-thread-method-destroys-run`：讲 pytest 超时实现
  机制，不涉及语义双分支。
- xcolmix/clipboard_lite 等 headless 草稿：各自 case 的入口选择，不含
  "同一断言跨构建形态语义漂移"的通用化表述。

## 适用范围

- 模拟器/游戏/多媒体等"主循环型"程序，为 CI 打 headless/null 后端包时。
- 任何"缺资源行为依赖 UI 后端"的消费者测试设计（缺 ROM、缺字体、缺配置
  文件、缺显示设备）。
- 不适用：上游对缺资源在所有构建形态下都硬退出（无需双分支）。

## 输入 / 输出

- 输入：被测包 bin 路径；上游 main 流程中资源失败分支与后端的关系（源码
  阅读 10 分钟）；CI 单测超时预算。
- 输出：test_package 中"无资源裸运行"断言的双分支实现（报错分支 + 有界
  空转分支）；MANIFEST.yml 中对该断言语义的说明文字。

## 示例（xroar 1.11 实测）

```
r8：`xroar`（无参数）在 null-UI 构建下不报 ROM 错误，60s 超时
    → test_package 失败（假阴性：核心其实已链接）
r9：改为双分支 + stdin=DEVNULL + timeout=20：
    OK: bare run idles without ROMs (headless null-UI behaviour)
    conan create exit=0，5/5 断言；L1e 模拟（删 bin/xroar）rc=1 通过
```

## 验证命令

```sh
python3 test_xroar.py <package>/bin   # 5/5 assertions；破坏产物后 rc=1
```
