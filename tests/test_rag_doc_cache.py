"""Tes cache dokumen RAG di disk (`src/rag_engine.py`).

Cache ini ada karena parsing penuh Materi (ratusan PDF via pypdf) memakan beberapa menit
dan cache memori saja hilang tiap proses restart. Seluruh tes di sini memakai loader tiruan
supaya tidak pernah menyentuh korpus Materi asli.
"""

import os
import tempfile
import unittest
from unittest import mock

import src.rag_engine as rag_engine


class RagDocsDiskCacheTests(unittest.TestCase):
    def setUp(self):
        fd, self.cache_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(self.cache_path)  # mulai dari kondisi tanpa cache
        rag_engine.clear_rag_cache()
        self.addCleanup(rag_engine.clear_rag_cache)
        self.addCleanup(self._remove_cache_files)

    def _remove_cache_files(self):
        for path in (self.cache_path, f"{self.cache_path}.tmp"):
            if os.path.exists(path):
                os.remove(path)

    def _patch_loaders(self, fingerprint="fp-1", content="isi asli", index_dir=None):
        """Ganti ketiga loader + sidik jari dengan tiruan; kembalikan mock loader PDF-nya."""
        pdf_loader = mock.Mock(
            return_value=[{"source": "a.pdf", "title": "A", "content": content, "type": "pdf"}]
        )
        patcher = mock.patch.multiple(
            rag_engine,
            RAG_DOCS_CACHE_FILE=self.cache_path,
            RAG_INDEX_DIR=index_dir or os.path.dirname(self.cache_path),
            _materi_fingerprint=mock.Mock(return_value=fingerprint),
            _load_markdown_files=mock.Mock(return_value=[]),
            _load_json_knowledge_files=mock.Mock(return_value=[]),
            _load_pdf_files=pdf_loader,
        )
        return pdf_loader, patcher

    def test_restart_reads_from_disk_instead_of_reparsing(self):
        pdf_loader, patcher = self._patch_loaders()
        with patcher:
            first = rag_engine._load_all_documents()
            self.assertEqual(pdf_loader.call_count, 1)
            self.assertTrue(os.path.exists(self.cache_path), "cache disk seharusnya ditulis")

            # Simulasi proses baru: cache memori hilang, cache disk tetap ada.
            rag_engine.clear_rag_cache()
            second = rag_engine._load_all_documents()

        self.assertEqual(second, first)
        self.assertEqual(pdf_loader.call_count, 1, "PDF tidak boleh diparse ulang saat cache sahih")

    def test_changed_materi_invalidates_cache(self):
        _, patcher = self._patch_loaders(fingerprint="fp-1", content="isi lama")
        with patcher:
            rag_engine._load_all_documents()
        rag_engine.clear_rag_cache()

        # Sidik jari berubah = ada berkas Materi yang berubah/ditambah/dihapus.
        pdf_loader, patcher = self._patch_loaders(fingerprint="fp-2", content="isi baru")
        with patcher:
            docs = rag_engine._load_all_documents()

        self.assertEqual(pdf_loader.call_count, 1, "sidik jari berbeda harus memicu parse ulang")
        self.assertEqual(docs[0]["content"], "isi baru")

    def test_force_reload_bypasses_disk_cache(self):
        _, patcher = self._patch_loaders(content="isi lama")
        with patcher:
            rag_engine._load_all_documents()
        rag_engine.clear_rag_cache()

        pdf_loader, patcher = self._patch_loaders(content="isi baru")
        with patcher:
            docs = rag_engine._load_all_documents(force_reload=True)

        self.assertEqual(pdf_loader.call_count, 1)
        self.assertEqual(docs[0]["content"], "isi baru")

    def test_unwritable_cache_dir_does_not_break_parsing(self):
        # RAG_INDEX_DIR diarahkan ke dalam sebuah *berkas*, jadi os.makedirs pasti gagal.
        blocker = tempfile.NamedTemporaryFile(suffix=".lock", delete=False)
        blocker.close()
        self.addCleanup(os.remove, blocker.name)

        pdf_loader, patcher = self._patch_loaders(index_dir=os.path.join(blocker.name, "sub"))
        with patcher:
            docs = rag_engine._load_all_documents()

        self.assertEqual(pdf_loader.call_count, 1)
        self.assertEqual(docs[0]["content"], "isi asli", "parsing harus tetap mengembalikan hasil")

    def test_corrupt_cache_file_is_ignored(self):
        with open(self.cache_path, "w", encoding="utf-8") as f:
            f.write("{bukan json yang sah")

        pdf_loader, patcher = self._patch_loaders()
        with patcher:
            docs = rag_engine._load_all_documents()

        self.assertEqual(pdf_loader.call_count, 1, "cache rusak harus diabaikan, bukan bikin gagal")
        self.assertEqual(docs[0]["content"], "isi asli")


if __name__ == "__main__":
    unittest.main()
