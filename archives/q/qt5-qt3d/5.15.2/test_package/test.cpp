#include <Qt3DCore/QEntity>
#include <Qt3DCore/QTransform>
#include <QCoreApplication>
#include <cstdio>

int main(int argc, char *argv[]) {
    QCoreApplication app(argc, argv);
    // 真实调用 Qt53DCore API：创建实体并附加组件
    // 注意：QComponent 构造函数为 protected 无法直接实例化，
    // 使用 public 构造的 QTransform（QComponent 子类）作为测试组件
    Qt3DCore::QEntity rootEntity;
    Qt3DCore::QTransform component(&rootEntity);
    rootEntity.addComponent(&component);
    const auto components = rootEntity.components();
    if (components.isEmpty()) {
        std::printf("Qt53D test FAILED: no components attached\n");
        return 1;
    }
    std::printf("Qt53D test PASSED\n");
    return 0;
}
