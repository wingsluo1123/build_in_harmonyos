// SPDX-License-Identifier: GPL-3.0-only
import { InputMethodExtensionAbility, inputMethodEngine, InputMethodExtensionContext } from '@kit.IMEKit';
import { Want } from '@kit.AbilityKit';
import { display } from '@kit.ArkUI';
import { hilog } from '@kit.PerformanceAnalysisKit';
import * as core from 'libwvkbd_napi.so';

// A process-local identifier and monotonically increasing session number make
// lifecycle evidence correlatable. No client text, device data or Want is logged.
class InputSession {
  private readonly run: string = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
  private session: number = 0;
  private context: InputMethodExtensionContext | undefined;
  private ability: inputMethodEngine.InputMethodAbility = inputMethodEngine.getInputMethodAbility();
  private client: inputMethodEngine.InputClient | undefined;
  private controller: inputMethodEngine.KeyboardController | undefined;
  private panel: inputMethodEngine.Panel | undefined;
  private panelSession: number = 0;
  private work: Promise<void> = Promise.resolve();
  private active: boolean = false;

  private marker(event: string, session: number): void {
    hilog.info(0xD003900, 'wvkbd', '%{public}s',
      JSON.stringify({ source: 'wvkbd', run: this.run, session: session, event: event }));
  }

  private evidence(event: string, values: Record<string, Object>): void {
    hilog.info(0xD003900, 'wvkbd', '%{public}s', JSON.stringify({
      source: 'wvkbd', run: this.run, session: this.session, event: event, ...values
    }));
  }

  reportKeyBounds(row: number, column: number, x: number, y: number,
    width: number, height: number): void {
    this.evidence('key_bounds', { row: row, column: column, x: Math.round(x), y: Math.round(y),
      width: Math.round(width), height: Math.round(height) });
  }

  reportCapsBounds(x: number, y: number, width: number, height: number): void {
    this.evidence('caps_bounds', { x: Math.round(x), y: Math.round(y),
      width: Math.round(width), height: Math.round(height) });
  }

  reportShiftDisplay(shift: boolean, blue: number, gray: number): void {
    if (blue < 100 && gray < 100) {
      this.evidence('shift_display_invalid', {});
      return;
    }
    this.evidence('shift_display', { shift: shift ? 1 : 0, blue: blue, gray: gray });
  }

  reportShiftGlyph(mask: string[]): void {
    if (mask.length !== 16 || mask.some((row) => row.length !== 16 || /[^01]/.test(row))) {
      this.evidence('shift_glyph_invalid', {});
      return;
    }
    this.evidence('shift_glyph', { mask: mask });
  }

  reportVisualEvidenceError(): void {
    this.evidence('shift_glyph_invalid', {});
  }

  private enqueue(operation: () => Promise<void>, session: number): Promise<void> {
    this.work = this.work.then(operation).catch(() => { this.marker('operation_error', session); });
    return this.work;
  }

  private start = (controller: inputMethodEngine.KeyboardController, client: inputMethodEngine.InputClient): void => {
    const session = ++this.session;
    this.active = true;
    this.controller = controller;
    this.client = client;
    core.resetSession();
    this.marker('input_start', session);
    this.enqueue(async () => {
      await this.destroyPanel();
      if (!this.active || session !== this.session || !this.context) { return; }
      const panel = await this.ability.createPanel(this.context, {
        type: inputMethodEngine.PanelType.SOFT_KEYBOARD,
        flag: inputMethodEngine.PanelFlag.FLG_FIXED
      });
      this.panel = panel;
      this.panelSession = session;
      this.marker('panel_created', session);
      if (!this.active || session !== this.session) { await this.destroyPanel(); return; }
      const screen = display.getDefaultDisplaySync();
      await panel.resize(screen.width, Math.floor(Math.min(screen.height * 0.4, 440 * screen.densityPixels)));
      await panel.setUiContent('pages/KeyboardPanel');
      if (!this.active || session !== this.session) { await this.destroyPanel(); return; }
      await panel.show();
      this.marker('panel_shown', session);
    }, session);
  };

  private stop = (): void => {
    const session = this.session;
    this.active = false;
    this.client = undefined;
    this.controller = undefined;
    core.resetSession();
    this.marker('input_stop', session);
    this.enqueue(async () => { await this.destroyPanel(); }, session);
  };

  private async destroyPanel(): Promise<void> {
    const panel = this.panel;
    if (!panel) { return; }
    const ownerSession = this.panelSession;
    await this.ability.destroyPanel(panel);
    this.panel = undefined;
    this.marker('panel_destroyed', ownerSession);
  }

  attach(context: InputMethodExtensionContext): void {
    this.context = context;
    this.ability.on('inputStart', this.start);
    this.ability.on('inputStop', this.stop);
    this.marker('service_created', this.session);
  }

  detach(): void {
    this.ability.off('inputStart', this.start);
    this.ability.off('inputStop', this.stop);
    this.stop();
    this.context = undefined;
    this.marker('service_destroyed', this.session);
  }

  press(row: number, column: number): Promise<void> {
    const session = this.session;
    return this.enqueue(async () => {
      const client = this.client;
      if (!this.active || session !== this.session || !client) { return; }
      const event = core.activate(row, column);
      switch (event.action) {
        case 0:
          if (!await client.insertText(event.text)) { this.marker('input_rejected', session); }
          break;
        case 1:
          if (!await client.deleteForward(1)) { this.marker('input_rejected', session); }
          break;
        case 2:
          const attribute = await client.getEditorAttribute();
          if (this.active && session === this.session && this.client === client) {
            if (!await client.sendKeyFunction(attribute.enterKeyType)) { this.marker('input_rejected', session); }
          }
          break;
        case 3:
          break;
      }
    }, session);
  }

  setCaps(enabled: boolean): Promise<void> {
    const session = this.session;
    return this.enqueue(async () => {
      if (this.active && session === this.session) { core.setCapsLock(enabled); }
    }, session);
  }

  dismiss(): Promise<void> {
    const session = this.session;
    return this.enqueue(async () => {
      const controller = this.controller;
      if (!this.active || session !== this.session || !controller) { return; }
      core.dismiss();
      await controller.hide();
      this.marker('panel_dismissed', session);
    }, session);
  }
}

export const inputSession: InputSession = new InputSession();

export default class InputMethodService extends InputMethodExtensionAbility {
  onCreate(_want: Want): void { inputSession.attach(this.context); }
  onDestroy(): void { inputSession.detach(); }
}
