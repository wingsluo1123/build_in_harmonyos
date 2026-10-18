# E4302 — tarball 里发行机生成的 config.h 在 out-of-tree 构建下压过新生成的 config.h

## 错误特征

```
In file included from lib/lirc/curl_poll.h:35:
lib/lirc/config.h:228:9: warning: 'SH_PATH' macro redefined [-Wmacro-redefined]
#define SH_PATH "/usr/bin/sh"
        ^
./config.h:228:9: note: previous definition is here
#define SH_PATH "/system/bin/sh"
        ^

lib/drv_enum.c:96:9: error: incompatible integer to pointer conversion returning 'int'
      from a function with result type 'struct udev_device *' [-Wint-conversion]
        return udev_device_new_from_device_id(udev, dev_id);
lib/drv_enum.c:233:17: error: use of undeclared identifier 'usb_busses'; did you mean 'usb_bus'?
lib/drv_enum.c:239:46: error: incomplete definition of type 'struct usb_device'
```

要点：同一份源码在 **in-tree 构建**下完全正常，**out-of-tree** 下才炸；报错面看起来
像"平台缺头文件"，实际是宏被错误地打开了。

## 触发条件

- 构建系统：autotools（automake），且有 `BUILT_SOURCES` 生成 `config.h`
- tarball 里**同时**带了发行机生成的 `lib/<subdir>/config.h`（`make dist` 未清理）
- 源码用**引号**包含它（`#include "config.h"`）而不是 `<config.h>`
- 构建是 out-of-tree（conan 的 `basic_layout` 默认如此，CI 与本地都是）

## 根因分析

1. `make dist` 把构建机上的生成物一起打进了 tarball。lirc 0.10.2 的
   `lib/lirc/config.h` 就是**发行机**（装了 libudev/libusb/ALSA）上生成的 config.h，
   里面写着：

   ```c
   #define HAVE_LIBUDEV_H 1
   #define HAVE_USB_H 1
   #define HAVE_LINUX_DEVINPUT 1
   #define HAVE_SOUNDCARD 1
   ```

2. `lib/lirc/curl_poll.h:35` 写的是 `#include "config.h"`；C 预处理对**引号包含**
   先从**包含者所在目录**搜索 ⇒ out-of-tree 构建里永远命中源树里这份陈旧副本，
   压过构建目录里刚生成的那份。
3. 上游自己的 `BUILT_SOURCES` 规则 `lirc/config.h: ../config.h`（cp 到 `lirc/`）
   在 **in-tree** 构建下 srcdir == builddir，顺手就把陈旧副本覆盖了，所以上游
   作者从未察觉；out-of-tree 下它写到另一个目录，问题被完整暴露。

后果：`#ifdef HAVE_LIBUDEV_H` / `#ifdef HAVE_USB_H` 包住的平台代码在根本没有这些
头文件的目标上被启用，产生一片"不完整类型/整数转指针"的级联错误。

## 解决方案

### 推荐方案

在 `build()` 里、`apply_conandata_patches()` 之后、`configure()` 之前，删掉源树里
tarball 自带的陈旧生成头：

```python
for relative in ("lib/lirc/config.h",):
    path = os.path.join(self.source_folder, relative)
    if os.path.isfile(path):
        os.remove(path)
```

这些文件本来就是 `BUILT_SOURCES`（规则 `lirc/config.h: ../config.h`），
make 会在构建目录重新生成并使用，删掉不会缺件。

### 禁止做法

- ❌ 往 config.h 追加 `HAVE_*`（`echo '#define HAVE_SNPRINTF 1' >> config.h`）：
  本条的宏是**多余**而不是缺失。引擎实测会误配到 E151（CMake 探测失败 →
  config.h 缺 HAVE_*），方向相反。
- ❌ 为了"让宏成立"而引入 libudev/libusb 依赖：平台确实没有这些库，
  正确做法是让探测结果说话（依赖闸也会拦）。

## 验证

```bash
tar tjf lirc-0.10.2.tar.bz2 | grep -E '(^|/)config\.h$'
grep -nE 'HAVE_LIBUDEV_H|HAVE_USB_H|HAVE_SOUNDCARD' <解压目录>/lib/lirc/config.h
grep -rn '#include "config.h"' <解压目录>/lib
```

三条同现即命中本条。lirc 0.10.2 实测：删除 `lib/lirc/config.h` 后
`lib/drv_enum.c` 的 20 条错误全部消失，`conan create` 继续走到链接成功。

## 关联条目

- 相似但方向相反：**E151**（探测失败导致 config.h **缺** HAVE_*，方案是补宏）
  —— 本条是 config.h **多了**与目标平台不符的宏，方案是让新生成的 config.h 生效。
- 同族：**E4300**（构建根目录的 VERSION 文件顶替 C++ 标准头，同属"生成物名字
  在包含路径里撞车"）。
