/*
 * Consumer test for the vkd3d package (Conan L1).
 *
 * Exercises the public shader-compiler API from <vkd3d_shader.h> exactly as an
 * external application would. This deliberately targets the part of vkd3d that
 * needs no GPU and no Vulkan device - the standalone DXBC/DXIL -> SPIR-V
 * compiler - so the assertion is self-contained and reproducible:
 *
 *   1. HLSL source          -> DXBC/TPF container   (profile vs_5_0)
 *   2. DXBC/TPF container   -> SPIR-V binary
 *   3. SPIR-V blob starts with the SPIR-V magic number 0x07230203
 *   4. malformed input is NOT reported as VKD3D_OK
 *
 * Exit code is 0 only when every assertion holds.
 */

#include <stdio.h>
#include <string.h>

#include <vkd3d_shader.h>

#define SPIRV_MAGIC 0x07230203u

static unsigned int failures;

static void check(int condition, const char *what)
{
    printf("[%s] %s\n", condition ? "ok" : "FAIL", what);
    if (!condition)
        failures++;
}

static const char hlsl_source[] =
    "float4 main(float4 position : POSITION) : SV_POSITION\n"
    "{\n"
    "    return position;\n"
    "}\n";

int main(void)
{
    struct vkd3d_shader_hlsl_source_info hlsl_info;
    struct vkd3d_shader_compile_info compile_info;
    struct vkd3d_shader_code dxbc;
    struct vkd3d_shader_code spirv;
    char *messages = NULL;
    int rc;

    memset(&hlsl_info, 0, sizeof(hlsl_info));
    hlsl_info.type = VKD3D_SHADER_STRUCTURE_TYPE_HLSL_SOURCE_INFO;
    hlsl_info.next = NULL;
    hlsl_info.entry_point = NULL;   /* defaults to "main" */
    hlsl_info.secondary_code.code = NULL;
    hlsl_info.secondary_code.size = 0;
    hlsl_info.profile = "vs_5_0";

    /* ---- stage 1: HLSL -> DXBC/TPF ------------------------------------- */
    memset(&compile_info, 0, sizeof(compile_info));
    compile_info.type = VKD3D_SHADER_STRUCTURE_TYPE_COMPILE_INFO;
    compile_info.next = &hlsl_info;
    compile_info.source.code = hlsl_source;
    compile_info.source.size = strlen(hlsl_source);
    compile_info.source_type = VKD3D_SHADER_SOURCE_HLSL;
    compile_info.target_type = VKD3D_SHADER_TARGET_DXBC_TPF;
    compile_info.options = NULL;
    compile_info.option_count = 0;
    compile_info.log_level = VKD3D_SHADER_LOG_INFO;
    compile_info.source_name = "consumer-test.hlsl";

    memset(&dxbc, 0, sizeof(dxbc));
    rc = vkd3d_shader_compile(&compile_info, &dxbc, &messages);
    printf("HLSL -> DXBC/TPF: rc=%d size=%zu\n", rc, dxbc.size);
    if (messages)
    {
        printf("  messages: %s\n", messages);
        vkd3d_shader_free_messages(messages);
        messages = NULL;
    }
    check(rc == VKD3D_OK, "vkd3d_shader_compile(HLSL) returns VKD3D_OK");
    check(dxbc.size > 0, "DXBC/TPF container is non-empty");
    check(dxbc.size > 4 && dxbc.code != NULL
            && memcmp(dxbc.code, "DXBC", 4) == 0,
            "DXBC/TPF container carries the 'DXBC' magic");

    if (rc != VKD3D_OK || !dxbc.code || dxbc.size == 0)
    {
        printf("RESULT: %u assertion(s) failed\n", failures);
        return 1;
    }

    /* ---- stage 2: DXBC/TPF -> SPIR-V ----------------------------------- */
    memset(&compile_info, 0, sizeof(compile_info));
    compile_info.type = VKD3D_SHADER_STRUCTURE_TYPE_COMPILE_INFO;
    compile_info.next = NULL;
    compile_info.source = dxbc;
    compile_info.source_type = VKD3D_SHADER_SOURCE_DXBC_TPF;
    compile_info.target_type = VKD3D_SHADER_TARGET_SPIRV_BINARY;
    compile_info.options = NULL;
    compile_info.option_count = 0;
    compile_info.log_level = VKD3D_SHADER_LOG_INFO;
    compile_info.source_name = "consumer-test.dxbc";

    memset(&spirv, 0, sizeof(spirv));
    rc = vkd3d_shader_compile(&compile_info, &spirv, &messages);
    printf("DXBC/TPF -> SPIR-V: rc=%d size=%zu\n", rc, spirv.size);
    if (messages)
    {
        printf("  messages: %s\n", messages);
        vkd3d_shader_free_messages(messages);
        messages = NULL;
    }
    check(rc == VKD3D_OK, "vkd3d_shader_compile(DXBC/TPF -> SPIR-V) returns VKD3D_OK");
    check(spirv.size > 0, "SPIR-V binary is non-empty");
    check(spirv.size >= 4 && spirv.code != NULL
            && *(const unsigned int *)spirv.code == SPIRV_MAGIC,
            "SPIR-V binary starts with the SPIR-V magic number 0x07230203");

    /* ---- negative control --------------------------------------------- */
    memset(&compile_info, 0, sizeof(compile_info));
    compile_info.type = VKD3D_SHADER_STRUCTURE_TYPE_COMPILE_INFO;
    compile_info.source.code = "this is not a valid shader";
    compile_info.source.size = strlen("this is not a valid shader");
    compile_info.source_type = VKD3D_SHADER_SOURCE_DXBC_TPF;
    compile_info.target_type = VKD3D_SHADER_TARGET_SPIRV_BINARY;
    compile_info.log_level = VKD3D_SHADER_LOG_INFO;
    {
        struct vkd3d_shader_code bad;
        memset(&bad, 0, sizeof(bad));
        messages = NULL;
        rc = vkd3d_shader_compile(&compile_info, &bad, &messages);
        printf("malformed DXBC input: rc=%d (expected non-OK)\n", rc);
        if (messages)
            vkd3d_shader_free_messages(messages);
        check(rc != VKD3D_OK, "malformed input is rejected (rc != VKD3D_OK)");
    }

    vkd3d_shader_free_shader_code(&dxbc);
    vkd3d_shader_free_shader_code(&spirv);

    printf("RESULT: %s (%u assertion(s) failed)\n", failures ? "FAIL" : "PASS", failures);
    return failures ? 1 : 0;
}
