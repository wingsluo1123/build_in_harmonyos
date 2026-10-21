#include "noopengldemo/renderer.h"

#include <QtCore>

#include <QOpenGLContext>
#include <QOpenGLFunctions>

namespace noopengldemo {

Renderer::Renderer()
  : glPowerOfTwoTexture(TextureScaling::Upscaling)
{
}

bool Renderer::prepareFrame()
{
  // 与 libosmscout TiledMapRenderer::RenderMap 同形态：首次渲染时探测
  // GL_ARB_texture_non_power_of_two，可用则关闭瓦片缩放。
  if (QOpenGLContext *glContext = QOpenGLContext::currentContext();
      glContext
      && this->glPowerOfTwoTexture != TextureScaling::NoScaling
      && glContext->functions()->hasOpenGLFeature(QOpenGLFunctions::NPOTTextures)) {

    // 只在首次渲染请求时改动一次，因此无需让瓦片缓存失效。
    this->glPowerOfTwoTexture = TextureScaling::NoScaling;
  }

  return true;
}

}  // namespace noopengldemo
