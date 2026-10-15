export interface NativeRenderResult {
  faceIndex: number;
  glyphCount: number;
  textWidth: number;
  lineSpacing: number;
  nonBackgroundPixels: number;
}

declare function renderTtcFace(path: string, faceIndex: number, sample: string): string;

export default {
  renderTtcFace
};
