// SPDX-License-Identifier: GPL-3.0-only
import { UIAbility, Want, AbilityConstant } from '@kit.AbilityKit';
import { window } from '@kit.ArkUI';

export default class EntryAbility extends UIAbility {
  onCreate(want: Want, _param: AbilityConstant.LaunchParam): void {
    const run = want.parameters?.runId;
    AppStorage.setOrCreate('wvkbdTestRun', typeof run === 'string' ? run : '');
  }
  async onWindowStageCreate(stage: window.WindowStage): Promise<void> {
    await stage.loadContent('pages/Index');
    const mainWindow = await stage.getMainWindow();
    await mainWindow.maximize();
  }
}
