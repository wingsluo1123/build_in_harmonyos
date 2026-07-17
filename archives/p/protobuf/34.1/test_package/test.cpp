#include <google/protobuf/message.h>
#include <google/protobuf/descriptor.h>
#include <cstdio>
#include <string>

int main() {
    const auto* pool = google::protobuf::DescriptorPool::generated_pool();
    const auto* desc = pool->FindMessageTypeByName("google.protobuf.FileDescriptorSet");
    if (desc == nullptr) {
        printf("FAIL: FileDescriptorSet not found\n");
        return 1;
    }
    std::string name(desc->name());
    printf("protobuf test: %s, fields=%d\n", name.c_str(), desc->field_count());
    return 0;
}
