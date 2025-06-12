import unittest
from src.utils.srt_utils import SRTUtils

class TestSRTUtils(unittest.TestCase):
    def setUp(self):
        self.long_text = "This is a test paragraph.\n\n" * 100  # Create a long text with multiple paragraphs
        self.multibyte_text = "Hello 世界! This is a test with multibyte characters. 你好！" * 50
        self.short_text = "This is a short text."

    def test_split_to_token_chunks(self):
        # Test with short text
        chunks = SRTUtils.split_to_token_chunks(self.short_text, max_tokens=10)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], self.short_text)

        # Test with long text
        chunks = SRTUtils.split_to_token_chunks(self.long_text, max_tokens=100)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(SRTUtils.get_tokenizer().encode(chunk)), 100)

        # Test with multibyte characters
        chunks = SRTUtils.split_to_token_chunks(self.multibyte_text, max_tokens=100)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(SRTUtils.get_tokenizer().encode(chunk)), 100)

    def test_smart_chunk_by_paragraphs(self):
        # Test with short text
        chunks = SRTUtils.smart_chunk_by_paragraphs(self.short_text, max_tokens=10)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], self.short_text)

        # Test with long text
        chunks = SRTUtils.smart_chunk_by_paragraphs(self.long_text, max_tokens=100)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(SRTUtils.get_tokenizer().encode(chunk)), 100)
            # Verify that paragraphs are preserved
            self.assertIn("This is a test paragraph.", chunk)

        # Test with multibyte characters
        chunks = SRTUtils.smart_chunk_by_paragraphs(self.multibyte_text, max_tokens=100)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(SRTUtils.get_tokenizer().encode(chunk)), 100)

    def test_different_models(self):
        # Test with different models
        models = ["gpt-4", "gpt-3.5-turbo", "text-davinci-003"]
        for model in models:
            chunks = SRTUtils.split_to_token_chunks(self.short_text, max_tokens=10, model=model)
            self.assertEqual(len(chunks), 1)
            self.assertEqual(chunks[0], self.short_text)

    def test_edge_cases(self):
        # Test with empty text
        chunks = SRTUtils.split_to_token_chunks("", max_tokens=10)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], "")

        # Test with very large max_tokens
        chunks = SRTUtils.split_to_token_chunks(self.long_text, max_tokens=1000000)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], self.long_text)

        # Test with max_tokens=1
        chunks = SRTUtils.split_to_token_chunks("Hello world", max_tokens=1)
        self.assertGreater(len(chunks), 1)

if __name__ == '__main__':
    unittest.main() 