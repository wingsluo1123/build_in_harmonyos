/*
 * evemu consumer test — real libevemu API calls, no device access.
 *
 * Capability note: evemu_new() only allocates the struct, calls
 * libevdev_new() and stores the name (src/evemu.c). It never opens
 * /dev/input/* or /dev/uinput, which is exactly why upstream uses the
 * same entry point in its own test/test-c-compile.c. Nothing here
 * records or replays input events.
 */
#include <stdio.h>
#include <string.h>

#include <evemu.h>

/* provided by test_cpp.cpp — mirrors upstream test-cxx-compile.c */
int evemu_cpp_probe(void);

int main(void) {
    struct evemu_device *dev;
    const char *name;

    dev = evemu_new("evemu-consumer");
    if (dev == NULL) {
        fprintf(stderr, "FAIL: evemu_new() returned NULL\n");
        return 1;
    }
    printf("evemu_new -> %p\n", (void *)dev);

    name = evemu_get_name(dev);
    if (name == NULL || strcmp(name, "evemu-consumer") != 0) {
        fprintf(stderr, "FAIL: evemu_get_name() -> %s\n",
                name ? name : "(null)");
        evemu_delete(dev);
        return 1;
    }
    printf("name -> %s\n", name);

    evemu_set_name(dev, "evemu-consumer-renamed");
    name = evemu_get_name(dev);
    if (name == NULL || strcmp(name, "evemu-consumer-renamed") != 0) {
        fprintf(stderr, "FAIL: name round-trip -> %s\n",
                name ? name : "(null)");
        evemu_delete(dev);
        return 1;
    }
    printf("name round-trip -> %s\n", name);

    evemu_delete(dev);
    printf("evemu delete -> OK\n");

    if (evemu_cpp_probe() != 0) {
        fprintf(stderr, "FAIL: C++ consumer probe\n");
        return 1;
    }
    printf("evemu consumer test: OK\n");
    return 0;
}
