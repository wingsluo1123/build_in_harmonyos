#define CL_TARGET_OPENCL_VERSION 120
#include <CL/cl.h>
#include <CL/cl_ext.h>
#include <CL/cl_icd.h>
#include <string.h>

/* Minimal vendor ICD: only the callbacks exercised by the loader are present.
 * Static callback addresses avoid interposition by libOpenCL's exported names. */
struct _cl_platform_id { const cl_icd_dispatch *dispatch; };

static cl_int CL_API_CALL fixture_info(cl_platform_id platform,
                                      cl_platform_info key, size_t capacity,
                                      void *value, size_t *size);
static cl_int CL_API_CALL fixture_devices(cl_platform_id platform,
                                         cl_device_type type, cl_uint capacity,
                                         cl_device_id *devices, cl_uint *count) {
    (void)platform; (void)type; (void)capacity; (void)devices;
    if (count) *count = 0;
    return CL_DEVICE_NOT_FOUND;
}
static const cl_icd_dispatch dispatch = {
    .clGetPlatformInfo = fixture_info,
    .clGetDeviceIDs = fixture_devices,
};
static struct _cl_platform_id fixture_platform = { &dispatch };

static cl_int CL_API_CALL fixture_ids(cl_uint capacity, cl_platform_id *platforms,
                                     cl_uint *count) {
    if ((!platforms && !count) || (platforms && !capacity))
        return CL_INVALID_VALUE;
    if (count) *count = 1;
    if (platforms) platforms[0] = &fixture_platform;
    return CL_SUCCESS;
}
static cl_int CL_API_CALL fixture_info(cl_platform_id platform,
                                      cl_platform_info key, size_t capacity,
                                      void *value, size_t *size) {
    const char *text;
    if (platform != &fixture_platform) return CL_INVALID_PLATFORM;
    switch (key) {
    case CL_PLATFORM_EXTENSIONS: text = "cl_khr_icd"; break;
    case CL_PLATFORM_ICD_SUFFIX_KHR: text = "TEST"; break;
    case CL_PLATFORM_PROFILE: text = "FULL_PROFILE"; break;
    case CL_PLATFORM_NAME: text = "Conan fixture platform"; break;
    case CL_PLATFORM_VENDOR: text = "Conan test ICD"; break;
    case CL_PLATFORM_VERSION: text = "OpenCL 1.2 Conan test ICD"; break;
    default: return CL_INVALID_VALUE;
    }
    size_t required = strlen(text) + 1;
    if (value && capacity < required) return CL_INVALID_VALUE;
    if (value) memcpy(value, text, required);
    if (size) *size = required;
    return CL_SUCCESS;
}
CL_API_ENTRY cl_int CL_API_CALL clIcdGetPlatformIDsKHR(
    cl_uint capacity, cl_platform_id *platforms, cl_uint *count) {
    return fixture_ids(capacity, platforms, count);
}
CL_API_ENTRY cl_int CL_API_CALL clGetPlatformInfo(
    cl_platform_id platform, cl_platform_info key, size_t capacity,
    void *value, size_t *size) {
    return fixture_info(platform, key, capacity, value, size);
}
CL_API_ENTRY void *CL_API_CALL clGetExtensionFunctionAddress(const char *name) {
    if (!name) return NULL;
    if (strcmp(name, "clIcdGetPlatformIDsKHR") == 0) return (void *)fixture_ids;
    if (strcmp(name, "clGetPlatformInfo") == 0) return (void *)fixture_info;
    return NULL;
}
