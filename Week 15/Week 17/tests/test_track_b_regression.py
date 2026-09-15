"""Adversarial checks for false positives and stable case joins (no live API)."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Task B'))
from run_experiment import GOLDEN_QUERIES
from src.track_b.utils.evidently_judge import join_cases, score_numeric, score_response_v2

class RegressionTests(unittest.TestCase):
    def test_numeric_false_positives(self):
        self.assertTrue(score_numeric('15% of 340 is 51.',51))
        self.assertTrue(score_numeric('51',51))
        for response in ['510', '-51', 'The answer is 510, not 51.', '51 is wrong; 510 is correct']:
            self.assertFalse(score_numeric(response,51),response)

    def test_negation_and_missing_criteria(self):
        self.assertFalse(score_response_v2('RAG has no retrieval or generation and never uses knowledge.',
            {'check_type':'rag','must_contain':['retrieval','generation','knowledge']})[0])
        self.assertFalse(score_response_v2('I cannot tell you the current date.', {'check_type':'datetime'})[0])
        self.assertFalse(score_response_v2('long enough but no criteria', {})[0])

    def test_join_reordered_missing_duplicate(self):
        row={'golden_id':'calculator_pct','response':'51','stopped_reason':'model_answered'}
        other={'golden_id':'rag_basic','response':'retrieval generation knowledge','stopped_reason':'model_answered'}
        first=join_cases([row,other],GOLDEN_QUERIES)
        second=join_cases([other,row],GOLDEN_QUERIES)
        self.assertTrue(first.equals(second))
        self.assertEqual(int(first.result_found.sum()),2)
        self.assertEqual(int(join_cases([],GOLDEN_QUERIES).deterministic_pass.sum()),0)
        with self.assertRaises(ValueError):join_cases([row,row],GOLDEN_QUERIES)
        with self.assertRaises(ValueError):join_cases([{'golden_id':'unknown'}],GOLDEN_QUERIES)

    def test_unicode_date_and_spacing(self):
        self.assertTrue(score_response_v2('September\u202f15,\u202f2026', {'check_type':'datetime','expected_date':'2026-09-15'})[0])
        self.assertFalse(score_response_v2('September 14, 2026', {'check_type':'datetime','expected_date':'2026-09-15'})[0])
        self.assertTrue(score_response_v2('2026‑09‑15', {'check_type':'datetime','expected_date':'2026-09-15'})[0])
        self.assertTrue(score_response_v2('Follow PEP\u202f8', {'must_contain':['PEP 8']})[0])

    def test_evidently_report_has_checks_and_missing_results_fail(self):
        import tempfile
        import json
        from unittest.mock import patch
        from evidently.llm.utils.wrapper import LLMResult
        from src.track_b.utils.evidently_judge import EvidentlyJudge, BoundedJudgeWrapper
        async def fixture(self, messages, seed=None):
            return LLMResult('{"category":"PASS","reasoning":"test fixture"}', 1, 1)
        from src.track_b.assistant.config import Settings
        with tempfile.TemporaryDirectory() as tmp, patch.object(BoundedJudgeWrapper, 'complete', fixture), patch.object(Settings, 'groq_keys', return_value=['fixture-not-a-key']):
            result = EvidentlyJudge(Path(tmp)).evaluate('fixture', [], GOLDEN_QUERIES)
            self.assertEqual(result['pct_tests_passed'], 0)
            snapshot = json.loads((Path(tmp)/'evidently_snapshot_fixture.json').read_text())
            self.assertGreaterEqual(len(snapshot['tests']), 2)

if __name__=='__main__':unittest.main()
