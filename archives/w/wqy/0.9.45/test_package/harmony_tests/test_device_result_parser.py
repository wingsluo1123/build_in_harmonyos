import unittest
import json
import tempfile
import zipfile
from pathlib import Path

from run_device_test import (
    DeviceTestError,
    bundle_dump_matches,
    parse_device_result,
    read_bundle_name_from_hap,
    read_run_id_from_hap,
    select_single_hdc_target,
)

RUN_ID = "0123456789abcdef0123456789abcdef"


class DeviceResultParserTests(unittest.TestCase):
    def test_accepts_exactly_one_pass_marker(self):
        result = parse_device_result(
            f"10-14 16:00:00.000  WQY_HARMONY_TEST_RUN_ID={RUN_ID}\n"
            "10-14 16:00:00.001  WQY_HARMONY_TEST_PASS=1/1\n",
            expected_run_id=RUN_ID,
        )
        self.assertEqual(result.pass_markers, 1)
        self.assertEqual(result.fail_markers, 0)

    def test_rejects_failure_marker_even_if_pass_is_present(self):
        with self.assertRaisesRegex(DeviceTestError, "failure marker"):
            parse_device_result(
                f"WQY_HARMONY_TEST_RUN_ID={RUN_ID}\n"
                "WQY_HARMONY_TEST_PASS=1/1\nWQY_HARMONY_TEST_FAIL=face 2 did not render\n",
                expected_run_id=RUN_ID,
            )

    def test_rejects_missing_pass_marker(self):
        with self.assertRaisesRegex(DeviceTestError, "expected one pass marker"):
            parse_device_result(
                f"WQY_HARMONY_TEST_RUN_ID={RUN_ID}\napp launched\n",
                expected_run_id=RUN_ID,
            )

    def test_rejects_duplicate_pass_markers(self):
        with self.assertRaisesRegex(DeviceTestError, "expected one pass marker"):
            parse_device_result(
                f"WQY_HARMONY_TEST_RUN_ID={RUN_ID}\n"
                "WQY_HARMONY_TEST_PASS=1/1\nWQY_HARMONY_TEST_PASS=1/1\n",
                expected_run_id=RUN_ID,
            )

    def test_ignores_old_run_results(self):
        log = (
            "WQY_HARMONY_TEST_RUN_ID=ffffffffffffffffffffffffffffffff\n"
            "WQY_HARMONY_TEST_PASS=1/1\n"
            f"WQY_HARMONY_TEST_RUN_ID={RUN_ID}\n"
            "WQY_HARMONY_TEST_PASS=1/1\n"
        )
        result = parse_device_result(log, expected_run_id=RUN_ID)
        self.assertEqual(result.pass_markers, 1)

    def test_rejects_zero_connected_hdc_targets(self):
        with self.assertRaisesRegex(DeviceTestError, "exactly one connected HDC target"):
            select_single_hdc_target("COM3\tUART\tReady\n")

    def test_selects_usb_and_ignores_uart_targets(self):
        target = select_single_hdc_target(
            "3QC0124C20001304\t\tUSB\tConnected\tlocalhost\thdc\n"
            "COM3\tUART\tReady\tunknown\thdc\n"
        )
        self.assertEqual(target, "3QC0124C20001304")

    def test_selects_wireless_tcp_target_and_ignores_uart_targets(self):
        target = select_single_hdc_target(
            "10.54.246.164:8710\t\tTCP\tConnected\tlocalhost\thdc\n"
            "COM3\tUART\tReady\tunknown...\thdc\n"
        )
        self.assertEqual(target, "10.54.246.164:8710")

    def test_rejects_multiple_connected_hdc_targets(self):
        targets = (
            "3QC0124C20001304\t\tUSB\tConnected\tlocalhost\thdc\n"
            "10.54.246.164:8710\t\tTCP\tConnected\tlocalhost\thdc\n"
        )
        with self.assertRaisesRegex(DeviceTestError, "found 2"):
            select_single_hdc_target(targets)

    def test_rejects_missing_current_run_id(self):
        with self.assertRaisesRegex(DeviceTestError, "run ID"):
            parse_device_result(
                "WQY_HARMONY_TEST_RUN_ID=ffffffffffffffffffffffffffffffff\n"
                "WQY_HARMONY_TEST_PASS=1/1\n",
                expected_run_id=RUN_ID,
            )

    def test_accepts_installed_bundle_dump_json(self):
        self.assertTrue(
            bundle_dump_matches(
                '{\n  "bundleName": "org.openharmony.wqyfontprobe",\n}',
                "org.openharmony.wqyfontprobe",
            )
        )

    def test_rejects_wrong_installed_bundle_dump(self):
        self.assertFalse(
            bundle_dump_matches(
                '{"bundleName": "org.example.other"}',
                "org.openharmony.wqyfontprobe",
            )
        )

    def test_reads_run_id_from_hap_root_relative_resource_path(self):
        root = Path(__file__).resolve().parents[6] / ".tmp" / "wqy-harmony-tests"
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            hap = Path(temporary) / "test.hap"
            with zipfile.ZipFile(hap, "w") as archive:
                archive.writestr(
                    "resources/rawfile/wqy-test-run-id.txt",
                    RUN_ID + "\n",
                )
            self.assertEqual(read_run_id_from_hap(hap), RUN_ID)

    def test_reads_bundle_name_from_hap_module_json(self):
        root = Path(__file__).resolve().parents[6] / ".tmp" / "wqy-harmony-tests"
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            hap = Path(temporary) / "test.hap"
            with zipfile.ZipFile(hap, "w") as archive:
                archive.writestr(
                    "module.json",
                    json.dumps({"app": {"bundleName": "org.openharmony.wqyfontprobe"}}),
                )
            self.assertEqual(
                read_bundle_name_from_hap(hap), "org.openharmony.wqyfontprobe"
            )


if __name__ == "__main__":
    unittest.main()
