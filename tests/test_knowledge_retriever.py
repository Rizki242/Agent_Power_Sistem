import unittest

from src.knowledge_retriever import (
    build_knowledge_context,
    load_knowledge_base,
    search_knowledge_base,
)


class KnowledgeRetrieverTests(unittest.TestCase):
    def test_load_knowledge_base_finds_documents(self):
        docs = load_knowledge_base(force_reload=True)
        self.assertGreater(len(docs), 0)
        first = docs[0]
        self.assertIn("source", first)
        self.assertIn("heading", first)
        self.assertIn("content", first)

    def test_search_rotor_bar_returns_relevant_guidance(self):
        results = search_knowledge_base("rotor bar sideband db", top_k=3)
        self.assertGreater(len(results), 0)
        found_rotor = any("rotor" in r["search_blob"] for r in results)
        self.assertTrue(found_rotor)

    def test_search_unbalance_voltage_nema(self):
        results = search_knowledge_base("voltage unbalance", top_k=3)
        self.assertGreater(len(results), 0)
        found_unbalance = any("unbalance" in r["search_blob"] or "tegangan" in r["search_blob"] for r in results)
        self.assertTrue(found_unbalance)

    def test_build_knowledge_context_produces_citations(self):
        context_str, citations = build_knowledge_context("sop pengambilan data motor")
        self.assertIsInstance(context_str, str)
        self.assertIsInstance(citations, list)
        if citations:
            self.assertIn("source", citations[0])
            self.assertIn("title", citations[0])

    def test_config_guidance_and_thresholds_indexed_via_mcsa_fallback(self):
        """Real config lives under data/MCSA/config/, not data/config/ (which
        doesn't exist); load_knowledge_base() must fall back there instead of
        silently indexing nothing. Regression guard for the bug fixed in
        commit f9ce79b."""
        docs = load_knowledge_base(force_reload=True)
        sources = {d["source"] for d in docs}
        self.assertIn("ESA/MCSA International Guidance", sources)
        self.assertIn("Thresholds Standard MCSA", sources)


if __name__ == "__main__":
    unittest.main()
