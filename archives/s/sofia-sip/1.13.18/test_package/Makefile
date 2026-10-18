PKGCONF ?= pkgconf
PACKAGES = sofia-sip-ua sofia-sip-ua-glib glib-2.0

SOFIA_CFLAGS = $(shell $(PKGCONF) --static --cflags $(PACKAGES))
SOFIA_LIBS = $(shell $(PKGCONF) --static --libs $(PACKAGES))
TESTS = $(BUILD_DIR)/test_sofia_consumer $(BUILD_DIR)/test_sofia_harmonyos

.PHONY: all check
all: $(TESTS)

$(BUILD_DIR)/test_sofia_consumer: $(SOURCE_DIR)/test_sofia_consumer.c
	$(CC) $(CFLAGS) $(SOFIA_CFLAGS) -pthread $< -o $@ $(SOFIA_LIBS) -pthread

$(BUILD_DIR)/test_sofia_harmonyos: $(SOURCE_DIR)/test_sofia_harmonyos.c
	$(CC) $(CFLAGS) $(SOFIA_CFLAGS) -pthread $< -o $@ $(SOFIA_LIBS) -pthread

check: all
	$(BUILD_DIR)/test_sofia_consumer
	$(BUILD_DIR)/test_sofia_harmonyos
