# Consumer-test project built with the mrbuild templates.
# MRBUILD_DIR is exported by the test environment (points into the package).
# NOTE: unquoted include paths on purpose — GNU make 4.3 mishandles a second
# quoted include name (quotes not stripped -> "No such file or directory").
include $(MRBUILD_DIR)/Makefile.common.header

PROJECT_NAME := mrtest
ABI_VERSION  := 0
TAIL_VERSION := 1
LIB_SOURCES  := lib.c
BIN_SOURCES  := run.c

include $(MRBUILD_DIR)/Makefile.common.footer
