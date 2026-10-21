#ifndef NOOPENGLEMDO_RENDERER_H
#define NOOPENGLEMDO_RENDERER_H

namespace noopengldemo {

/// 复刻 libosmscout TiledMapRenderer 的形态：构造函数里预设一个「GL 可用时自动降级」
/// 的优化开关，prepareFrame() 在首次渲染时探测 GL 扩展并可能改小该开关。
class Renderer
{
public:
    enum class TextureScaling {
        Upscaling,    ///< GL 扩展不可用：继续按 2 的幂缩放瓦片
        NoScaling     ///< GL_ARB_texture_non_power_of_two 可用：无需缩放
    };

    Renderer();

    /// 探测 GL 扩展（无 GL 时应静默跳过，保持默认缩放策略）。
    /// 返回 false 表示渲染无法继续。
    bool prepareFrame();

    TextureScaling scaling() const { return glPowerOfTwoTexture; }

private:
    TextureScaling glPowerOfTwoTexture;
};

}  // namespace noopengldemo

#endif  // NOOPENGLEMDO_RENDERER_H
