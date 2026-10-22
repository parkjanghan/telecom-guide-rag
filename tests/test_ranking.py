import unittest
from telecom_rag.ranking import mmr_indices
class MMRTests(unittest.TestCase):
 def test_diversity(self):
  v=[[1,0],[.999,.001],[.7,.7]]
  self.assertEqual(mmr_indices([1,0],v,2,.3),[0,2])
  self.assertEqual(mmr_indices([1,0],v,2,1),[0,1])
 def test_empty(self):self.assertEqual(mmr_indices([1,0],[],3),[])
 def test_weight(self):
  with self.assertRaises(ValueError):mmr_indices([1],[[1]],1,2)
