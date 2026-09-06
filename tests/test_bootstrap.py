import unittest
from unittest.mock import Mock, patch

from subify import bootstrap
from subify.errors import DependencyError


class BootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        bootstrap.managed_ffmpeg_paths.cache_clear()

    def tearDown(self) -> None:
        bootstrap.managed_ffmpeg_paths.cache_clear()

    @patch("subify.bootstrap.managed_ffmpeg_paths")
    @patch("subify.bootstrap.system_ffmpeg_available", return_value=True)
    def test_system_ffmpeg_available_skips_managed_setup(self, _system_available, managed_paths) -> None:
        bootstrap.bootstrap_runtime_dependencies()

        managed_paths.assert_not_called()

    @patch("subify.bootstrap.managed_ffmpeg_paths")
    @patch("subify.bootstrap.system_ffmpeg_available", return_value=True)
    def test_announce_with_system_ffmpeg_available_prints_no_setup_status(
        self,
        _system_available,
        managed_paths,
    ) -> None:
        with patch("subify.ui.PhaseStatus") as phase_status, patch("subify.ui.print_message") as print_message:
            bootstrap.bootstrap_runtime_dependencies(announce=True)

        managed_paths.assert_not_called()
        phase_status.assert_not_called()
        print_message.assert_not_called()

    @patch("subify.bootstrap.managed_ffmpeg_paths", return_value=("managed-ffmpeg", "managed-ffprobe"))
    @patch("subify.bootstrap.system_ffmpeg_available", return_value=False)
    def test_system_ffmpeg_unavailable_invokes_managed_setup(self, _system_available, managed_paths) -> None:
        bootstrap.bootstrap_runtime_dependencies()

        managed_paths.assert_called_once_with()

    @patch("subify.bootstrap.shutil.which", side_effect=[None, None])
    def test_managed_setup_succeeds_with_static_ffmpeg(self, _which) -> None:
        run = Mock()
        run.get_or_fetch_platform_executables_else_raise.return_value = (
            "managed-ffmpeg",
            "managed-ffprobe",
        )

        with patch.dict("sys.modules", {"static_ffmpeg": Mock(run=run)}):
            self.assertEqual(
                bootstrap.managed_ffmpeg_paths(),
                ("managed-ffmpeg", "managed-ffprobe"),
            )

        run.get_or_fetch_platform_executables_else_raise.assert_called_once_with()

    @patch("subify.bootstrap.shutil.which", side_effect=[None, None])
    def test_managed_setup_failure_raises_dependency_error(self, _which) -> None:
        run = Mock()
        run.get_or_fetch_platform_executables_else_raise.side_effect = RuntimeError("network down")

        with patch.dict("sys.modules", {"static_ffmpeg": Mock(run=run)}):
            with self.assertRaises(DependencyError) as context:
                bootstrap.managed_ffmpeg_paths()

        message = str(context.exception)
        self.assertIn("Subify could not set up FFmpeg automatically", message)
        self.assertIn("network down", message)

    @patch("subify.bootstrap.managed_ffmpeg_paths", return_value=("managed-ffmpeg", "managed-ffprobe"))
    @patch("subify.bootstrap.system_ffmpeg_available", return_value=False)
    def test_announce_path_runs_managed_setup_without_ready_status(
        self,
        _system_available,
        managed_paths,
    ) -> None:
        with patch("subify.ui.PhaseStatus") as phase_status, patch("subify.ui.print_message") as print_message:
            bootstrap.bootstrap_runtime_dependencies(announce=True)

        managed_paths.assert_called_once_with()
        phase_status.assert_not_called()
        print_message.assert_not_called()


if __name__ == "__main__":
    unittest.main()
