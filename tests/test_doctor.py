import unittest
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from subify.cli import main
from subify.doctor import (
    DoctorCheck,
    DoctorStatus,
    _check_faster_whisper,
    _check_ffmpeg,
    _check_ffprobe,
    _check_output_directory,
    _check_python,
    _check_temporary_workspace,
    doctor_exit_code,
    render_doctor,
)
from subify.errors import DependencyError, InputValidationError


class DoctorTests(unittest.TestCase):
    @patch("subify.ui.console", None)
    @patch("subify.doctor.validate_output_directory")
    @patch("subify.doctor.resolve_output_directory", return_value="Downloads/Subify")
    @patch("subify.doctor.validate_importable_dependency")
    @patch("subify.doctor.find_ffprobe", return_value="ffprobe")
    @patch("subify.doctor.find_ffmpeg", return_value="ffmpeg")
    def test_all_healthy_dependencies(
        self,
        _find_ffmpeg,
        _find_ffprobe,
        _validate_importable_dependency,
        _resolve_output_directory,
        validate_output_directory,
    ) -> None:
        validate_output_directory.return_value = "Downloads/Subify"

        stdout = StringIO()
        with patch("sys.stdout", stdout):
            exit_code = main(["doctor"])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Subify Doctor", output)
        self.assertIn("Subify-CLI", output)
        self.assertIn("Python", output)
        self.assertIn("FFmpeg", output)
        self.assertIn("FFprobe", output)
        self.assertIn("Faster-Whisper", output)
        self.assertIn("Output Directory", output)
        self.assertIn("Temp Workspace", output)
        self.assertIn("Checks Passed : [✓] 7/7", output)
        self.assertIn("Status        : Ready to generate subtitles", output)

    @patch("subify.doctor.sys.version_info", SimpleNamespace(major=3, minor=10, micro=9))
    @patch("subify.doctor.validate_python_runtime", side_effect=DependencyError("Python 3.11 or newer is required."))
    def test_python_version_check(self, _validate_python_runtime) -> None:
        python_check = _check_python()

        self.assertEqual(python_check.status, DoctorStatus.FAIL)
        self.assertEqual(python_check.detail, "Python version is unsupported")
        self.assertIn("Install Python 3.11 or newer", python_check.action)

    @patch("subify.doctor.find_ffmpeg", side_effect=DependencyError("missing"))
    def test_ffmpeg_missing(self, _find_ffmpeg) -> None:
        ffmpeg_check = _check_ffmpeg()

        self.assertEqual(ffmpeg_check.status, DoctorStatus.FAIL)
        self.assertEqual(ffmpeg_check.detail, "Not found")
        self.assertIn("PATH", ffmpeg_check.action)

    @patch("subify.doctor.find_ffprobe", side_effect=DependencyError("missing"))
    def test_ffprobe_missing(self, _find_ffprobe) -> None:
        ffprobe_check = _check_ffprobe()

        self.assertEqual(ffprobe_check.status, DoctorStatus.FAIL)
        self.assertEqual(ffprobe_check.detail, "Not found")

    @patch("subify.doctor.validate_importable_dependency", side_effect=DependencyError("missing"))
    def test_faster_whisper_missing(self, _validate_importable_dependency) -> None:
        whisper_check = _check_faster_whisper()

        self.assertEqual(whisper_check.status, DoctorStatus.FAIL)
        self.assertEqual(whisper_check.detail, "Not installed")

    @patch("subify.doctor.validate_output_directory", side_effect=InputValidationError("no write"))
    def test_output_directory_failure(self, _validate_output_directory) -> None:
        output_check = _check_output_directory()

        self.assertEqual(output_check.status, DoctorStatus.FAIL)
        self.assertEqual(output_check.detail, "Cannot write to the output location")

    @patch("subify.doctor.TemporaryDirectory", side_effect=OSError("no temp"))
    def test_temporary_workspace_failure(self, _temporary_directory) -> None:
        temp_check = _check_temporary_workspace()

        self.assertEqual(temp_check.status, DoctorStatus.FAIL)
        self.assertEqual(temp_check.name, "Temp Workspace")
        self.assertEqual(temp_check.detail, "Cannot create temporary files")

    def test_exit_code_when_all_pass(self) -> None:
        checks = [DoctorCheck("One", DoctorStatus.PASS, "Ready")]

        self.assertEqual(doctor_exit_code(checks), 0)

    def test_exit_code_when_required_check_fails(self) -> None:
        checks = [DoctorCheck("One", DoctorStatus.FAIL, "Broken")]

        self.assertEqual(doctor_exit_code(checks), 1)

    def test_warning_does_not_cause_failure_exit_code(self) -> None:
        checks = [DoctorCheck("One", DoctorStatus.WARNING, "Usable")]

        self.assertEqual(doctor_exit_code(checks), 0)

    @patch("subify.ui.console", None)
    def test_failure_summary_lists_issues_and_install_command(self) -> None:
        checks = [
            DoctorCheck("Python", DoctorStatus.PASS, "Python 3.11.1 detected"),
            DoctorCheck("FFmpeg", DoctorStatus.FAIL, "Not found"),
            DoctorCheck("FFprobe", DoctorStatus.PASS, "Media inspection tools ready"),
            DoctorCheck("Faster-Whisper", DoctorStatus.FAIL, "Not installed"),
            DoctorCheck("Output Directory", DoctorStatus.PASS, "Write permissions verified"),
            DoctorCheck("Temp Workspace", DoctorStatus.PASS, "Temporary storage operational"),
            DoctorCheck("Subify-CLI", DoctorStatus.PASS, "Version 0.1.0"),
        ]
        stdout = StringIO()

        with patch("sys.stdout", stdout):
            render_doctor(checks)

        output = stdout.getvalue()
        self.assertIn("[✗] 5/7 checks passed", output)
        self.assertIn("Issues Found:", output)
        self.assertIn("FFmpeg not found in PATH", output)
        self.assertIn("Faster-Whisper missing", output)
        self.assertIn("Run:", output)
        self.assertIn("pip install faster-whisper", output)

    @patch("subify.cli.start_shell")
    @patch("subify.cli.doctor_command", return_value=0)
    def test_doctor_does_not_start_shell(self, doctor_command, start_shell) -> None:
        self.assertEqual(main(["doctor"]), 0)
        doctor_command.assert_called_once()
        start_shell.assert_not_called()


if __name__ == "__main__":
    unittest.main()
