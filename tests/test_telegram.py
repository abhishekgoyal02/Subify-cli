import unittest
import runpy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from subify.errors import InputValidationError, PackagingError, TranscriptionError
from subify.models import PipelineResult
from telegram.bot import TOKEN_ENV_VAR, TelegramConfigError, load_bot_token
from telegram.handlers import TelegramVideoHandler, telegram_error_message


class FakeTelegramClient:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []
        self.edits: list[tuple[int, int, str]] = []
        self.documents: list[tuple[int, Path, str | None, bool]] = []
        self.downloaded_paths: list[Path] = []
        self.file_info = {"file_path": "videos/source.mp4"}

    def send_message(self, chat_id: int, text: str):
        self.messages.append((chat_id, text))
        return {"message_id": len(self.messages)}

    def edit_message_text(self, chat_id: int, message_id: int, text: str):
        self.edits.append((chat_id, message_id, text))
        return {"message_id": message_id}

    def get_file(self, file_id: str):
        return self.file_info

    def download_file(self, file_path: str, destination: Path):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"video")
        self.downloaded_paths.append(destination)
        return destination

    def send_document(self, chat_id: int, document_path: Path, *, caption: str | None = None):
        self.documents.append((chat_id, document_path, caption, document_path.exists()))
        return {"document": {"file_name": document_path.name}}


def video_update(file_name: str = "lesson.mp4"):
    return {
        "update_id": 1,
        "message": {
            "chat": {"id": 42},
            "video": {"file_id": "file-1", "file_name": file_name},
        },
    }


def document_update(file_name: str = "lesson.mp4"):
    return {
        "update_id": 1,
        "message": {
            "chat": {"id": 42},
            "document": {"file_id": "file-1", "file_name": file_name},
        },
    }


class TelegramConfigTests(unittest.TestCase):
    def test_bot_startup_configuration_reads_token(self) -> None:
        self.assertEqual(load_bot_token({TOKEN_ENV_VAR: " token "}), "token")

    def test_missing_token_raises_configuration_error(self) -> None:
        with self.assertRaises(TelegramConfigError):
            load_bot_token({})

    @patch("telegram.bot.main", return_value=0)
    def test_package_entrypoint_delegates_to_bot_main(self, main) -> None:
        with self.assertRaises(SystemExit) as context:
            runpy.run_module("telegram", run_name="__main__")

        self.assertEqual(context.exception.code, 0)
        main.assert_called_once_with()


class TelegramHandlerTests(unittest.TestCase):
    def test_no_video_prompts_user_for_mp4(self) -> None:
        client = FakeTelegramClient()

        TelegramVideoHandler(client).handle_update({"message": {"chat": {"id": 42}, "text": "hello"}})

        self.assertEqual(client.messages, [(42, "Please send an .mp4 video file.")])

    def test_unsupported_file_is_rejected_before_download(self) -> None:
        client = FakeTelegramClient()

        TelegramVideoHandler(client).handle_update(video_update("lesson.mov"))

        self.assertEqual(client.messages, [(42, "Only .mp4 videos are supported in this version.")])
        self.assertEqual(client.downloaded_paths, [])

    @patch("subify.pipeline.process_video")
    def test_document_video_handling_calls_pipeline(self, process_video) -> None:
        client = FakeTelegramClient()

        def run_pipeline(video_path: Path, *, output_dir: Path, progress_callback):
            zip_path = output_dir / "lesson_subify.zip"
            output_dir.mkdir(parents=True, exist_ok=True)
            zip_path.write_bytes(b"zip")
            return PipelineResult(zip_path=zip_path)

        process_video.side_effect = run_pipeline

        TelegramVideoHandler(client).handle_update(document_update())

        process_video.assert_called_once()
        self.assertEqual(len(client.documents), 1)

    @patch("subify.pipeline.process_video")
    def test_valid_video_handling_calls_pipeline_with_downloaded_file(self, process_video) -> None:
        client = FakeTelegramClient()

        def run_pipeline(video_path: Path, *, output_dir: Path, progress_callback):
            self.assertEqual(video_path.name, "lesson.mp4")
            self.assertEqual(output_dir.name, "output")
            progress_callback(("audio_extraction", "start"))
            zip_path = output_dir / "lesson_subify.zip"
            output_dir.mkdir(parents=True, exist_ok=True)
            zip_path.write_bytes(b"zip")
            return PipelineResult(zip_path=zip_path)

        process_video.side_effect = run_pipeline

        TelegramVideoHandler(client).handle_update(video_update())

        self.assertEqual(process_video.call_count, 1)
        self.assertTrue(any("Extracting audio" in edit[2] for edit in client.edits))

    @patch("subify.pipeline.process_video")
    def test_unsafe_filename_is_sanitized_inside_workspace(self, process_video) -> None:
        client = FakeTelegramClient()
        observed_path: list[Path] = []

        def run_pipeline(video_path: Path, *, output_dir: Path, progress_callback):
            observed_path.append(video_path)
            zip_path = output_dir / "lesson_subify.zip"
            output_dir.mkdir(parents=True, exist_ok=True)
            zip_path.write_bytes(b"zip")
            return PipelineResult(zip_path=zip_path)

        process_video.side_effect = run_pipeline

        TelegramVideoHandler(client).handle_update(video_update(r"..\..\lesson.mp4"))

        self.assertEqual(observed_path[0].name, "lesson.mp4")
        self.assertNotIn("..", observed_path[0].parts)

    @patch("subify.pipeline.process_video")
    def test_object_style_video_message_is_supported(self, process_video) -> None:
        client = FakeTelegramClient()
        update = {
            "message": SimpleNamespace(
                chat=SimpleNamespace(id=42),
                video=SimpleNamespace(file_id="file-1", file_name="lesson.mp4"),
            )
        }

        def run_pipeline(_video_path: Path, *, output_dir: Path, progress_callback):
            zip_path = output_dir / "lesson_subify.zip"
            output_dir.mkdir(parents=True, exist_ok=True)
            zip_path.write_bytes(b"zip")
            return PipelineResult(zip_path=zip_path)

        process_video.side_effect = run_pipeline

        TelegramVideoHandler(client).handle_update(update)

        process_video.assert_called_once()

    @patch("subify.pipeline.process_video")
    def test_successful_pipeline_result_sends_zip(self, process_video) -> None:
        client = FakeTelegramClient()

        def run_pipeline(_video_path: Path, *, output_dir: Path, progress_callback):
            zip_path = output_dir / "lesson_subify.zip"
            output_dir.mkdir(parents=True, exist_ok=True)
            zip_path.write_bytes(b"zip")
            return PipelineResult(zip_path=zip_path)

        process_video.side_effect = run_pipeline

        TelegramVideoHandler(client).handle_update(video_update())

        self.assertEqual(len(client.documents), 1)
        self.assertEqual(client.documents[0][0], 42)
        self.assertEqual(client.documents[0][1].name, "lesson_subify.zip")
        self.assertTrue(client.documents[0][3])

    @patch("subify.pipeline.process_video")
    def test_temporary_files_are_cleaned_up_after_success(self, process_video) -> None:
        client = FakeTelegramClient()
        observed_paths: list[Path] = []

        def run_pipeline(video_path: Path, *, output_dir: Path, progress_callback):
            zip_path = output_dir / "lesson_subify.zip"
            output_dir.mkdir(parents=True, exist_ok=True)
            zip_path.write_bytes(b"zip")
            observed_paths.extend([video_path, output_dir, zip_path])
            return PipelineResult(zip_path=zip_path)

        process_video.side_effect = run_pipeline

        TelegramVideoHandler(client).handle_update(video_update())

        self.assertTrue(observed_paths)
        for path in observed_paths:
            self.assertFalse(path.exists())

    @patch("subify.pipeline.process_video")
    def test_temporary_files_are_cleaned_up_after_pipeline_failure(self, process_video) -> None:
        client = FakeTelegramClient()
        observed_input: list[Path] = []

        def fail_pipeline(video_path: Path, *, output_dir: Path, progress_callback):
            observed_input.append(video_path)
            raise TranscriptionError("Transcription failed: internal")

        process_video.side_effect = fail_pipeline

        TelegramVideoHandler(client).handle_update(video_update())

        self.assertTrue(observed_input)
        self.assertFalse(observed_input[0].exists())

    @patch("subify.pipeline.process_video", side_effect=InputValidationError("The current supported limit is 12 minutes."))
    def test_duration_failure_is_user_friendly(self, _process_video) -> None:
        client = FakeTelegramClient()

        TelegramVideoHandler(client).handle_update(video_update())

        self.assertIn("The maximum supported video length is 12 minutes.", client.messages[-1][1])

    @patch("subify.pipeline.process_video", side_effect=TranscriptionError("Transcription failed: stack details"))
    def test_pipeline_failure_is_user_friendly(self, _process_video) -> None:
        client = FakeTelegramClient()

        TelegramVideoHandler(client).handle_update(video_update())

        self.assertEqual(
            client.messages[-1],
            (42, "Processing failed:\nSubify could not generate a transcript for this video."),
        )

    @patch("telegram.handlers.LOGGER.exception")
    @patch("subify.pipeline.process_video", side_effect=RuntimeError("Traceback: secret path"))
    def test_unknown_errors_do_not_expose_raw_tracebacks(self, _process_video, log_exception) -> None:
        client = FakeTelegramClient()

        TelegramVideoHandler(client).handle_update(video_update())

        self.assertIn("An unexpected error occurred", client.messages[-1][1])
        self.assertNotIn("Traceback", client.messages[-1][1])
        self.assertNotIn("secret path", client.messages[-1][1])
        log_exception.assert_called_once()

    def test_known_error_mapping_does_not_expose_internal_paths(self) -> None:
        message = telegram_error_message(
            InputValidationError(r"Input file does not exist: C:\temp\subify-telegram-x\lesson.mp4")
        )

        self.assertNotIn("C:\\temp", message)
        self.assertEqual(message, "This video could not be read. Please send a valid .mp4 file.")

    @patch("subify.pipeline.process_video", return_value=PipelineResult(zip_path=None))
    def test_missing_zip_result_is_reported_as_packaging_failure(self, _process_video) -> None:
        client = FakeTelegramClient()

        TelegramVideoHandler(client).handle_update(video_update())

        self.assertIn("Subify could not package the processed files.", client.messages[-1][1])

    @patch("subify.pipeline.process_video")
    def test_nonexistent_zip_result_is_reported_as_packaging_failure(self, process_video) -> None:
        client = FakeTelegramClient()

        def run_pipeline(_video_path: Path, *, output_dir: Path, progress_callback):
            return PipelineResult(zip_path=output_dir / "missing.zip")

        process_video.side_effect = run_pipeline

        TelegramVideoHandler(client).handle_update(video_update())

        self.assertEqual(client.documents, [])
        self.assertIn("Subify could not package the processed files.", client.messages[-1][1])

    def test_cli_import_does_not_import_telegram_adapter(self) -> None:
        import sys

        sys.modules.pop("subify.cli", None)
        sys.modules.pop("telegram.bot", None)
        sys.modules.pop("telegram.handlers", None)

        import subify.cli  # noqa: F401

        self.assertNotIn("telegram.bot", sys.modules)
        self.assertNotIn("telegram.handlers", sys.modules)


if __name__ == "__main__":
    unittest.main()
