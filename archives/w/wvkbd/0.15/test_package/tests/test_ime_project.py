"""Build contract only; device IME behavior is tested by the HDC runner."""
import json
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "harmonyos" / "ime_app"


def test_ime_project_declares_public_input_method():
    test_app = APP.parents[1] / "test_package" / "ohos_test_app"
    for project in (APP, test_app):
        product = json.loads((project / "build-profile.json5").read_text(
            encoding="utf-8"))["app"]["products"][0]
        assert product.get("compileSdkVersion") == "26.0.0"
        assert product["compatibleSdkVersion"] == "6.1.0(23)"
        assert product["targetSdkVersion"] == "6.1.0(23)"
        assert json.loads((project / "hvigor/hvigor-config.json5").read_text(
            encoding="utf-8"))["modelVersion"] == "26.0.0"
        assert json.loads((project / "oh-package.json5").read_text(
            encoding="utf-8"))["modelVersion"] == "26.0.0"
        assert json.loads((project / "entry/oh-package.json5").read_text(
            encoding="utf-8"))["version"] == "0.15.0"
    module = json.loads((APP / "entry/src/main/module.json5").read_text(encoding="utf-8"))["module"]
    extensions = module.get("extensionAbilities", [])
    assert any(ext.get("type") == "inputMethod" for ext in extensions), "missing system InputMethod extension"
    service = (APP / "entry/src/main/ets/extension/InputMethodService.ts").read_text(encoding="utf-8")
    assert "extends InputMethodExtensionAbility" in service
    assert "@kit.IMEKit" in service
    cmake = (APP / "entry/src/main/cpp/CMakeLists.txt").read_text(encoding="utf-8")
    assert "wvkbd::core" in cmake
    assert "if(NOT DEFINED wvkbd_DIR AND" in cmake


def test_backspace_uses_harmonyos_api_for_text_before_the_cursor():
    service = (APP / "entry/src/main/ets/extension/InputMethodService.ts").read_text(
        encoding="utf-8")
    assert "client.deleteForward(1)" in service
    assert "client.deleteBackward(1)" not in service


def test_visual_evidence_loop_uses_arkts_supported_iteration():
    panel = (APP / "entry/src/main/ets/pages/KeyboardPanel.ets").read_text(encoding="utf-8")
    assert "for (const [row, column] of needed)" not in panel
    assert "const coordinates = needed[index]" in panel


def test_device_restart_really_stops_the_text_input_editor():
    editor = (APP.parents[1] / "test_package/ohos_test_app/entry/src/main/ets/pages/Index.ets")
    source = editor.read_text(encoding="utf-8")
    assert "private transitionController: TextInputController" in source
    assert ".id('wvkbd_test_stop_sink')" in source
    assert "this.getUIContext().getFocusController().requestFocus('wvkbd_test_stop_sink')" in source
    assert "this.getUIContext().getFocusController().requestFocus('wvkbd_test_editor')" in source
    assert "this.lifecycleMarker('transition_focus', 1)" in source
    assert "this.lifecycleMarker('editor_blur', 1)" in source


def test_enter_acceptance_checks_the_text_in_submit_event():
    editor = APP.parents[1] / "test_package/ohos_test_app/entry/src/main/ets/pages/Index.ets"
    source = editor.read_text(encoding="utf-8")
    assert ".onSubmit((_enterKey, event) =>" in source
    assert "this.marker('D02', event.text === 'aB ', {" in source
    assert "d02_text_length: event.text.length" in source
    assert "d02_state_match: this.value === event.text ? 1 : 0" in source


def test_d02_diagnostics_use_explicit_arkts_types_without_object_spread():
    editor = APP.parents[1] / "test_package/ohos_test_app/entry/src/main/ets/pages/Index.ets"
    source = editor.read_text(encoding="utf-8")
    assert "interface D02Shape" in source
    assert "interface TestMarker" in source
    assert "record.d02_text_length = details.d02_text_length" in source
    assert "...details" not in source


def test_input_change_diagnostic_records_only_numeric_shape():
    editor = APP.parents[1] / "test_package/ohos_test_app/entry/src/main/ets/pages/Index.ets"
    source = editor.read_text(encoding="utf-8")
    assert "interface InputChangeMarker" in source
    assert "event: 'input_change'" in source
    assert "length: value.length" in source
    assert "expected: value === 'aB ' ? 1 : 0" in source
    assert "text: value" not in source


def test_d04_is_recorded_on_input_without_stealing_editor_focus():
    editor = APP.parents[1] / "test_package/ohos_test_app/entry/src/main/ets/pages/Index.ets"
    source = editor.read_text(encoding="utf-8")
    assert "private restartReported: boolean = false" in source
    assert "private lifecycleIndex: number = 0" in source
    assert "sequence: ++this.lifecycleIndex" in source
    assert "this.phase === 2 && value === 'd' && !this.restartReported" in source
    assert "this.marker('D04', true)" in source
    assert "this.requestEditorHandoff()" in source
    assert "Button('Check restart')" not in source
