"""AI inference is deferred until the first similarity calculation.

This regression test uses stubs to avoid downloading model weights in CI.
"""
import functools
import sys
import unittest
from runpy import run_module
from unittest.mock import MagicMock, patch


class LazyRerankerTests(unittest.TestCase):
    def test_app_import_does_not_load_model_but_similarity_check_does(self):
        st = MagicMock()
        st.cache_resource.side_effect = lambda fn: functools.lru_cache(maxsize=1)(fn)
        transformers = MagicMock()
        tokenizer = MagicMock()
        inputs = {"attention_mask": MagicMock()}
        inputs["attention_mask"].sum.return_value.item.return_value = 12
        tokenizer.return_value = inputs
        model = MagicMock()
        logits = MagicMock()
        logits.item.return_value = 0.5
        model.return_value.logits.squeeze.return_value = logits
        transformers.AutoTokenizer.from_pretrained.return_value = tokenizer
        transformers.AutoModelForSequenceClassification.from_pretrained.return_value = model
        torch = MagicMock()
        torch.sigmoid.return_value.item.return_value = 0.75

        with patch.dict(sys.modules, {
            "streamlit": st,
            "newspaper": MagicMock(),
            "bs4": MagicMock(),
            "modules.news_summarizer": MagicMock(),
            "transformers": transformers,
            "torch": torch,
        }):
            module = run_module("modules.news_ai")
            transformers.AutoTokenizer.from_pretrained.assert_not_called()
            transformers.AutoModelForSequenceClassification.from_pretrained.assert_not_called()

            result = module["similarity_check"]("test summary", "test title")
            self.assertEqual(result["model_name"], "BAAI/bge-reranker-v2-m3")
            self.assertEqual(result["token_count"], 12)
            self.assertEqual(result["normalized"], 0.75)
            transformers.AutoTokenizer.from_pretrained.assert_called_once_with(
                "BAAI/bge-reranker-v2-m3"
            )
            transformers.AutoModelForSequenceClassification.from_pretrained.assert_called_once_with(
                "BAAI/bge-reranker-v2-m3"
            )
            model.eval.assert_called_once_with()

            # Streamlit's resource cache prevents a second model load.
            module["similarity_check"]("another summary", "another title")
            transformers.AutoModelForSequenceClassification.from_pretrained.assert_called_once()


if __name__ == "__main__":
    unittest.main()
