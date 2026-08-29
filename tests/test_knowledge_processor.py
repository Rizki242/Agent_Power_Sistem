import json
import os
import unittest

from src.knowledge_processor import (
    delete_knowledge_file,
    parse_markdown_file,
    process_and_save_knowledge_file,
)
from src.knowledge_retriever import search_knowledge_base


class KnowledgeProcessorTests(unittest.TestCase):
    def test_parse_markdown_with_frontmatter(self):
        md_text = """---
title: "SOP Pengujian Isolasi Motor"
tags: ["Megger", "Insulation", "SOP"]
level: "Intermediate"
source: "IEEE 43-2000"
---

# Pendahuluan
Pengujian tahanan isolasi dilakukan dengan Megger 1000V.

## Prosedur Pengujian
1. Lepas sambungan kabel motor dari panel.
2. Ukur tahanan fasa ke ground.
3. Nilai minimum adalah 1 M-Ohm per kV + 1 M-Ohm.
"""
        doc = parse_markdown_file(md_text, default_title="Fallback Title")
        self.assertEqual(doc["title"], "SOP Pengujian Isolasi Motor")
        self.assertIn("Megger", doc["tags"])
        self.assertEqual(doc["source"], "IEEE 43-2000")
        self.assertEqual(len(doc["sections"]), 2)
        self.assertEqual(doc["sections"][0]["heading"], "Pendahuluan")
        self.assertEqual(doc["sections"][1]["heading"], "Prosedur Pengujian")
        self.assertIn("1 M-Ohm", doc["sections"][1]["content"])

    def test_process_and_save_markdown_knowledge(self):
        md_content = b"""# Panduan Vibrasi Pompa
## Batas Vibrasi ISO 10816
Batas vibrasi overall untuk pompa sentrifugal kelas II adalah 2.8 mm/s RMS.
"""
        success, msg, doc = process_and_save_knowledge_file(
            file_name="panduan_vibrasi.md",
            file_bytes=md_content,
            custom_title="Panduan Vibrasi Pompa Baru",
            custom_tags=["Vibrasi", "ISO 10816"],
        )
        self.assertTrue(success)
        self.assertIn("panduan-vibrasi-pompa-baru.json", msg)

        # Verify it can be immediately retrieved by the knowledge retriever RAG search!
        results = search_knowledge_base("batas vibrasi iso 10816 pompa", top_k=2)
        self.assertGreater(len(results), 0)
        found = any("10816" in r["search_blob"] for r in results)
        self.assertTrue(found)

        # Cleanup test file
        del_ok, _ = delete_knowledge_file("panduan-vibrasi-pompa-baru.json")
        self.assertTrue(del_ok)


if __name__ == "__main__":
    unittest.main()
