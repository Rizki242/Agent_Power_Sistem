"""Tests for RAG API router."""

import unittest
from fastapi.testclient import TestClient
from api_server import app


class RAGApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_rag_status_endpoint(self):
        response = self.client.get("/api/rag/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("data", data)
        meta = data["data"]
        self.assertIn("is_available", meta)
        self.assertIn("chunk_size", meta)
        self.assertEqual(meta["chunk_size"], 1000)
        self.assertEqual(meta["chunk_overlap"], 200)

    def test_rag_chunks_inspection(self):
        response = self.client.get("/api/rag/chunks?limit=5")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        chunk_data = data["data"]
        self.assertIn("total", chunk_data)
        self.assertIn("chunks", chunk_data)
        self.assertIsInstance(chunk_data["chunks"], list)
        if chunk_data["chunks"]:
            first = chunk_data["chunks"][0]
            self.assertIn("chunk_id", first)
            self.assertIn("source", first)
            self.assertIn("content", first)
            self.assertIn("char_length", first)

    def test_rag_search_endpoint(self):
        response = self.client.post("/api/rag/search", json={"query": "vibrasi bearing", "top_k": 3})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("results", data)
        self.assertIn("engine", data)
        self.assertIsInstance(data["results"], list)


if __name__ == "__main__":
    unittest.main()

