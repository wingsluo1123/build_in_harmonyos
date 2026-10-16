# wheel 0.48.0 适配笔记

## 这是什么、为什么要它

`wheel` 是**官方 wheel 打包格式实现**（PyPI，纯 Python），提供 `wheel.wheelfile` /
`wheel.bdist_wheel` / `wheel.tags` 等模块。

补它的直接原因是 **meson-python 的上游测试套件**：`tests/test_rpath.py`、
`test_wheel.py`、`test_wheelfile.py` 等 **6 个模块**都 `import wheel.wheelfile`，
而 ohpcd 此前**没有任何 wheel 版本**（R35 实测 `conan list wheel/*` 为空），
于是该套件在 pytest **采集阶段**即失败：

```text
tests/test_rpath.py:8: import wheel.wheelfile
E   ModuleNotFoundError: No module named 'wheel'
!!! Interrupted: 6 errors during collection !!!    (rc=2)
```

## 打包方式（沿用本仓 pure-Python 先例）

照 `packaging/26.3` 的做法：**不做 pip/setuptools 构建**，直接把上游的 `wheel/`
包目录拷进 `lib/python3.12/site-packages`（上游 0.48.0 用 `src/wheel/` 布局，
配方里对两种布局都做了探测）。`PYTHONPATH` 通过 `runenv_info` 发布，
消费方（如 meson-python 的套件）即可 `import wheel.wheelfile`。

## 源码与校验

- URL：`https://files.pythonhosted.org/packages/source/w/wheel/wheel-0.48.0.tar.gz`
  （PyPI canonical sdist 路径，与 `packaging/26.3` 同一写法）
- sha256：`94800765601e9171bf5d58d066e640662842bcedcbab982b2c90787a2c987322`
  —— 由镜像索引的**声明值**与实际下载字节的**实测值双向核对**一致后写入。

## 上游测试

上游带 `tests/`（pytest 套件），配方内**真实执行**并按实际 rc 如实打印（R51），
不把"未跑"写成"通过"。测试期依赖（pytest）按本仓先例取宿主解释器环境中已有的，
不额外引入制品仓依赖。

---
*编译笔记 · 2026-10-14*
