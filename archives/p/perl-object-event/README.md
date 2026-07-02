# perl-object-event

**Object::Event** — Perl 事件回调接口模块

## 描述

Object::Event 提供了一个事件回调接口，允许对象注册、触发和管理事件回调。支持事件优先级、回调注销、事件停止传播等功能。

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 1.23-r0 | built | 2026-06-29 | 初始编译，鸿蒙平台适配 |

## 使用说明

### 安装

```bash
# 通过 Conan 安装
conan install --requires=perl-object-event/1.23-r0@ohpcd/stable -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
```

### 基本用法

```perl
use Object::Event;

my $obj = Object::Event->new();

# 注册事件回调
$obj->reg_cb(my_event => sub {
    my ($self, $arg) = @_;
    print "Event received: $arg\n";
});

# 触发事件
$obj->event(my_event => "hello");

# 注销回调
$obj->unreg_cb($callback);
```

### 高级用法

```perl
# 事件优先级 (高优先级先执行)
$obj->reg_cb("my_event", 100, sub { print "high priority\n" });
$obj->reg_cb("my_event", 0,   sub { print "low priority\n" });

# before_/after_ 前缀事件
$obj->reg_cb(before_my_event => sub { print "before\n" });
$obj->reg_cb(after_my_event  => sub { print "after\n" });
$obj->event("my_event");  # 输出: before, main, after

# 停止事件传播
$obj->reg_cb(my_event => sub { $obj->stop_event });

# Guard 自动注销
{
    my $guard = $obj->reg_cb(my_event => sub { ... });
    # $guard 超出作用域后自动注销回调
}
```

## 运行时依赖

- Perl >= 5.10
- common::sense (系统 Perl 模块)
- AnyEvent (系统 Perl 模块, >= 7.17)

## 鸿蒙平台适配

- **构建系统**: ExtUtils::MakeMaker (Makefile.PL)
- **编译参数**: `INSTALL_BASE=/` + `DESTDIR` 模式
- **补丁**: 无需补丁，纯 Perl 模块直接编译
- **平台限制**: 无 SELinux 限制（纯 Perl 模块不涉及动态库加载）
