# 鸿蒙本机显示复现

这里保存独立部署辅助源码，不向 xmbmon 配方注入第二个软件包。原版 xmbmon、官方 OHOS Xvfb
和 Python 查看器在同一鸿蒙设备运行，浏览器通过回环 HTTP 查看真实帧缓冲。
支持刷新及两档尺寸控制，未实现 ArkUI 窗口或通用远程桌面。

1. 在联网主机/设备运行 `python3 prepare_assets.py`，按 downloads.json 下载并校验已测版本。
   下载器是提交时新增的机械下载入口；这些固定哈希归档已在真机的新目录安装验证。
2. 将本目录及下载文件复制到设备私有工作目录。用本PR配方完成原生 `conan create`，
   将JSON标准输出保存到 `SESSION/evidence/conan-partial-graph.json`。SESSION须为实际绝对目录。
3. 在普通HiShell执行：

```sh
python3 install_runtime.py --work NEW_PRIVATE_WORK --graph SESSION/evidence/conan-partial-graph.json
TMPDIR=NEW_PRIVATE_WORK/tmp python3 local_viewer.py --work NEW_PRIVATE_WORK --session SESSION --duration 3600
```

NEW_PRIVATE_WORK必须为新的本任务私有目录。看到 `LOCAL_GUI_READY` 后，在设备浏览器访问
http://127.0.0.1:8205/。X11显示端口6205和HTTP8205都只监听回环；其他本机进程可访问。
同一时间仅运行一个本任务实例。Ctrl+C、到期或创建 `SESSION/local-gui-stop` 时回收自己的子进程。
重启前移除本任务停止标记。保留 `SESSION/evidence/local-gui/` 的结果和图像。

实测依赖：Xvfb21.1.15、pixman0.46.4、libXfont2 2.0.7、nettle3.10.2、libtirpc1.3.3、
fontenc1.1.7、freetype2.14.3、xkbcomp1.4.7、libpng1.6.43、zlib1.3.1、xkeyboard-config2.42。
libxkbfile1.1.3使用X.Org原始源码。安装过程补pixman SONAME、以-Bsymbolic链接PNG共享库，
并构建仅作用于Xvfb的键盘路径/回环绑定适配器。未修改全局安装前缀或系统库。
原始归档和哈希见downloads.json，各依赖遵循原项目许可证，二进制归档不提交到源码仓库。
