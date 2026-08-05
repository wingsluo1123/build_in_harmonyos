#include <gd.h>
#include <dlfcn.h>
#include <stdio.h>
#ifndef TARGET_SO
#define TARGET_SO "libgd.so"
#endif
int main(void) {
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) {
        fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror());
        return 1;
    }
    printf("libgd: dlopen %s ok\n", TARGET_SO);

    /* resolve gdImageCreate and exercise it */
    typedef void *(*gd_image_create_t)(int, int);
    gd_image_create_t _gdImageCreate =
        (gd_image_create_t)dlsym(h, "gdImageCreate");
    if (!_gdImageCreate) {
        fprintf(stderr, "dlsym gdImageCreate failed: %s\n", dlerror());
        return 1;
    }
    void *im = _gdImageCreate(64, 32);
    if (!im) {
        fprintf(stderr, "gdImageCreate(64, 32) returned NULL\n");
        return 1;
    }
    printf("libgd: gdImageCreate(64, 32) ok\n");

    /* resolve gdImageDestroy and clean up */
    typedef void (*gd_image_destroy_t)(void *);
    gd_image_destroy_t _gdImageDestroy =
        (gd_image_destroy_t)dlsym(h, "gdImageDestroy");
    if (_gdImageDestroy) {
        _gdImageDestroy(im);
        printf("libgd: gdImageDestroy ok\n");
    }

    /* check version string */
    typedef const char *(*gd_version_string_t)(void);
    gd_version_string_t _gdVersionString =
        (gd_version_string_t)dlsym(h, "gdVersionString");
    if (_gdVersionString) {
        const char *ver = _gdVersionString();
        printf("libgd: version %s\n", ver ? ver : "(null)");
    }

    dlclose(h);
    printf("libgd: test PASSED\n");
    return 0;
}
