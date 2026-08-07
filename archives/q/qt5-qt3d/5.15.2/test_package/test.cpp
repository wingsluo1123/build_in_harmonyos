#include <Qt3DCore/QEntity>
#include <Qt3DCore/QComponent>
#include <QCoreApplication>
#include <cstdio>

int main(int argc, char *argv[]) {
    QCoreApplication app(argc, argv);
    // 真实调用 Qt53DCore API：创建实体并附加组件
    Qt3DCore::QEntity rootEntity;
    Qt3DCore::QComponent component(&rootEntity);
    rootEntity.addComponent(&component);
    const auto components = rootEntity.components();
    if (components.isEmpty()) {
        std::printf("Qt53D test FAILED: no components attached\n");
        return 1;
    }
    std::printf("Qt53D test PASSED\n");
    return 0;
}
