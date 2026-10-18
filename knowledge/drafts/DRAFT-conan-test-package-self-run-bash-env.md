# DRAFT:conan test_package 的 test() 必须保留 self.run(),Windows 宿主统一走 bash 侧

## 症状(同一根因族的三种面貌:test() 的执行方式与门禁/宿主 shell 不匹配)

### A. 平台 L0d 静态门禁:test() 无 self.run() 即判 stub

```text
类别: 门禁拦截
问题: conanfile.py 的 test() 方法缺少实际测试逻辑
原因: test_package/conanfile.py 的 test() 方法中没有调用 self.run() 执行测试程序。
```

触发案例:yaml-mode 0.0.16 CI #84995(2026-10-12)——test() 用
`subprocess.run([...])` 列表直调消费脚本,本地全绿,CI 在 L0d 直接拦截,
conan-build-test 未执行。

### B. Windows 宿主 + 交叉 profile:self.run() 报两套 env 脚本冲突

```text
ConanException: Cannot wrap command with different envs,
['...\test_package\conanbuild.bat'] - ['...\test_package\conanbuild.sh']
```

profile 里设了 `tools.microsoft.bash:subsystem=msys2` 时,conan 会同时生成
`.bat`/`.sh` 两套聚合 env 脚本;test_package 默认按 cmd 侧执行却要 source
bash 侧脚本,无法择一即抛错。

### C. 用 env= 参数绕开 B 后,症状变为「'.' 不是内部或外部命令」

```text
RUN: D:\...\python.exe D:\...\consumer_ym.py C:\...\p
'.' is not recognized as an internal or external command,
```

命令由 cmd 执行,却套了 bash 风格的 `. <script>` source 前缀,cmd 把 `.`
当命令名。

## 根因

test() 的执行环境由 conan 决定:平台门禁要求它必须经 `self.run()`;而
`self.run` 在 Windows 宿主上的 shell 归属(bash 还是 cmd)与 profile 的
bash 子系统配置、以及 env 脚本的两套变体直接耦合。三者只要不同侧,就以
A/B/C 之一失败——`subprocess` 直调能同时绕开 B/C,却必然撞上 A。

## 定式

```python
class XxxTestConan(ConanFile):
    test_type = "explicit"
    win_bash = True          # 与 profile 的 bash 子系统同侧,消解 .bat/.sh 二选一

    def test(self):
        pkg = self.dependencies["<pkg>"].package_folder.replace("\\", "/")
        py = sys.executable.replace("\\", "/")
        for name in ("consumer_xxx.py", "test_layout.py"):
            script = os.path.join(self.source_folder, name).replace("\\", "/")
            self.run("%s %s %s" % (py, script, pkg))
```

要点:

- `self.run()` 必须保留:平台 L0d 静态门禁按"test() 是否调用 self.run()"
  判 stub,`subprocess` 直调不豁免。(与 `build()` 内的 subprocess 直调不同
  ——那里没有这条门禁,不能把两处结论互相照搬。)
- `win_bash = True` 让命令与 env 脚本同侧;bash 侧要求正斜杠,故
  `sys.executable`/`source_folder`/`package_folder` 统一 `.replace("\\", "/")`。
- Linux(CI)上 `win_bash` 不生效,上述 replace 是 no-op:同一份 test_package
  在本地与 CI 行为一致,不再需要"CI 跑 self.run、本地另建 harness"的双轨。
- Windows 侧 `conan create` 会额外产出 `.bat` env 脚本(含 `msys2_mode.bat`),
  须确认它们被 `.gitignore` 覆盖,否则会混进提交。

## 附带坑

- 零字节文件检查只扫交付树(`share/`+`licenses/`):package 根目录的
  `conaninfo.txt` 是 conan 注入的基础设施文件,常为零字节,会误报。
- 本地无网/证书问题时,可用 `python -m http.server` + 临时改 conandata.yml
  URL 到 127.0.0.1 喂 tarball(sha256 闸门照样生效),跑完
  `git checkout -- conandata.yml` 还原。

## 实测

- CI:提交 2441c79b(恢复 `self.run()`)后 CI #91873 全绿(L0 门禁 / test_package
  / L1,2026-10-14);对照提交 1bc9949c(`subprocess` 直调)#84995 被 L0d 拦截。
- 本地(Windows 宿主,OHOS aarch64-win 交叉 profile):`win_bash` 定式下
  `conan create` 全链路通过,test_package 两个 `self.run()` 均 rc=0,
  consumer 33 项 + layout 39 项 = 72 项 0 失败(2026-10-14 复核)。

## 关联

- 同族但不可照搬:知识库内 `build()` 侧的 subprocess 直调案例(libatomic-ops
  7.10.0 notes.md、xmlsec 1.3.12、tidyhtml 5.8.0)——那些位置没有 L0d 门禁。
