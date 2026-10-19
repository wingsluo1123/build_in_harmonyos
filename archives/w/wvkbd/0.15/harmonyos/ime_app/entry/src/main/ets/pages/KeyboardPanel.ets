// SPDX-License-Identifier: GPL-3.0-only
import * as core from 'libwvkbd_napi.so';
import { inputSession } from '../extension/InputMethodService';
import { image } from '@kit.ImageKit';
import { UIContext } from '@kit.ArkUI';

interface PanelKey {
  row: number;
  column: number;
  label: string;
  action: number;
}
interface PanelRow { index: number; keys: PanelKey[]; }

@Entry
@Component
struct KeyboardPanel {
  @State rows: PanelRow[] = [];
  @State shift: boolean = false;
  @State caps: boolean = false;
  private visualBusy: boolean = false;
  private visualAttempts: number = 0;

  aboutToAppear(): void { this.refresh(); }

  private refresh(): void {
    const rows: PanelRow[] = [];
    for (let row = 0; row < core.rowCount(); row++) {
      const keys: PanelKey[] = [];
      for (let column = 0; column < core.keyCount(row); column++) {
        const key = core.keyAt(row, column);
        this.shift = key.shift;
        this.caps = key.capsLock;
        keys.push({ row: row, column: column, label: key.label, action: key.action });
      }
      rows.push({ index: row, keys: keys });
    }
    this.rows = rows;
    this.scheduleVisualEvidence();
  }

  private scheduleVisualEvidence(): void {
    setTimeout(() => { this.reportVisualEvidence(); }, 160);
  }

  private async reportVisualEvidence(): Promise<void> {
    if (this.visualBusy) {
      setTimeout(() => { this.reportVisualEvidence(); }, 80);
      return;
    }
    this.visualBusy = true;
    try {
      const context = this.getUIContext();
      const components = context.getComponentUtils();
      const needed = [[3, 0], [3, 2], [4, 0], [4, 3], [4, 5], [4, 8],
        [5, 1], [5, 3]];
      for (let index = 0; index < needed.length; index++) {
        const coordinates = needed[index];
        const row = coordinates[0];
        const column = coordinates[1];
        const id = `wvkbd_key_${row}_${column}`;
        const bounds = components.getRectangleById(id);
        inputSession.reportKeyBounds(row, column, bounds.screenOffset.x,
          bounds.screenOffset.y, bounds.size.width, bounds.size.height);
      }
      const caps = components.getRectangleById('wvkbd_caps');
      inputSession.reportCapsBounds(caps.screenOffset.x, caps.screenOffset.y,
        caps.size.width, caps.size.height);
      await this.captureShiftDisplay(context);
      await this.captureShiftGlyph(context);
      this.visualAttempts = 0;
    } catch (_error) {
      this.visualAttempts++;
      if (this.visualAttempts < 8) {
        setTimeout(() => { this.reportVisualEvidence(); }, 180);
      }
    } finally {
      this.visualBusy = false;
    }
  }

  private async captureShiftDisplay(context: UIContext): Promise<void> {
    const pixelMap = await context.getComponentSnapshot().get('wvkbd_key_4_0',
      { waitUntilRenderFinished: true });
    try {
      const info = await pixelMap.getImageInfo();
      const stride = pixelMap.getBytesNumberPerRow();
      const data = new ArrayBuffer(pixelMap.getPixelBytesNumber());
      await pixelMap.readPixelsToBuffer(data);
      const pixels = new Uint8Array(data);
      const bytesPerPixel = stride / info.size.width;
      if (bytesPerPixel !== 4 || info.size.width > 512 || info.size.height > 512) {
        throw new Error('unsupported component image');
      }
      let blue = 0;
      let gray = 0;
      for (let y = 2; y < info.size.height - 2; y++) {
        for (let x = 2; x < info.size.width - 2; x++) {
          const offset = y * stride + x * 4;
          let red = pixels[offset];
          let green = pixels[offset + 1];
          let blueChannel = pixels[offset + 2];
          if (info.pixelFormat === image.PixelMapFormat.BGRA_8888) {
            const swap = red;
            red = blueChannel;
            blueChannel = swap;
          } else if (info.pixelFormat === image.PixelMapFormat.ARGB_8888) {
            red = pixels[offset + 1];
            green = pixels[offset + 2];
            blueChannel = pixels[offset + 3];
          }
          if (Math.abs(red - 36) < 18 && Math.abs(green - 108) < 18 &&
              Math.abs(blueChannel - 188) < 18) { blue++; }
          if (Math.abs(red - 76) < 18 && Math.abs(green - 83) < 18 &&
              Math.abs(blueChannel - 96) < 18) { gray++; }
        }
      }
      inputSession.reportShiftDisplay(this.shift, blue, gray);
    } finally {
      await pixelMap.release();
    }
  }

  private async captureShiftGlyph(context: UIContext): Promise<void> {
    const pixelMap = await context.getComponentSnapshot().get('wvkbd_shift_label',
      { scale: 3, waitUntilRenderFinished: true });
    try {
      const info = await pixelMap.getImageInfo();
      const stride = pixelMap.getBytesNumberPerRow();
      const data = new ArrayBuffer(pixelMap.getPixelBytesNumber());
      await pixelMap.readPixelsToBuffer(data);
      const pixels = new Uint8Array(data);
      const bytesPerPixel = stride / info.size.width;
      if (bytesPerPixel !== 4 || info.size.width > 512 || info.size.height > 512) {
        throw new Error('unsupported component image');
      }
      let minX = info.size.width;
      let maxX = -1;
      let minY = info.size.height;
      let maxY = -1;
      const white = new Uint8Array(info.size.width * info.size.height);
      for (let y = 0; y < info.size.height; y++) {
        for (let x = 0; x < info.size.width; x++) {
          const offset = y * stride + x * 4;
          let red = pixels[offset];
          let green = pixels[offset + 1];
          let blue = pixels[offset + 2];
          let alpha = pixels[offset + 3];
          if (info.pixelFormat === image.PixelMapFormat.BGRA_8888) {
            const swap = red;
            red = blue;
            blue = swap;
          } else if (info.pixelFormat === image.PixelMapFormat.ARGB_8888) {
            alpha = pixels[offset];
            red = pixels[offset + 1];
            green = pixels[offset + 2];
            blue = pixels[offset + 3];
          }
          if (alpha > 48 && red > 175 && green > 175 && blue > 175) {
            white[y * info.size.width + x] = 1;
            minX = Math.min(minX, x);
            maxX = Math.max(maxX, x);
            minY = Math.min(minY, y);
            maxY = Math.max(maxY, y);
          }
        }
      }
      const mask: string[] = [];
      if (maxX >= minX && maxY >= minY) {
        const glyphWidth = maxX - minX + 1;
        const glyphHeight = maxY - minY + 1;
        for (let cellY = 0; cellY < 16; cellY++) {
          let row = '';
          for (let cellX = 0; cellX < 16; cellX++) {
            const x0 = minX + Math.floor(cellX * glyphWidth / 16);
            const x1 = Math.max(x0 + 1, minX + Math.floor((cellX + 1) * glyphWidth / 16));
            const y0 = minY + Math.floor(cellY * glyphHeight / 16);
            const y1 = Math.max(y0 + 1, minY + Math.floor((cellY + 1) * glyphHeight / 16));
            let lit = false;
            for (let y = y0; y < Math.min(y1, maxY + 1) && !lit; y++) {
              for (let x = x0; x < Math.min(x1, maxX + 1); x++) {
                if (white[y * info.size.width + x]) { lit = true; break; }
              }
            }
            row += lit ? '1' : '0';
          }
          mask.push(row);
        }
      }
      if (mask.length === 16) { inputSession.reportShiftGlyph(mask); }
    } finally {
      await pixelMap.release();
    }
  }

  build() {
    Column({ space: 4 }) {
      Row({ space: 12 }) {
        Text('wvkbd').fontSize(18).fontColor('#FFFFFF')
        Button(this.caps ? 'Caps: On' : 'Caps: Off')
          .id('wvkbd_caps').accessibilityText(this.caps ? 'Caps Lock on' : 'Caps Lock off')
          .backgroundColor(this.caps ? '#246CBC' : '#4C5360')
          .onClick(async () => { await inputSession.setCaps(!this.caps); this.refresh(); })
        Text(this.shift ? 'Shift: On' : 'Shift: Off').fontColor('#FFFFFF').id('wvkbd_shift_state')
        Blank()
        Button('Hide').id('wvkbd_hide')
          .onClick(async () => { await inputSession.dismiss(); this.refresh(); })
      }.width('100%').height(40)
      ForEach(this.rows, (row: PanelRow) => {
        Row({ space: 4 }) {
          ForEach(row.keys, (key: PanelKey) => {
            Button() {
              Text(key.label)
                .id(key.label === '⇧' ? 'wvkbd_shift_label' : `wvkbd_label_${key.row}_${key.column}`)
                .fontSize(20).fontColor('#FFFFFF')
            }
              .id(`wvkbd_key_${key.row}_${key.column}`)
              .accessibilityText(key.label)
              .backgroundColor(key.action === 3 && this.shift ? '#246CBC' : '#4C5360')
              .borderRadius(6).layoutWeight(key.label === 'Space' ? 4 : 1).height('100%')
              .onClick(async () => { await inputSession.press(key.row, key.column); this.refresh(); })
          }, (key: PanelKey) => `${key.row}:${key.column}:${key.label}`)
        }.width('100%').layoutWeight(1)
      }, (row: PanelRow) => `${row.index}`)
    }.width('100%').height('100%').padding(8).backgroundColor('#202630')
      .onAppear(() => { this.scheduleVisualEvidence(); })
  }
}
