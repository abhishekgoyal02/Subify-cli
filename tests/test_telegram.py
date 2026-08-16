import unittest
import runpy
import tempfile
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from unittest.mock import patch

from subify.errors import InputValidationError, PackagingError, TranscriptionError
from subify.models import PipelineResult
from telegram.bot import (
    DOWNLOAD_CHUNK_SIZE_BYTES,
    TOKEN_ENV_VAR,
    BotApiClient,
    TelegramApiError,
    TelegramConfigError,
    load_bot_token,
    run_polling,
)
from telegram.handlers import STATUS_UPDATE_STAGES, TelegramVideoHandler, telegram_error_message
from telegram.ux import (
    INITIAL_STATUS_MESSAGE,
    SUCCESS_STATUS_MESSAGE,
    TELEGRAM_STAGE_MESSAGES,
    UNSUPPORTED_FILE_MESSAGE,
    ZIP_CAPTION,
    NO_VIDEO_MESSAGE,
    pipeline_error_message,
    unknown_error_message,
)


class FakeTelegramClient:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []
        self.edits: list[tuple[int, int, str]] = []
        self.documents: list[tuple[int, Path, str | None, bool]] = []
        self.downloaded_paths: list[Path] = []
        self.file_info = {"file_path": "videos/source.mp4"}
        self.fail_edits = False

    def send_message(self, chat_id: int, text: str):
        self.messages.append((chat_id, text))
        return {"message_id": len(self.messages)}

    def edit_message_text(self, chat_id: int, message_id: int, text: str):
        if self.fail_edits:
            raise RuntimeError("edit failed")
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


def user_visible_texts(client: FakeTelegramClient) -> list[str]:
    texts = [text for _chat_id, text in client.messages]
    texts.extend(text for _chat_id, _message_id, text in client.edits)
    texts.extend(caption for _chat_id, _path, caption, _exists in client.documents if caption)
    return texts


def emoji_count(text: str) -> int:
    return sum(
        1
        for character in text
        if (
            "\U0001F300" <= character <= "\U0001FAFF"
            or "\u2600" <= character <= "\u27BF"
        )
    )


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

    @patch("telegram.bot.request.urlopen")
    def test_telegram_api_http_error_logs_description_without_token(self, urlopen) -> None:
        body = b'{"ok":false,"error_code":400,"description":"Bad Request: file is too big"}'
        urlopen.side_effect = HTTPError(
            "https://api.telegram.org/botsecret-token/getFile",
            400,
            "Bad Request",
            {},
            BytesIO(body),
        )
        client = BotApiClient("secret-token")

        with self.assertLogs("telegram.bot", level="ERROR") as logs:
            with self.assertRaises(TelegramApiError) as context:
                client.get_file("file-1")

        log_output = "\n".join(logs.output)
        self.assertIn("Bad Request: file is too big", log_output)
        self.assertIn("Bad Request: file is too big", str(context.exception))
        self.assertNotIn("secret-token", log_output)
        self.assertNotIn("secret-token", str(context.exception))

    @patch("telegram.bot.request.urlopen")
    def test_download_file_streams_to_disk_and_logs_breakdown_without_token(self, urlopen) -> None:
        captured = {"read_sizes": []}

        class FakeResponse:
            headers = {"Content-Length": "6"}

            def __init__(self) -> None:
                self._chunks = [b"abc", b"def", b""]

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def read(self, size=-1):
                captured["read_sizes"].append(size)
                return self._chunks.pop(0)

        def capture_url(url):
            captured["url"] = url
            return FakeResponse()

        urlopen.side_effect = capture_url

        with tempfile.TemporaryDirectory() as temp_dir_name:
            destination = Path(temp_dir_name) / "lesson.mp4"

            with self.assertLogs("telegram.bot", level="INFO") as logs:
                result = BotApiClient("secret-token").download_file("videos/source lesson.mp4", destination)

            self.assertEqual(result, destination)
            self.assertEqual(destination.read_bytes(), b"abcdef")
            self.assertFalse(destination.with_name("lesson.mp4.part").exists())

        log_output = "\n".join(logs.output)
        self.assertIn("Telegram file download breakdown", log_output)
        self.assertIn("bytes=6", log_output)
        self.assertIn("source lesson.mp4", log_output)
        self.assertNotIn("secret-token", log_output)
        self.assertTrue(captured["url"].endswith("/videos/source%20lesson.mp4"))
        self.assertEqual(captured["read_sizes"], [DOWNLOAD_CHUNK_SIZE_BYTES] * 3)

    @patch("telegram.bot.request.urlopen")
    def test_download_file_rejects_empty_response_and_removes_partial_file(self, urlopen) -> None:
        class FakeResponse:
            headers = {"Content-Length": "0"}

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def read(self, _size=-1):
                return b""

        urlopen.return_value = FakeResponse()

        with tempfile.TemporaryDirectory() as temp_dir_name:
            destination = Path(temp_dir_name) / "lesson.mp4"

            with self.assertRaises(TelegramApiError) as context:
                BotApiClient("secret-token").download_file("videos/lesson.mp4", destination)

            self.assertFalse(destination.exists())
            self.assertFalse(destination.with_name("lesson.mp4.part").exists())

        self.assertIn("empty", str(context.exception))
        self.assertNotIn("secret-token", str(context.exception))

    @patch("telegram.bot.request.urlopen")
    def test_download_file_rejects_incomplete_response_and_removes_partial_file(self, urlopen) -> None:
        class FakeResponse:
            headers = {"Content-Length": "6"}

            def __init__(self) -> None:
                self._chunks = [b"abc", b""]

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def read(self, _size=-1):
                return self._chunks.pop(0)

        urlopen.return_value = FakeResponse()

        with tempfile.TemporaryDirectory() as temp_dir_name:
            destination = Path(temp_dir_name) / "lesson.mp4"

            with self.assertRaises(TelegramApiError) as context:
                BotApiClient("secret-token").download_file("videos/lesson.mp4", destination)

            self.assertFalse(destination.exists())
            self.assertFalse(destination.with_name("lesson.mp4.part").exists())

        self.assertIn("incomplete", str(context.exception))
        self.assertNotIn("secret-token", str(context.exception))

    @patch("telegram.bot.request.urlopen")
    def test_download_file_http_error_exposes_safe_description(self, urlopen) -> None:
        body = b'{"ok":false,"error_code":404,"description":"Not Found"}'
        urlopen.side_effect = HTTPError(
            "https://api.telegram.org/file/botsecret-token/videos/lesson.mp4",
            404,
            "Not Found",
            {},
            BytesIO(body),
        )

        with tempfile.TemporaryDirectory() as temp_dir_name:
            destination = Path(temp_dir_name) / "lesson.mp4"

            with self.assertLogs("telegram.bot", level="ERROR") as logs:
                with self.assertRaises(TelegramApiError) as context:
                    BotApiClient("secret-token").download_file("videos/lesson.mp4", destination)

            self.assertFalse(destination.exists())
            self.assertFalse(destination.with_name("lesson.mp4.part").exists())

        log_output = "\n".join(logs.output)
        self.assertIn("Not Found", log_output)
        self.assertIn("Not Found", str(context.exception))
        self.assertNotIn("secret-token", log_output)
        self.assertNotIn("secret-token", str(context.exception))

    @patch("telegram.bot.uuid.uuid4")
    @patch("telegram.bot.request.urlopen")
    def test_send_document_uses_send_document_multipart_contract(self, urlopen, uuid4) -> None:
        captured = {}
        uuid4.return_value.hex = "fixedboundary"

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def read(self):
                return b'{"ok":true,"result":{"document":{"file_name":"lesson_subify.zip"}}}'

        def capture_request(req):
            captured["url"] = req.full_url
            captured["data"] = req.data
            captured["content_type"] = req.get_header("Content-type")
            return FakeResponse()

        urlopen.side_effect = capture_request

        with tempfile.TemporaryDirectory() as temp_dir_name:
            zip_path = Path(temp_dir_name) / "lesson_subify.zip"
            zip_path.write_bytes(b"PK\x03\x04zip")

            result = BotApiClient("secret-token").send_document(42, zip_path, caption=ZIP_CAPTION)

        body = captured["data"]
        self.assertEqual(result["document"]["file_name"], "lesson_subify.zip")
        self.assertTrue(captured["url"].endswith("/sendDocument"))
        self.assertIn("multipart/form-data; boundary=subify-fixedboundary", captured["content_type"])
        self.assertIn(b'name="chat_id"\r\n\r\n42\r\n', body)
        self.assertIn(f'name="caption"\r\n\r\n{ZIP_CAPTION}\r\n'.encode("utf-8"), body)
        self.assertIn(
            b'Content-Disposition: form-data; name="document"; filename="lesson_subify.zip"',
            body,
        )
        self.assertIn(b"Content-Type: application/zip\r\n\r\nPK\x03\x04zip", body)
        self.assertNotIn(b"secret-token", body)

    @patch("telegram.bot.request.urlopen")
    def test_send_document_api_failure_exposes_safe_description(self, urlopen) -> None:
        body = b'{"ok":false,"error_code":400,"description":"Bad Request: file must be non-empty"}'
        urlopen.side_effect = HTTPError(
            "https://api.telegram.org/botsecret-token/sendDocument",
            400,
            "Bad Request",
            {},
            BytesIO(body),
        )

        with tempfile.TemporaryDirectory() as temp_dir_name:
            zip_path = Path(temp_dir_name) / "lesson_subify.zip"
            zip_path.write_bytes(b"zip")

            with self.assertLogs("telegram.bot", level="ERROR") as logs:
                with self.assertRaises(TelegramApiError) as context:
                    BotApiClient("secret-token").send_document(42, zip_path)

        log_output = "\n".join(logs.output)
        self.assertIn("Bad Request: file must be non-empty", log_output)
        self.assertIn("Bad Request: file must be non-empty", str(context.exception))
        self.assertNotIn("secret-token", log_output)
        self.assertNotIn("secret-token", str(context.exception))

    def test_send_document_rejects_missing_file_before_upload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            missing_zip = Path(temp_dir_name) / "missing.zip"

            with self.assertRaises(TelegramApiError) as context:
                BotApiClient("secret-token").send_document(42, missing_zip)

        self.assertIn("Document file is not available", str(context.exception))

    def test_send_document_rejects_empty_file_before_upload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            empty_zip = Path(temp_dir_name) / "empty.zip"
            empty_zip.write_bytes(b"")

            with self.assertRaises(TelegramApiError) as context:
                BotApiClient("secret-token").send_document(42, empty_zip)

        self.assertIn("Document file is empty", str(context.exception))

    def test_polling_conflict_returns_cleanly_without_traceback(self) -> None:
        class ConflictClient:
            def get_updates(self, *, offset=None):
                raise TelegramApiError(
                    "getUpdates",
                    "Conflict: terminated by other getUpdates request",
                    status_code=409,
                )

        with self.assertLogs("telegram.bot", level="ERROR") as logs:
            exit_code = run_polling(ConflictClient(), handler=object())

        self.assertEqual(exit_code, 1)
        self.assertIn("another getUpdates consumer is already running", "\n".join(logs.output))
        self.assertNotIn("Traceback", "\n".join(logs.output))

    def test_centralized_telegram_copy_stays_short_and_one_emoji_max(self) -> None:
        messages = [
            INITIAL_STATUS_MESSAGE,
            SUCCESS_STATUS_MESSAGE,
            ZIP_CAPTION,
            NO_VIDEO_MESSAGE,
            UNSUPPORTED_FILE_MESSAGE,
            unknown_error_message(),
            *TELEGRAM_STAGE_MESSAGES.values(),
            pipeline_error_message(InputValidationError("The current supported limit is 12 minutes.")),
            pipeline_error_message(TranscriptionError("Transcription failed: internal")),
            pipeline_error_message(PackagingError("zip failed")),
            telegram_error_message(InputValidationError("Only .mp4 videos are supported in this version.")),
        ]

        for message in messages:
            with self.subTest(message=message):
                self.assertLessEqual(len(message), 110)
                self.assertLessEqual(emoji_count(message), 1)

    def test_stage_copy_covers_pipeline_stage_events(self) -> None:
        expected_stages = {
            "input_validation",
            "dependency_validation",
            "duration_validation",
            "disk_space_validation",
            "audio_extraction",
            "english_transcription",
            "srt_generation",
            "subtitle_embedding",
            "zip_packaging",
        }

        self.assertEqual(set(TELEGRAM_STAGE_MESSAGES), expected_stages)

    def test_status_update_stages_are_meaningful_slow_milestones(self) -> None:
        self.assertEqual(
            STATUS_UPDATE_STAGES,
            {
                "english_transcription",
                "subtitle_embedding",
                "zip_packaging",
            },
        )
        self.assertLess(set(STATUS_UPDATE_STAGES), set(TELEGRAM_STAGE_MESSAGES))


class TelegramHandlerTests(unittest.TestCase):
    def test_no_video_prompts_user_for_mp4(self) -> None:
        client = FakeTelegramClient()

        TelegramVideoHandler(client).handle_update({"message": {"chat": {"id": 42}, "text": "hello"}})

        self.assertEqual(client.messages, [(42, NO_VIDEO_MESSAGE)])

    def test_unsupported_file_is_rejected_before_download(self) -> None:
        client = FakeTelegramClient()

        TelegramVideoHandler(client).handle_update(video_update("lesson.mov"))

        self.assertEqual(client.messages, [(42, UNSUPPORTED_FILE_MESSAGE)])
        self.assertEqual(client.downloaded_paths, [])

    @patch("subify.pipeline.process_video")
    def test_document_video_handling_calls_pipeline(self, process_video) -> None:
        client = FakeTelegramClient()

        def run_pipeline(video_path: Path, *, output_dir: Path, progress_callback, transcription_function=None):
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

        def run_pipeline(video_path: Path, *, output_dir: Path, progress_callback, transcription_function=None):
            self.assertEqual(video_path.name, "lesson.mp4")
            self.assertEqual(output_dir.name, "output")
            progress_callback(("audio_extraction", "start"))
            progress_callback(("english_transcription", "start"))
            zip_path = output_dir / "lesson_subify.zip"
            output_dir.mkdir(parents=True, exist_ok=True)
            zip_path.write_bytes(b"zip")
            return PipelineResult(zip_path=zip_path)

        process_video.side_effect = run_pipeline

        TelegramVideoHandler(client).handle_update(video_update())

        self.assertEqual(process_video.call_count, 1)
        self.assertEqual(client.messages, [(42, INITIAL_STATUS_MESSAGE)])
        self.assertNotIn(TELEGRAM_STAGE_MESSAGES["audio_extraction"], [edit[2] for edit in client.edits])
        self.assertTrue(any(TELEGRAM_STAGE_MESSAGES["english_transcription"] == edit[2] for edit in client.edits))
        self.assertTrue(all(edit[1] == 1 for edit in client.edits))

    @patch("subify.pipeline.process_video")
    def test_unsafe_filename_is_sanitized_inside_workspace(self, process_video) -> None:
        client = FakeTelegramClient()
        observed_path: list[Path] = []

        def run_pipeline(video_path: Path, *, output_dir: Path, progress_callback, transcription_function=None):
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

        def run_pipeline(_video_path: Path, *, output_dir: Path, progress_callback, transcription_function=None):
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

        def run_pipeline(_video_path: Path, *, output_dir: Path, progress_callback, transcription_function=None):
            zip_path = output_dir / "lesson_subify.zip"
            output_dir.mkdir(parents=True, exist_ok=True)
            zip_path.write_bytes(b"zip")
            return PipelineResult(zip_path=zip_path)

        process_video.side_effect = run_pipeline

        TelegramVideoHandler(client).handle_update(video_update())

        self.assertEqual(len(client.documents), 1)
        self.assertEqual(client.documents[0][0], 42)
        self.assertEqual(client.documents[0][1].name, "lesson_subify.zip")
        self.assertEqual(client.documents[0][2], ZIP_CAPTION)
        self.assertTrue(client.documents[0][3])
        self.assertEqual(client.messages, [(42, INITIAL_STATUS_MESSAGE)])
        self.assertEqual(client.edits[-1], (42, 1, SUCCESS_STATUS_MESSAGE))

    @patch("subify.pipeline.process_video")
    def test_handler_passes_reusable_transcriber_to_pipeline(self, process_video) -> None:
        client = FakeTelegramClient()
        observed_transcription_functions = []

        class FakeTranscriber:
            def transcribe_audio(self, _audio_path: Path):
                return []

        fake_transcriber = FakeTranscriber()

        def run_pipeline(_video_path: Path, *, output_dir: Path, progress_callback, transcription_function=None):
            observed_transcription_functions.append(transcription_function)
            zip_path = output_dir / "lesson_subify.zip"
            output_dir.mkdir(parents=True, exist_ok=True)
            zip_path.write_bytes(b"zip")
            return PipelineResult(zip_path=zip_path)

        process_video.side_effect = run_pipeline

        TelegramVideoHandler(client, transcriber=fake_transcriber).handle_update(video_update())

        process_video.assert_called_once()
        self.assertEqual(len(observed_transcription_functions), 1)
        self.assertIs(observed_transcription_functions[0].__self__, fake_transcriber)
        self.assertIs(observed_transcription_functions[0].__func__, FakeTranscriber.transcribe_audio)

    @patch("subify.pipeline.process_video")
    def test_duplicate_stage_text_does_not_trigger_duplicate_edit(self, process_video) -> None:
        client = FakeTelegramClient()

        def run_pipeline(_video_path: Path, *, output_dir: Path, progress_callback, transcription_function=None):
            progress_callback(("english_transcription", "start"))
            progress_callback(("english_transcription", "start"))
            zip_path = output_dir / "lesson_subify.zip"
            output_dir.mkdir(parents=True, exist_ok=True)
            zip_path.write_bytes(b"zip")
            return PipelineResult(zip_path=zip_path)

        process_video.side_effect = run_pipeline

        TelegramVideoHandler(client).handle_update(video_update())

        transcription_edits = [
            edit for edit in client.edits
            if edit[2] == TELEGRAM_STAGE_MESSAGES["english_transcription"]
        ]
        self.assertEqual(len(transcription_edits), 1)
        self.assertEqual(len(client.messages), 1)

    @patch("subify.pipeline.process_video")
    def test_quick_pipeline_stages_do_not_trigger_status_edits(self, process_video) -> None:
        client = FakeTelegramClient()

        def run_pipeline(_video_path: Path, *, output_dir: Path, progress_callback, transcription_function=None):
            for stage in (
                "input_validation",
                "dependency_validation",
                "duration_validation",
                "disk_space_validation",
                "audio_extraction",
                "srt_generation",
            ):
                progress_callback((stage, "start"))
            zip_path = output_dir / "lesson_subify.zip"
            output_dir.mkdir(parents=True, exist_ok=True)
            zip_path.write_bytes(b"zip")
            return PipelineResult(zip_path=zip_path)

        process_video.side_effect = run_pipeline

        TelegramVideoHandler(client).handle_update(video_update())

        self.assertEqual(client.messages, [(42, INITIAL_STATUS_MESSAGE)])
        self.assertEqual(client.edits, [(42, 1, SUCCESS_STATUS_MESSAGE)])

    @patch("subify.pipeline.process_video")
    def test_meaningful_pipeline_stages_edit_same_status_message(self, process_video) -> None:
        client = FakeTelegramClient()

        def run_pipeline(_video_path: Path, *, output_dir: Path, progress_callback, transcription_function=None):
            for stage in (
                "english_transcription",
                "subtitle_embedding",
                "zip_packaging",
            ):
                progress_callback((stage, "start"))
            zip_path = output_dir / "lesson_subify.zip"
            output_dir.mkdir(parents=True, exist_ok=True)
            zip_path.write_bytes(b"zip")
            return PipelineResult(zip_path=zip_path)

        process_video.side_effect = run_pipeline

        TelegramVideoHandler(client).handle_update(video_update())

        self.assertEqual(client.messages, [(42, INITIAL_STATUS_MESSAGE)])
        self.assertEqual(
            client.edits,
            [
                (42, 1, TELEGRAM_STAGE_MESSAGES["english_transcription"]),
                (42, 1, TELEGRAM_STAGE_MESSAGES["subtitle_embedding"]),
                (42, 1, TELEGRAM_STAGE_MESSAGES["zip_packaging"]),
                (42, 1, SUCCESS_STATUS_MESSAGE),
            ],
        )

    @patch("subify.pipeline.process_video")
    def test_status_edit_failure_does_not_stop_processing_or_send_replacement_messages(self, process_video) -> None:
        client = FakeTelegramClient()
        client.fail_edits = True

        def run_pipeline(_video_path: Path, *, output_dir: Path, progress_callback, transcription_function=None):
            progress_callback(("english_transcription", "start"))
            zip_path = output_dir / "lesson_subify.zip"
            output_dir.mkdir(parents=True, exist_ok=True)
            zip_path.write_bytes(b"zip")
            return PipelineResult(zip_path=zip_path)

        process_video.side_effect = run_pipeline

        TelegramVideoHandler(client).handle_update(video_update())

        self.assertEqual(client.messages, [(42, INITIAL_STATUS_MESSAGE)])
        self.assertEqual(client.edits, [])
        self.assertEqual(len(client.documents), 1)

    @patch("subify.pipeline.process_video")
    def test_temporary_files_are_cleaned_up_after_success(self, process_video) -> None:
        client = FakeTelegramClient()
        observed_paths: list[Path] = []

        def run_pipeline(video_path: Path, *, output_dir: Path, progress_callback, transcription_function=None):
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

        def fail_pipeline(video_path: Path, *, output_dir: Path, progress_callback, transcription_function=None):
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

        self.assertEqual(len(client.messages), 1)
        self.assertIn("12 minutes", client.edits[-1][2])
        self.assertEqual(client.edits[-1][1], 1)

    @patch("subify.pipeline.process_video", side_effect=TranscriptionError("Transcription failed: stack details"))
    def test_pipeline_failure_is_user_friendly(self, _process_video) -> None:
        client = FakeTelegramClient()

        TelegramVideoHandler(client).handle_update(video_update())

        self.assertEqual(len(client.messages), 1)
        self.assertIn("whisper", client.edits[-1][2])
        self.assertEqual(client.edits[-1][1], 1)

    @patch("telegram.handlers.LOGGER.exception")
    @patch("subify.pipeline.process_video", side_effect=RuntimeError("Traceback: secret path"))
    def test_unknown_errors_do_not_expose_raw_tracebacks(self, _process_video, log_exception) -> None:
        client = FakeTelegramClient()

        TelegramVideoHandler(client).handle_update(video_update())

        self.assertEqual(len(client.messages), 1)
        self.assertEqual(client.edits[-1][2], unknown_error_message())
        self.assertNotIn("Traceback", client.edits[-1][2])
        self.assertNotIn("secret path", client.edits[-1][2])
        log_exception.assert_called_once()

    def test_known_error_mapping_does_not_expose_internal_paths(self) -> None:
        message = telegram_error_message(
            InputValidationError(r"Input file does not exist: C:\temp\subify-telegram-x\lesson.mp4")
        )

        self.assertNotIn("C:\\temp", message)
        self.assertEqual(message, "yeah... this video is kinda cursed. i can't read it.")

    @patch("subify.pipeline.process_video", return_value=PipelineResult(zip_path=None))
    def test_missing_zip_result_is_reported_as_packaging_failure(self, _process_video) -> None:
        client = FakeTelegramClient()

        TelegramVideoHandler(client).handle_update(video_update())

        self.assertEqual(len(client.messages), 1)
        self.assertIn("zip", client.edits[-1][2])
        self.assertIn("tragic", client.edits[-1][2])

    @patch("subify.pipeline.process_video")
    def test_empty_zip_result_is_reported_as_packaging_failure(self, process_video) -> None:
        client = FakeTelegramClient()

        def run_pipeline(_video_path: Path, *, output_dir: Path, progress_callback, transcription_function=None):
            zip_path = output_dir / "empty.zip"
            output_dir.mkdir(parents=True, exist_ok=True)
            zip_path.write_bytes(b"")
            return PipelineResult(zip_path=zip_path)

        process_video.side_effect = run_pipeline

        TelegramVideoHandler(client).handle_update(video_update())

        self.assertEqual(client.documents, [])
        self.assertEqual(len(client.messages), 1)
        self.assertIn("zip", client.edits[-1][2])

    @patch("subify.pipeline.process_video")
    def test_send_document_failure_reports_telegram_description(self, process_video) -> None:
        client = FakeTelegramClient()

        def fail_send_document(chat_id: int, document_path: Path, *, caption: str | None = None):
            raise TelegramApiError("sendDocument", "Bad Request: document send failed", status_code=400)

        def run_pipeline(_video_path: Path, *, output_dir: Path, progress_callback, transcription_function=None):
            zip_path = output_dir / "lesson_subify.zip"
            output_dir.mkdir(parents=True, exist_ok=True)
            zip_path.write_bytes(b"zip")
            return PipelineResult(zip_path=zip_path)

        client.send_document = fail_send_document
        process_video.side_effect = run_pipeline

        with self.assertLogs("telegram.handlers", level="ERROR") as logs:
            TelegramVideoHandler(client).handle_update(video_update())

        self.assertEqual(len(client.messages), 1)
        self.assertIn("telegram fumbled the handoff", client.edits[-1][2])
        self.assertIn("Bad Request: document send failed", client.edits[-1][2])
        self.assertIn("Bad Request: document send failed", "\n".join(logs.output))

    @patch("subify.pipeline.process_video")
    def test_nonexistent_zip_result_is_reported_as_packaging_failure(self, process_video) -> None:
        client = FakeTelegramClient()

        def run_pipeline(_video_path: Path, *, output_dir: Path, progress_callback, transcription_function=None):
            return PipelineResult(zip_path=output_dir / "missing.zip")

        process_video.side_effect = run_pipeline

        TelegramVideoHandler(client).handle_update(video_update())

        self.assertEqual(client.documents, [])
        self.assertEqual(len(client.messages), 1)
        self.assertIn("zip", client.edits[-1][2])

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
