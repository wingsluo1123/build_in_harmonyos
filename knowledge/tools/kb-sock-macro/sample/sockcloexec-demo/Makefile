# KB-SOCK-MACRO 样例库 — 最小构建（故意不用 configure/autotools）
#
# 手工复现：
#   make check                                  # 宽松编译：编译过、运行时断言失败
#   make check STRICT=1                         # 严格编译：macro redefined 直接红
#   make -f ../../../../reproduce.sh 不可用，用 kb-sock-macro/reproduce.sh 做两阶段对照

CC ?= /data/service/hnp/bin/clang
AR ?= llvm-ar
CFLAGS ?= -O2 -Wall
CPPFLAGS += -Iinclude -I.

ifeq ($(STRICT),1)
CFLAGS += -Werror
endif

BIN = check_cloexec

all: $(BIN)

$(BIN): src/demo_sock.c test/check_cloexec.c
	$(CC) $(CPPFLAGS) $(CFLAGS) $^ -o $@

check: $(BIN)
	./$(BIN)

clean:
	rm -f $(BIN)

.PHONY: all check clean
