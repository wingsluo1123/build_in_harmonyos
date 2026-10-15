/*
 * 消费者测试：以真实用户方式调用已安装的 libshaderc C API，
 * 把一段顶点着色器编译为 SPIR-V，并校验返回结果与 SPIR-V 头部。
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <shaderc/shaderc.h>

#define SPIRV_MAGIC 0x07230203u

static const char kVertexShader[] =
    "#version 450\n"
    "layout(location = 0) in vec3 inPosition;\n"
    "layout(location = 0) out vec4 outColor;\n"
    "void main() {\n"
    "  gl_Position = vec4(inPosition, 1.0);\n"
    "  outColor = vec4(1.0, 0.5, 0.25, 1.0);\n"
    "}\n";

static int failures = 0;

static void check(int condition, const char *what) {
  if (condition) {
    printf("  [ok]   %s\n", what);
  } else {
    printf("  [FAIL] %s\n", what);
    ++failures;
  }
}

/* 编译成功时返回 SPIR-V 字节数，失败返回 0。 */
static size_t compile_vertex_shader(shaderc_compilation_result_t *out) {
  shaderc_compiler_t compiler = shaderc_compiler_initialize();
  check(compiler != NULL, "shaderc_compiler_initialize()");
  if (compiler == NULL) {
    return 0;
  }

  shaderc_compiler_t compiler_ok = compiler;
  *out = shaderc_compile_into_spv(compiler_ok, kVertexShader, strlen(kVertexShader),
                                  shaderc_glsl_vertex_shader, "test.vert", "main", NULL);
  shaderc_compiler_release(compiler_ok);
  check(*out != NULL, "shaderc_compile_into_spv() 返回非空结果");
  if (*out == NULL) {
    return 0;
  }
  check(shaderc_result_get_compilation_status(*out) == shaderc_compilation_status_success,
        "编译状态为 success");
  if (shaderc_result_get_compilation_status(*out) != shaderc_compilation_status_success) {
    fprintf(stderr, "编译错误信息: %s\n", shaderc_result_get_error_message(*out));
    return 0;
  }
  return shaderc_result_get_length(*out);
}

int main(void) {
  printf("shaderc consumer test (shaderc 2026.3)\n");

  shaderc_compilation_result_t result = NULL;
  size_t size = compile_vertex_shader(&result);
  check(size > 0, "编译产物非空");
  if (size == 0) {
    return 1;
  }

  const uint32_t *words = (const uint32_t *)shaderc_result_get_bytes(result);
  check(words != NULL, "shaderc_result_get_bytes() 返回非空");
  check(size % sizeof(uint32_t) == 0, "产物长度为 4 字节对齐");
  check(words != NULL && words[0] == SPIRV_MAGIC, "SPIR-V magic 正确 (0x07230203)");
  check(words != NULL && words[1] != 0, "SPIR-V version 字段非零");
  check(shaderc_result_get_num_warnings(result) == 0, "无编译告警");
  shaderc_result_release(result);

  /* 再带编译选项走一遍：指定 Vulkan 目标环境与性能优化。 */
  shaderc_compiler_t compiler = shaderc_compiler_initialize();
  shaderc_compile_options_t options = shaderc_compile_options_initialize();
  check(options != NULL, "shaderc_compile_options_initialize()");
  if (compiler != NULL && options != NULL) {
    shaderc_compile_options_set_target_env(options, shaderc_target_env_vulkan,
                                           shaderc_env_version_vulkan_1_1);
    shaderc_compile_options_set_optimization_level(options,
                                                   shaderc_optimization_level_performance);
    shaderc_compilation_result_t optimized = shaderc_compile_into_spv(
        compiler, kVertexShader, strlen(kVertexShader), shaderc_glsl_vertex_shader,
        "test.vert", "main", options);
    check(optimized != NULL, "带编译选项调用 shaderc_compile_into_spv()");
    if (optimized != NULL) {
      check(shaderc_result_get_compilation_status(optimized) ==
                shaderc_compilation_status_success,
            "Vulkan 1.1 + performance 优化编译成功");
      check(shaderc_result_get_length(optimized) > 0, "优化产物非空");
      shaderc_result_release(optimized);
    }
    shaderc_compile_options_release(options);
  }
  if (compiler != NULL) {
    shaderc_compiler_release(compiler);
  }

  if (failures != 0) {
    printf("consumer test FAILED: %d 项断言未通过\n", failures);
    return 1;
  }
  printf("consumer test PASSED\n");
  return 0;
}
