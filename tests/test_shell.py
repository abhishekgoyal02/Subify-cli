import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

from subify import ui
from subify.shell import execute_shell_line, parse_shell_command, start_shell, suggest_shell_commands


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

    def test_shell_input_uses_subify_placeholder_not_traditional_prompt(self) -> None:
        prompts: list[str] = []

        def input_reader(prompt: str) -> str:
            prompts.append(prompt)
            return "/exit"

        with (
            patch("subify.shell.ui.render_welcome"),
            patch("subify.shell.ui.render_shell_exit"),
        ):
            start_shell(Mock(return_value=0), input_reader=input_reader)

        self.assertEqual(len(prompts), 1)
        self.assertIn(ui.SHELL_INPUT_PLACEHOLDER, prompts[0])
        self.assertNotIn("subify >", prompts[0])
        self.assertNotIn("C:\\>", prompts[0])
        self.assertNotIn("PS C:\\>", prompts[0])

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

    def test_slash_filtering_shows_all_shell_commands(self) -> None:
        suggestions = suggest_shell_commands("/")

        self.assertIn("/help", suggestions)
        self.assertIn("/version", suggestions)
        self.assertIn("/process", suggestions)
        self.assertIn("/generate-srt", suggestions)
        self.assertIn("/embed", suggestions)
        self.assertIn("/update", suggestions)
        self.assertIn("/config", suggestions)
        self.assertIn("/clear", suggestions)
        self.assertIn("/history", suggestions)
        self.assertIn("/exit", suggestions)

    def test_slash_filtering_matches_partial_commands(self) -> None:
        self.assertEqual(suggest_shell_commands("/h"), ("/help",))
        self.assertEqual(suggest_shell_commands("/v"), ("/version",))
        self.assertEqual(suggest_shell_commands("/pr"), ("/process",))
        self.assertEqual(suggest_shell_commands("/gen"), ("/generate-srt",))
        self.assertEqual(suggest_shell_commands("/em"), ("/embed",))

    def test_doctor_is_not_suggested_inside_shell(self) -> None:
        self.assertNotIn("/doctor", suggest_shell_commands("/"))

    def test_help_panel_is_short_and_includes_website(self) -> None:
        buffer = io.StringIO()

        with patch("subify.ui.console", None), redirect_stdout(buffer):
            ui.render_shell_help()

        output = buffer.getvalue()
        self.assertIn("SUBIFY HELP", output)
        self.assertIn("A quick map of the shell and what Subify actually does.", output)
        self.assertIn("Type / to discover actions", output)
        self.assertIn("https://subify-cli.vercel.app/", output)
        self.assertNotIn('/process "video.mp4"', output)
        self.assertNotIn('/generate-srt "video.mp4"', output)
        self.assertNotIn('/embed "video.mp4" "video.srt"', output)
        self.assertNotIn("/doctor", output)

    def test_shell_exit_works(self) -> None:
        with patch("subify.shell.ui.render_shell_exit") as render_exit:
            should_continue = execute_shell_line("/exit", Mock(return_value=0))

        self.assertFalse(should_continue)
        render_exit.assert_called_once()

    def test_ctrl_c_must_be_pressed_twice_to_exit_shell_without_stacked_hint(self) -> None:
        calls = 0

        def input_reader(_prompt: str) -> str:
            nonlocal calls
            calls += 1
            raise KeyboardInterrupt

        with (
            patch("subify.shell.ui.clear_terminal"),
            patch("subify.shell.ui.render_welcome"),
            patch("subify.shell.ui.render_shell_footer"),
            patch("subify.shell.ui.render_shell_interrupt_hint") as render_hint,
            patch("subify.shell.ui.render_shell_exit") as render_exit,
            patch("subify.shell.ui.print_message"),
        ):
            exit_code = start_shell(Mock(return_value=0), input_reader=input_reader)

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls, 2)
        render_hint.assert_not_called()
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

    def test_slash_process_routes_to_shared_command_dispatcher(self) -> None:
        dispatcher = Mock(return_value=0)

        execute_shell_line('/process "C:\\Videos\\lesson with spaces.mp4"', dispatcher)

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
