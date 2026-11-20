"""The reranker uses a cached, lightweight ONNX session without loading Torch."""
import functools
import sys
import unittest
from pathlib import Path
from runpy import run_module
from unittest.mock import MagicMock, patch

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


class LowMemoryRerankerTests(unittest.TestCase):
    def _load_with_stubs(self, *, static_batch=None):
        st = MagicMock()
        st.cache_resource.side_effect = lambda **kwargs: (
            lambda fn: functools.lru_cache(maxsize=1)(fn)
        )
        hf = MagicMock()
        hf.hf_hub_download.side_effect = lambda **kwargs: kwargs["filename"]
        tokenizer = MagicMock()
        tokenizer.encode.return_value = MagicMock(
            ids=[0, 27, 2, 2, 81, 2],
            attention_mask=[1, 1, 1, 1, 1, 1],
            type_ids=[0, 0, 0, 0, 0, 0],
        )
        tokenizers = MagicMock()
        tokenizers.Tokenizer.from_file.return_value = tokenizer

        ort = MagicMock()
        session = ort.InferenceSession.return_value
        batch = static_batch if static_batch is not None else "batch"
        fields = [
            MagicMock(name="input_ids", shape=[batch, "seq"]),
            MagicMock(name="attention_mask", shape=[batch, "seq"]),
        ]
        fields[0].name, fields[1].name = "input_ids", "attention_mask"
        session.get_inputs.return_value = fields
        session.run.return_value = [np.full((batch if isinstance(batch, int) else 1, 1),
                                            1.0986122886681098, dtype=np.float32)]
        deps = {
            "streamlit": st,
            "newspaper": MagicMock(),
            "bs4": MagicMock(),
            "modules.news_summarizer": MagicMock(),
            "huggingface_hub": hf,
            "tokenizers": tokenizers,
            "onnxruntime": ort,
        }
        return deps, st, hf, tokenizers, tokenizer, ort, session

    def test_first_inference_only_downloads_int8_and_tokenizer_once(self):
        deps, st, hf, tokenizers, tokenizer, ort, session = self._load_with_stubs()
        with patch.dict(sys.modules, deps):
            m = run_module("modules.news_ai")
            hf.hf_hub_download.assert_not_called()
            ort.InferenceSession.assert_not_called()

            result = m["similarity_check"]("test summary", "test title")
            self.assertEqual(result["score"], 75.0)
            self.assertEqual(result["score_hundredths"], 7500)
            self.assertAlmostEqual(result["normalized"], .75, places=5)
            self.assertEqual(result["token_count"], 6)
            self.assertIn("ONNX INT8", result["model_name"])
            tokenizer.encode.assert_called_once_with(
                "test summary", "test title", add_special_tokens=True,
            )
            self.assertEqual(hf.hf_hub_download.call_count, 2)
            self.assertEqual(
                {c.kwargs["filename"] for c in hf.hf_hub_download.call_args_list},
                {"onnx/model_int8.onnx", "tokenizer.json"},
            )
            self.assertTrue(all(
                c.kwargs["revision"] == m["RERANKER_ONNX_REVISION"]
                for c in hf.hf_hub_download.call_args_list
            ))
            tokenizer.enable_truncation.assert_called_once_with(
                max_length=512, strategy="longest_first",
            )
            options = ort.SessionOptions.return_value
            self.assertEqual(options.intra_op_num_threads, 2)
            self.assertFalse(options.enable_mem_pattern)
            self.assertEqual(
                ort.InferenceSession.call_args.kwargs["providers"],
                ["CPUExecutionProvider"],
            )

            m["similarity_check"]("another summary", "another title")
            self.assertEqual(hf.hf_hub_download.call_count, 2)
            ort.InferenceSession.assert_called_once()
            self.assertEqual(session.run.call_count, 2)

    def test_fixed_batch_onnx_is_supported_with_identical_pairs(self):
        deps, _, _, _, _, _, session = self._load_with_stubs(static_batch=8)
        with patch.dict(sys.modules, deps):
            result = run_module("modules.news_ai")["similarity_check"](
                "summary", "title",
            )
            self.assertEqual(result["score"], 75.0)
            feed = session.run.call_args.args[1]
            self.assertEqual(feed["input_ids"].shape, (8, 6))
            np.testing.assert_array_equal(feed["input_ids"][0], feed["input_ids"][7])
            self.assertEqual(feed["attention_mask"].dtype, np.int64)

    def test_fixed_sequence_length_pads_with_xlm_roberta_pad_id(self):
        deps, _, _, _, _, _, session = self._load_with_stubs()
        inputs = session.get_inputs.return_value
        inputs[0].shape, inputs[1].shape = [1, 8], [1, 8]
        with patch.dict(sys.modules, deps):
            run_module("modules.news_ai")["similarity_check"]("sum", "title")
        feed = session.run.call_args.args[1]
        self.assertEqual(feed["input_ids"][0, -2:].tolist(), [1, 1])
        self.assertEqual(feed["attention_mask"][0, -2:].tolist(), [0, 0])

    def test_dependency_and_cold_start_contracts(self):
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        code = (ROOT / "modules/news_ai.py").read_text(encoding="utf-8")
        self.assertIn("onnxruntime", requirements)
        self.assertIn("tokenizers", requirements)
        self.assertNotIn("\ntorch\n", requirements)
        self.assertNotIn("\ntransformers\n", requirements)
        self.assertNotIn("AutoModelForSequenceClassification", code)
        self.assertNotIn("import torch", code)
        self.assertIn("from newspaper import Article", code)

    def test_unavailable_model_has_readable_error_with_original_cause(self):
        deps, _, hf, _, _, _, _ = self._load_with_stubs()
        hf.hf_hub_download.side_effect = OSError("model network unavailable")
        with patch.dict(sys.modules, deps):
            m = run_module("modules.news_ai")
            with self.assertRaisesRegex(RuntimeError, "모델을 불러오지 못했습니다"):
                m["load_ai_model"]()


if __name__ == "__main__":
    unittest.main()
