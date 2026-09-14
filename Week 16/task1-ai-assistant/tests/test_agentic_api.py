"""API contract checks with a scripted provider; no network or model startup."""
import os
os.environ.setdefault('DEBUG', 'false')
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app import main
from app.llm.provider import LLMResponse


class AgenticAPITests(unittest.TestCase):
    def test_configured_provider_without_unaccounted_health_call(self):
        provider = AsyncMock()
        provider.chat.return_value = LLMResponse(content='CLARIFY: Which documents should I compare?',usage={'prompt_tokens':4,'completion_tokens':3})
        with patch.object(main, 'get_provider', return_value=provider) as factory:
            client = TestClient(main.app)
            response = client.post('/chat/agentic',json={'message':'Compare them','max_iterations':3})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['stopped_reason'],'clarification')
        self.assertEqual(response.json()['total_tokens'],{'prompt_tokens':4,'completion_tokens':3})
        # get_provider called for primary; fallback creation is best-effort and may also call it
        self.assertTrue(factory.call_count >= 1)
        provider.health_check.assert_not_called()

    def test_api_rejects_more_than_five_iterations(self):
        client = TestClient(main.app)
        self.assertEqual(client.post('/chat/agentic',json={'message':'q','max_iterations':6}).status_code,422)

    def test_health_poll_does_not_consume_model_quota(self):
        with patch.object(main,'get_provider') as factory:
            result=TestClient(main.app).get('/health')
        self.assertEqual(result.status_code,200)
        self.assertIsNone(result.json()['llm_available'])
        factory.assert_not_called()
