# torchvision

Datasets, Transforms and Models for computer vision.

The torchvision package consists of popular datasets, model architectures, and common image transformations for computer vision.

## C++ Extension

This archive provides the torchvision C++ extension library (`libtorchvision.so`) which provides custom operators (NMS, ROI Align, ROI Pool, Deformable Conv, etc.) and image I/O support.

## Dependencies

- **libtorch (PyTorch 2.9.0)**: Core dependency. Must be available as a Conan package or installed locally.
- libpng (optional, for PNG support)
- libjpeg (optional, for JPEG support)

## Versions

- [0.28.0](0.28.0/) — Built against PyTorch 2.9.0 (CPU-only)
