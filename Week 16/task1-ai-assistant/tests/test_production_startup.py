"""Check production startup wires the same knowledge tool as the core API."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'task2-production'))
from backend import main as production


class ProductionStartupTests(unittest.IsolatedAsyncioTestCase):
    async def test_registers_knowledge_tool_after_retriever_creation(self):
        retriever = Mock()
        retriever.ingest_documents.return_value = 3
        with patch.object(production, 'RAGRetriever', return_value=retriever) as factory, \
             patch.object(production, 'rag_retriever', None), \
             patch.object(production.tool_registry, '_tools', {}), \
             patch.object(production.fallback_manager, 'register_providers'):
            async with production.lifespan(production.app):
                self.assertIn('search_knowledge', production.tool_registry.list_tools())
                self.assertTrue(Path(factory.call_args.kwargs['source_dir']).is_dir())
