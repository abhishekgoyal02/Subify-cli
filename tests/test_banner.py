import unittest
from unittest import mock

from subify import banner


class PipelineArtworkTests(unittest.TestCase):
    def test_default_waveform_keeps_original_text_and_dim_style(self):
        top, base = banner._build_waveform().renderables

        self.assertEqual(top.plain, "  ▄▄      ▄▄      ▄▄      ▄▄")
        self.assertEqual(base.plain, " ████    ████    ████    ████")
        self.assertEqual(
            [span.style for span in top.spans],
            ["dim", "dim", "dim", "dim"],
        )
        self.assertEqual(
            [span.style for span in base.spans],
            ["dim", "dim", "dim", "dim"],
        )

    def test_completed_stages_remain_highlighted(self):
        top, base = banner._build_waveform(stage=3).renderables

        expected_styles = [
            "#CC7A29",
            "#CC7A29",
            "#CC7A29",
            "dim",
        ]
        self.assertEqual([span.style for span in top.spans], expected_styles)
        self.assertEqual([span.style for span in base.spans], expected_styles)

    def test_all_four_stages_can_be_completed(self):
        top, base = banner._build_waveform(stage=4).renderables

        self.assertEqual(
            [span.style for span in top.spans],
            ["#CC7A29"] * 4,
        )
        self.assertEqual(
            [span.style for span in base.spans],
            ["#CC7A29"] * 4,
        )

    def test_invalid_stage_is_rejected(self):
        for stage in (-1, 5):
            with self.subTest(stage=stage):
                with self.assertRaises(ValueError):
                    banner._build_waveform(stage)

    def test_pipeline_updates_only_the_existing_waveform_rows(self):
        console = mock.Mock()
        console.is_terminal = True
        console.width = 80
        pipeline = banner.PipelineDisplay(console=console, stage=0)

        pipeline.start()
        pipeline.update(1)
        pipeline.update(2)
        pipeline.stop()

        self.assertEqual(console.print.call_count, 3)
        self.assertIsInstance(console.print.call_args_list[0].args[0], banner.Group)
        for call in console.print.call_args_list[1:]:
            self.assertIsInstance(call.args[0], banner.Align)
            self.assertIsInstance(call.args[0].renderable, banner.Group)
        self.assertEqual(console.control.call_count, 4)

    def test_completed_stages_do_not_regress(self):
        console = mock.Mock()
        console.is_terminal = True
        console.width = 80
        pipeline = banner.PipelineDisplay(console=console, stage=0)

        pipeline.update(3)
        pipeline.update(1)

        self.assertEqual(pipeline.stage, 3)
        waveform = console.print.call_args.args[0].renderable
        top, _base = waveform.renderables
        self.assertEqual(
            [span.style for span in top.spans],
            ["#CC7A29", "#CC7A29", "#CC7A29", "dim"],
        )

    def test_stop_does_not_render_the_banner_again(self):
        console = mock.Mock()
        console.is_terminal = True
        console.width = 80
        pipeline = banner.PipelineDisplay(console=console)

        pipeline.start()
        pipeline.stop()

        console.print.assert_called_once()

    def test_output_tracking_restores_cursor_below_processing_output(self):
        console = mock.Mock()
        console.is_terminal = True
        console.width = 80
        pipeline = banner.PipelineDisplay(console=console)

        pipeline.record_output("First line\nSecond line\n")
        pipeline.update(1)

        move_up = console.control.call_args_list[0].args[0]
        move_down = console.control.call_args_list[1].args[0]
        self.assertIn("\x1b[15A", str(move_up))
        self.assertIn("\x1b[13B", str(move_down))

    @mock.patch("subify.banner.PipelineDisplay")
    def test_display_and_update_share_one_pipeline_instance(
        self, pipeline_class
    ):
        pipeline = pipeline_class.return_value

        displayed_pipeline = banner.display_startup_banner(stage=0)
        banner.update_pipeline(stage=2)
        banner.stop_pipeline()

        self.assertIs(displayed_pipeline, pipeline)
        pipeline.start.assert_called_once_with()
        pipeline.update.assert_called_once_with(2)
        pipeline.stop.assert_called_once_with()
        self.assertIsNone(banner._active_pipeline)

    @mock.patch("subify.banner.PipelineDisplay")
    def test_display_stops_an_existing_pipeline_before_restarting(
        self, pipeline_class
    ):
        existing_pipeline = mock.Mock()
        banner._active_pipeline = existing_pipeline

        banner.display_startup_banner()
        banner.stop_pipeline()

        existing_pipeline.stop.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
