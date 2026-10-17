#define _POSIX_C_SOURCE 200809L
#define CL_TARGET_OPENCL_VERSION 120
#define CL_USE_DEPRECATED_OPENCL_1_1_APIS
#include <CL/cl.h>
#include <CL/cl_ext.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ocl_test_icdl.c defines this loader-specific extension locally. */
typedef cl_int (CL_API_CALL *loader_info_fn)(cl_uint, size_t, void *, size_t *);
enum { ICDL_OCL_VERSION = 1, ICDL_VERSION, ICDL_NAME, ICDL_VENDOR };

static int failures = 0;
static int checks = 0;

static void check(int ok, const char *msg) {
    ++checks;
    if (!ok) {
        fprintf(stderr, "FAIL: %s\n", msg);
        ++failures;
    }
}

static void check_loader_string(loader_info_fn info, cl_uint key,
                                const char *expected, int prefix) {
    size_t size = 0, written = 0;
    cl_int err = info(key, 0, NULL, &size);
    check(err == CL_SUCCESS && size > 1 && size < 1024,
          "loader info size query failed");
    if (err != CL_SUCCESS || size <= 1 || size >= 1024)
        return;
    char *value = (char *)malloc(size);
    check(value != NULL, "loader info allocation failed");
    if (value == NULL)
        return;
    memset(value, 0xff, size);
    err = info(key, size, value, &written);
    check(err == CL_SUCCESS && written == size && value[size - 1] == '\0',
          "loader info value query failed");
    if (err == CL_SUCCESS && value[size - 1] == '\0') {
        check(prefix ? strncmp(value, expected, strlen(expected)) == 0
                     : strcmp(value, expected) == 0,
              "unexpected loader identity");
        printf("loader info %u: %s\n", (unsigned)key, value);
    }
    check(info(key, size - 1, value, NULL) == CL_INVALID_VALUE,
          "loader info accepted undersized buffer");
    free(value);
}

static void check_platform_string(cl_platform_id platform,
                                  cl_platform_info key, const char *expected) {
    char value[128] = {0};
    size_t size = 0;
    cl_int err = clGetPlatformInfo(platform, key, sizeof(value), value, &size);
    check(err == CL_SUCCESS && size > 1 && size <= sizeof(value),
          "platform info query failed");
    if (err == CL_SUCCESS && size > 1 && size <= sizeof(value)) {
        check(value[size - 1] == '\0' && strcmp(value, expected) == 0,
              "incorrect fixture platform info");
        printf("platform info: %s\n", value);
    }
}

int main(int argc, char **argv) {
    if (argc != 2 || (strcmp(argv[1], "empty") != 0 &&
                      strcmp(argv[1], "fixture") != 0)) {
        fprintf(stderr, "usage: %s empty|fixture\n", argv[0]);
        return 2;
    }
    int fixture = strcmp(argv[1], "fixture") == 0;
    /* Isolate host drivers/layers so both paths execute on every CI worker. */
    if (setenv("OCL_ICD_VENDORS", fixture ? TEST_ICD_PATH : EMPTY_VENDOR_DIR, 1) ||
        setenv("OCL_ICD_FILENAMES", "", 1) ||
        setenv("OPENCL_LAYERS", "", 1) ||
        setenv("OCL_ICD_LAYERS", EMPTY_VENDOR_DIR, 1) ||
        unsetenv("OCL_ICD_ASSUME_ICD_EXTENSION")) {
        perror("configure isolated loader environment");
        return 2;
    }

    cl_uint count = 99;
    cl_int err = clGetPlatformIDs(0, NULL, &count);
    check(err == (fixture ? CL_SUCCESS : CL_PLATFORM_NOT_FOUND_KHR),
          "unexpected platform enumeration status");
    check(count == (fixture ? 1u : 0u), "incorrect platform count");
    check(clGetPlatformIDs(0, NULL, NULL) == CL_INVALID_VALUE,
          "platform enumeration accepted invalid arguments");
    printf("mode %s: clGetPlatformIDs returned %d, %u platform(s)\n",
           argv[1], err, (unsigned)count);

    /* v2.3.5 resolves this even without vendors; clIcdGetPlatformIDsKHR
     * belongs to vendor ICD discovery, not this loader-owned extension. */
    loader_info_fn info = (loader_info_fn)clGetExtensionFunctionAddress(
        "clGetICDLoaderInfoOCLICD");
    check(info != NULL, "loader info extension could not be resolved");
    if (info != NULL) {
        check_loader_string(info, ICDL_OCL_VERSION, "OpenCL ", 1);
        check_loader_string(info, ICDL_VERSION, "2.3.5", 0);
        check_loader_string(info, ICDL_NAME, "OpenCL ICD Loader", 0);
        check_loader_string(info, ICDL_VENDOR, "OCL Icd free software", 0);
        check(info(0, 0, NULL, NULL) == CL_INVALID_VALUE,
              "loader info accepted invalid parameter name");
    }
    check(clGetExtensionFunctionAddress("clMissingConsumerTestOCLICD") == NULL,
          "unknown extension unexpectedly resolved");
    check(clUnloadCompiler() == CL_SUCCESS, "clUnloadCompiler failed");

    if (fixture) {
        cl_platform_id platform = NULL;
        err = clGetPlatformIDs(1, &platform, NULL);
        check(err == CL_SUCCESS && platform != NULL,
              "fixture platform retrieval failed");
        if (err == CL_SUCCESS && platform != NULL) {
            check_platform_string(platform, CL_PLATFORM_VENDOR, "Conan test ICD");
            check_platform_string(platform, CL_PLATFORM_VERSION,
                                  "OpenCL 1.2 Conan test ICD");
        }
    }
    printf("ocl-icd test: %d checks, %d failures (%s)\n", checks, failures, argv[1]);
    return failures ? 1 : 0;
}
