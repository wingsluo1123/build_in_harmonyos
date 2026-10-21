// SPDX-License-Identifier: GPL-3.0-only
import { hilog } from '@kit.PerformanceAnalysisKit';
import * as consumer from 'libwvkbd_test.so';

interface D02Shape {
  d02_text_length: number;
  d02_prefix_match: number;
  d02_trailing_space: number;
  d02_line_break: number;
  d02_state_match: number;
}

interface TestMarker {
  source: string;
  run: string;
  case: string;
  result: number;
  d02_text_length?: number;
  d02_prefix_match?: number;
  d02_trailing_space?: number;
  d02_line_break?: number;
  d02_state_match?: number;
}

interface InputChangeMarker {
  source: string;
  run: string;
  event: string;
  change: number;
  length: number;
  expected: number;
}

@Entry
@Component
struct Index {
  @State value: string = '';
  @State phase: number = 1;
  @State status: string = 'Ready';
  @State transitionValue: string = '';
  private run: string = '';
  private changeIndex: number = 0;
  private lifecycleIndex: number = 0;
  private restartReported: boolean = false;
  private controller: TextInputController = new TextInputController();
  private transitionController: TextInputController = new TextInputController();

  private marker(id: string, pass: boolean, details?: D02Shape): void {
    // Only run IDs and bounded numeric results leave this app; no text is logged.
    const record: TestMarker = {
      source: 'wvkbd-test', run: this.run, case: id, result: pass ? 1 : 0
    };
    if (details !== undefined) {
      record.d02_text_length = details.d02_text_length;
      record.d02_prefix_match = details.d02_prefix_match;
      record.d02_trailing_space = details.d02_trailing_space;
      record.d02_line_break = details.d02_line_break;
      record.d02_state_match = details.d02_state_match;
    }
    hilog.info(0xD003900, 'wvkbd-test', '%{public}s', JSON.stringify(record));
    this.status = `${id}=${pass ? 1 : 0}`;
  }

  private lifecycleMarker(event: string, result: number): void {
    hilog.info(0xD003900, 'wvkbd-test', '%{public}s', JSON.stringify({
      source: 'wvkbd-test', run: this.run, event, result,
      sequence: ++this.lifecycleIndex
    }));
  }

  private inputChangeMarker(value: string): void {
    this.changeIndex++;
    const record: InputChangeMarker = {
      source: 'wvkbd-test', run: this.run, event: 'input_change',
      change: this.changeIndex, length: value.length, expected: value === 'aB ' ? 1 : 0
    };
    hilog.info(0xD003900, 'wvkbd-test', '%{public}s', JSON.stringify(record));
  }

  private requestEditorHandoff(): void {
    this.lifecycleMarker('session_stop_click', -1);
    try {
      this.getUIContext().getFocusController().requestFocus('wvkbd_test_stop_sink');
      this.lifecycleMarker('session_stop_result', 1);
      this.status = 'Session stopped';
    } catch (_error) {
      this.sessionStopError();
    }
  }

  private sessionStopError(): void {
    this.lifecycleMarker('session_stop_error', 0);
    this.status = 'Session stop failed';
  }

  aboutToAppear(): void {
    this.run = AppStorage.get<string>('wvkbdTestRun') ?? '';
    if (!/^[a-f0-9]{32}$/.test(this.run)) { this.status = 'Invalid run'; return; }
    const results = consumer.runCases();
    for (let index = 0; index < 4; ++index) {
      this.marker(`C0${index + 1}`, results.length === 4 && results[index] === 1);
    }
  }

  build() {
    Column({ space: 14 }) {
      Text('wvkbd synthetic input test').fontSize(24)
      Text(this.status).id('wvkbd_test_status')
      TextInput({ text: this.value, placeholder: 'Synthetic test input', controller: this.controller })
        .id('wvkbd_test_editor').accessibilityText('Synthetic test editor')
        .defaultFocus(true)
        .enterKeyType(EnterKeyType.Done)
        .onChange((value: string) => {
          this.value = value;
          this.inputChangeMarker(value);
          if (this.phase === 2 && value === 'd' && !this.restartReported) {
            this.restartReported = true;
            this.marker('D04', true);
            this.requestEditorHandoff();
          }
        })
        .onBlur(() => { this.lifecycleMarker('editor_blur', 1); })
        .onSubmit((_enterKey, event) => {
          if (this.phase === 1) {
            this.marker('D02', event.text === 'aB ', {
              d02_text_length: event.text.length,
              d02_prefix_match: event.text.startsWith('aB') ? 1 : 0,
              d02_trailing_space: event.text.endsWith(' ') ? 1 : 0,
              d02_line_break: event.text.includes('\n') || event.text.includes('\r') ? 1 : 0,
              d02_state_match: this.value === event.text ? 1 : 0
            });
          }
        })
      TextInput({ text: this.transitionValue, placeholder: 'Lifecycle focus target',
        controller: this.transitionController })
        .id('wvkbd_test_stop_sink').accessibilityText('Lifecycle focus target')
        .onChange((value: string) => { this.transitionValue = value; })
        .onFocus(() => { this.lifecycleMarker('transition_focus', 1); })
      Button('Check primary').id('wvkbd_test_primary')
        .onClick(() => { this.marker('D01', this.phase === 1 && this.value === 'aB '); })
      Button('End editor session')
        .id('wvkbd_test_end').width('100%').height(52)
        .focusOnTouch(true)
        .onClick(() => { this.requestEditorHandoff(); })
      Button('New session').id('wvkbd_test_new')
        .onClick(() => {
          this.phase = 2;
          this.restartReported = false;
          this.value = '';
          this.getUIContext().getFocusController().requestFocus('wvkbd_test_editor');
        })
    }.width('100%').padding(24)
  }
}
