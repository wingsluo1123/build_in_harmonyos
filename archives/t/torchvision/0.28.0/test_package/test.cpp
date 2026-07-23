#include <torch/torch.h>
#include <torchvision/ops/nms.h>

#include <iostream>

int main() {
    const auto boxes = torch::tensor({
        {0.0F, 0.0F, 10.0F, 10.0F},
        {1.0F, 1.0F, 11.0F, 11.0F},
        {20.0F, 20.0F, 30.0F, 30.0F},
    });
    const auto scores = torch::tensor({0.9F, 0.8F, 0.7F});

    const auto keep = vision::ops::nms(boxes, scores, 0.5);
    if (keep.numel() != 2) {
        std::cerr << "unexpected NMS keep count: " << keep.numel() << std::endl;
        return 1;
    }
    if (keep[0].item<int64_t>() != 0 || keep[1].item<int64_t>() != 2) {
        std::cerr << "unexpected NMS indices: " << keep << std::endl;
        return 1;
    }

    std::cout << "torchvision NMS smoke test passed" << std::endl;
    return 0;
}
