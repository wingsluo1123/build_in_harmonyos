#include <onnx/onnx_pb.h>
#include <cstdio>

int main() {
    onnx::ModelProto model;
    model.set_ir_version(7);
    if (model.ir_version() == 7) {
        printf("ONNX test: ModelProto ir_version=%d\n", model.ir_version());
        return 0;
    }
    printf("ONNX test: FAIL\n");
    return 1;
}
