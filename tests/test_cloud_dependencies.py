"""Cloud dependency-resolution checks for the original FP32 reranker."""
from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CloudDependencyTests(unittest.TestCase):
    def test_cpu_torch_backend_does_not_override_pypi_for_requests(self):
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        with (ROOT / "uv.toml").open("rb") as stream:
            config = tomllib.load(stream)
        self.assertEqual(config["pip"]["torch-backend"], "cpu")
        self.assertNotIn("--extra-index-url", requirements)
        self.assertIn("torch", requirements.splitlines())
        self.assertIn("requests>=2.31,<3", requirements.splitlines())
        self.assertIn("pyarrow>=24,<25", requirements.splitlines())

    def test_original_scoring_model_is_unchanged(self):
        source = (ROOT / "modules/news_ai.py").read_text(encoding="utf-8")
        self.assertIn('RERANKER_NAME = "BAAI/bge-reranker-v2-m3"', source)
        self.assertIn("from transformers import AutoModelForSequenceClassification", source)
        self.assertIn("@st.cache_resource", source)
        self.assertNotIn("onnxruntime", source)


if __name__ == "__main__":
    unittest.main()
