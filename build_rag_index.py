"""Script to build RAG index from VIBRASI and TRIBOLOGY knowledge base.

Usage:
    python build_rag_index.py [--force]

This will:
1. Load all documents from Materi/VIBRASI and Materi/TRIBOLOGY
2. Create embeddings using sentence-transformers
3. Build FAISS vector store
4. Save index to data/rag_index/
"""

import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(description="Build RAG index for MCSA Knowledge Base")
    parser.add_argument("--force", action="store_true", help="Force rebuild even if index exists")
    parser.add_argument("--test", type=str, help="Test query after building index")
    args = parser.parse_args()

    print("=" * 60)
    print("MCSA RAG Index Builder")
    print("=" * 60)

    try:
        from src.rag_engine import get_rag_engine, is_rag_available
    except ImportError as exc:
        print(f"ERROR: Cannot import rag_engine: {exc}")
        print("Make sure you are running from the project root directory.")
        sys.exit(1)

    if not is_rag_available():
        print("ERROR: Required packages not installed.")
        print("Run: pip install langchain langchain-community faiss-cpu sentence-transformers")
        sys.exit(1)

    engine = get_rag_engine()

    print(f"\nIndex directory: {engine.index_dir}")
    print(f"Force rebuild: {args.force}")
    print()

    print("Building RAG index...")
    success, message = engine.build_index(force=args.force)

    if success:
        print(f"SUCCESS: {message}")

        if args.test:
            print(f"\nTesting with query: '{args.test}'")
            results = engine.search(args.test, top_k=3)
            if results:
                print(f"\nFound {len(results)} results:")
                for i, r in enumerate(results, 1):
                    print(f"\n--- Result {i} ---")
                    print(f"Source: {r['source']}")
                    print(f"Title: {r['title']}")
                    print(f"Content preview: {r['content'][:200]}...")
            else:
                print("No results found.")
    else:
        print(f"FAILED: {message}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
