"""Verify both acceptance floors are required and missing metrics fail closed."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Task A'))
from src.track_a.train import promotion_allowed

class PromotionGateTests(unittest.TestCase):
    def test_both_boundaries_pass(self):
        self.assertTrue(promotion_allowed({'cv_f1_mean':.60,'roc_auc':.80}))

    def test_each_floor_blocks_independently(self):
        self.assertFalse(promotion_allowed({'cv_f1_mean':.59,'roc_auc':.95}))
        self.assertFalse(promotion_allowed({'cv_f1_mean':.75,'roc_auc':.79}))
        self.assertFalse(promotion_allowed({}))

if __name__=='__main__': unittest.main()
