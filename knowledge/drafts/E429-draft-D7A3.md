# E429 — HarmonyOS 6.1 IME 会话切换未回调 `inputStop`

## 错误特征

输入法自动化在真实文本输入框之间切换时，旧会话的面板销毁日志已出现，但系统没有发出旧客户端的 `inputStop`。若验收无条件要求 stop 与 destroy 两个回调，就会把设备实际完成的客户端切换判为失败。

在 HarmonyOS 6.1 真机上，单独调用 `TextInputController.stopEditing()` 或 IME 控制器的 `stopInputSession()` 并不能保证产生这两个观测事件。API 返回或没有抛异常也不足以证明旧面板已经销毁。

## 触发条件

- 构建系统：HarmonyOS Stage 模型 IME 扩展
- 阶段：真机生命周期测试
- 设备行为：转移到另一个真实 `TextInput` 后，记录到焦点回调和旧 token 的 `panel_destroyed`，没有旧 token 的 `inputStop`

## 根因分析

IME 会话回调由系统与当前输入客户端共同驱动。HarmonyOS 6.1 在客户端焦点交接时可能销毁旧键盘面板，但不向旧客户端发送独立的 `inputStop` 回调。把 API 调用结果等同于系统生命周期回调，或把“stop 必须发生”写成平台无条件不变量，都会误判有效的焦点交接。

## 解决方案

### 推荐方案

用第二个真实 `TextInput` 触发客户端交接。先记录当前会话 token，再要求焦点请求成功、焦点回调实际发生、旧 token 的键盘面板销毁，并出现不同 token 的新 `input_start` 与新面板创建/展示。HarmonyOS 6.1 真机观测到新会话 `input_start` 可能先于旧面板销毁；应要求旧面板销毁先于新 panel 创建和展示，而不强制销毁先于新会话 start。再从实际 UI 确认 Shift 状态已重置。若系统发出 `inputStop`，还必须验证它先于旧面板销毁。只有上述证据齐全后，才允许在新会话中输入测试字符。测试最终清理时，可在编辑器收到目标字符后记录用例成功，并由测试应用程序化聚焦第二个真实 `TextInput`；runner 应在字符输入前记录清理边界，避免点击按钮造成焦点竞态。若一个测试 run 中可能重复发生相同事件，日志记录还应包含单调序号或交互 ID；按 JSON 内容去重时，不能把相同字段的第二次真实事件误删。

### 禁止做法

- 仅凭 `stopEditing()` 或 `stopInputSession()` 没有报错，就认为旧会话已停止或面板已销毁。
- 把 `inputStop` 缺失自动视为通过；若没有焦点回调、旧面板销毁和不同的新会话 token，仍应失败。
- 用主机注入文本或纯断言替代真机键盘输入与渲染状态检查。

## 验证

运行归档的 `test_package/run_harmonyos_device_test.py`，并检查有序日志中旧/新 token、焦点回调、旧面板销毁和新面板展示；对键盘图标使用组件快照，对新会话 Shift 状态使用真实 UI 颜色观测。

HarmonyOS IME 输入客户端接口的删除方向也需用实际光标位置验证：在 SDK 26 的 `InputClient` 声明中，`deleteForward()` 删除光标之前的文本，`deleteBackward()` 删除之后的文本。编辑器光标在末尾时，Backspace 应调用 `deleteForward(1)`；不能只按方法名称的通常含义猜测方向。

## 关联条目

- 相关：无
