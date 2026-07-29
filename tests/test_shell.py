import unittest
from unittest.mock import Mock, patch

from subify.shell import execute_shell_line, parse_shell_command, start_shell


class ShellTests(unittest.TestCase):
    def test_existing_welcome_renders_once_and_exit_stops_session(self) -> None:
        dispatcher = Mock(return_value=0)

        with (
            patch("subify.shell.ui.render_welcome") as render_welcome,
            patch("subify.shell.ui.render_shell_exit") as render_exit,
        ):
            exit_code = start_shell(dispatcher, input_reader=lambda _prompt: "/exit")

        self.assertEqual(exit_code, 0)
        render_welcome.assert_called_once()
        render_exit.assert_called_once()
        dispatcher.assert_not_called()

    def test_shell_help_works(self) -> None:
        with patch("subify.shell.ui.render_shell_help") as render_help:
            should_continue = execute_shell_line("/help", Mock(return_value=0))

        self.assertTrue(should_continue)
        render_help.assert_called_once()

    def test_slash_shows_suggested_commands(self) -> None:
        with patch("subify.shell.ui.render_shell_suggestions") as render_suggestions:
            should_continue = execute_shell_line("/", Mock(return_value=0))

        self.assertTrue(should_continue)
        render_suggestions.assert_called_once()
        self.assertIn("/help", render_suggestions.call_args.args[0])
        self.assertIn("/version", render_suggestions.call_args.args[0])

    def test_shell_exit_works(self) -> None:
        with patch("subify.shell.ui.render_shell_exit") as render_exit:
            should_continue = execute_shell_line("/exit", Mock(return_value=0))

        self.assertFalse(should_continue)
        render_exit.assert_called_once()

    def test_unknown_command_is_handled_safely(self) -> None:
        with patch("subify.shell.ui.render_unknown_shell_command") as render_unknown:
            should_continue = execute_shell_line("xyz", Mock(return_value=0))

        self.assertTrue(should_continue)
        render_unknown.assert_called_once_with("xyz")

    def test_empty_input_does_not_crash_or_dispatch(self) -> None:
        dispatcher = Mock(return_value=0)

        self.assertTrue(execute_shell_line("   ", dispatcher))
        dispatcher.assert_not_called()

    def test_process_routes_to_shared_command_dispatcher(self) -> None:
        dispatcher = Mock(return_value=0)

        execute_shell_line('process "C:\\Videos\\lesson with spaces.mp4"', dispatcher)

        dispatcher.assert_called_once_with(["process", "C:\\Videos\\lesson with spaces.mp4"])

    def test_generate_srt_routes_to_shared_command_dispatcher(self) -> None:
        dispatcher = Mock(return_value=0)

        execute_shell_line('generate-srt "lesson with spaces.mp4"', dispatcher)

        dispatcher.assert_called_once_with(["generate-srt", "lesson with spaces.mp4"])

    def test_embed_routes_to_shared_command_dispatcher(self) -> None:
        dispatcher = Mock(return_value=0)

        execute_shell_line('embed "lesson one.mp4" "lesson one.srt"', dispatcher)

        dispatcher.assert_called_once_with(["embed", "lesson one.mp4", "lesson one.srt"])

    def test_missing_direct_command_arguments_do_not_dispatch(self) -> None:
        dispatcher = Mock(return_value=0)

        with patch("subify.shell.ui.render_shell_error") as render_error:
            execute_shell_line("process", dispatcher)

        dispatcher.assert_not_called()
        render_error.assert_called_once_with("Usage: process <video>")

    def test_argparse_failures_do_not_exit_shell(self) -> None:
        dispatcher = Mock(side_effect=SystemExit(2))

        with patch("subify.shell.ui.render_shell_error") as render_error:
            should_continue = execute_shell_line("process lesson.mp4 --bad-option", dispatcher)

        self.assertTrue(should_continue)
        render_error.assert_called_once()

    def test_parse_shell_command_handles_extra_whitespace_and_quoted_paths(self) -> None:
        args = parse_shell_command('  embed   "my lesson.mp4"   "my captions.srt"  ')

        self.assertEqual(args, ["embed", "my lesson.mp4", "my captions.srt"])


if __name__ == "__main__":
    unittest.main()
