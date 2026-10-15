import { common } from '@kit.AbilityKit';
import { fileIo as fs } from '@kit.CoreFileKit';
import { hilog } from '@kit.PerformanceAnalysisKit';
import wqyFontProbe from 'libwqyfontprobe.so';

const DOMAIN = 0xD001100;
const TAG = 'WQYFontProbe';
const SAMPLE_TEXT = '中文字体测试';

interface NativeRenderResult {
  faceIndex: number;
  glyphCount: number;
  textWidth: number;
  lineSpacing: number;
  nonBackgroundPixels: number;
}

@Entry
@Component
struct Index {
  @State status: string = 'Loading the packaged WQY TTC and rasterizing Chinese text…';

  aboutToAppear(): void {
    this.runNativeDrawingTest();
  }

  private async runNativeDrawingTest(): Promise<void> {
    let runId = '';
    try {
      const context = getContext(this) as common.UIAbilityContext;
      const runIdBytes = await context.resourceManager.getRawFileContent('wqy-test-run-id.txt');
      for (let index = 0; index < runIdBytes.length; index++) {
        runId += String.fromCharCode(runIdBytes[index]);
      }
      runId = runId.trim();
      if (!/^[0-9a-f]{32}$/.test(runId)) {
        throw new Error('the HAP contains an invalid test run ID');
      }
      hilog.info(DOMAIN, TAG, 'WQY_HARMONY_TEST_RUN_ID=%{public}s', runId);

      const fontBytes = await context.resourceManager.getRawFileContent('wqy-zenhei.ttc');
      const fontPath = `${context.filesDir}/wqy-zenhei.ttc`;
      try {
        fs.unlinkSync(fontPath);
      } catch (_) {
        // The first launch has no staged file yet.
      }
      const fontFile = fs.openSync(fontPath, fs.OpenMode.CREATE | fs.OpenMode.READ_WRITE);
      let written = 0;
      try {
        const exactBytes = fontBytes.buffer.slice(
          fontBytes.byteOffset,
          fontBytes.byteOffset + fontBytes.byteLength
        );
        written = fs.writeSync(fontFile.fd, exactBytes as ArrayBuffer);
      } finally {
        fs.closeSync(fontFile.fd);
      }
      if (written !== fontBytes.byteLength) {
        throw new Error(`private TTC copy wrote ${written}/${fontBytes.byteLength} bytes`);
      }

      for (let faceIndex = 0; faceIndex < 3; faceIndex++) {
        const nativeResult = JSON.parse(
          wqyFontProbe.renderTtcFace(fontPath, faceIndex, SAMPLE_TEXT)
        ) as NativeRenderResult;
        if (nativeResult.faceIndex !== faceIndex || nativeResult.glyphCount !== 6 ||
            nativeResult.textWidth <= 0 || nativeResult.lineSpacing <= 0 ||
            nativeResult.nonBackgroundPixels <= 0) {
          throw new Error(`face ${faceIndex} returned invalid metrics/raster: ${JSON.stringify(nativeResult)}`);
        }
        hilog.info(
          DOMAIN,
          TAG,
          'face=%{public}d glyphs=%{public}d advance=%{public}f line=%{public}f pixels=%{public}d',
          faceIndex,
          nativeResult.glyphCount,
          nativeResult.textWidth,
          nativeResult.lineSpacing,
          nativeResult.nonBackgroundPixels
        );
      }

      hilog.info(DOMAIN, TAG, 'WQY_HARMONY_TEST_PASS=1/1');
      this.status = `PASS: all 3 TTC faces rasterized “${SAMPLE_TEXT}” into Native Drawing bitmaps.`;
    } catch (error) {
      const message = error instanceof Error ? error.message : JSON.stringify(error);
      hilog.error(DOMAIN, TAG, 'WQY_HARMONY_TEST_FAIL=%{public}s', message);
      this.status = `FAIL: ${message}`;
    }
  }

  build() {
    Column({ space: 16 }) {
      Text('WQY 0.9.45 HarmonyOS Font Probe')
        .fontSize(24)
        .fontWeight(FontWeight.Bold)
      Text('Loads the packaged TTC into app-private storage and rasterizes Chinese text with OH_Drawing.')
        .fontSize(16)
      Text(this.status)
        .fontSize(16)
        .width('100%')
    }
    .padding(24)
    .width('100%')
    .height('100%')
  }
}
