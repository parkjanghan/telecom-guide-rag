import unittest
from pathlib import Path
from unittest.mock import patch
from telecom_rag.core import read_md, split_offsets

class FakeTokens:
    def encode(self, text, add_special_tokens=False):
        return type('Encoded',(),{'offsets':[(i,i+1) for i in range(len(text))]})()

class ChunkContractTests(unittest.TestCase):
    def test_overlapping_chunks_preserve_every_character(self):
        text='가족결합 유지\n|대상|조건|\n|본인|인증|\n😀 끝부분까지 보존'
        ranges=split_offsets(text,FakeTokens(),12,3)
        covered=set()
        for a,b in ranges:
            covered.update(range(a,b));self.assertLessEqual(b-a,12)
        self.assertEqual(covered,set(range(len(text))))
        self.assertEqual(ranges[0][0],0);self.assertEqual(ranges[-1][1],len(text))
    def test_invalid_overlap_fails_instead_of_looping(self):
        for size,overlap in [(0,0),(10,10),(10,-1)]:
            with self.assertRaises(ValueError):split_offsets('본문',FakeTokens(),size,overlap)
    def test_non_topic_markdown_is_not_a_topic(self):
        with patch.object(Path,'read_text',return_value='# 설명서\n'):
            self.assertEqual(read_md(Path('README.md'))[0],{})
    def test_obsidian_yaml_lists_remain_readable(self):
        value='---\nitem_id: sample\naliases:\n  - 통신비 변경\n  - 계좌 변경\nanswer_ready: false\n---\n본문'
        with patch.object(Path,'read_text',return_value=value):
            meta,body=read_md(Path('sample.md'))
            self.assertEqual(meta['aliases'],['통신비 변경','계좌 변경'])
            self.assertFalse(meta['answer_ready'])
            self.assertEqual(body,'본문')
    def test_obsidian_dates_remain_serializable(self):
        with patch.object(Path,'read_text',return_value='---\neffective_from: 2026-10-22\n---\n본문'):
            meta,_=read_md(Path('date.md'))
            self.assertEqual(meta['effective_from'],'2026-10-22')
    def test_frontmatter_does_not_evaluate_yaml(self):
        with patch.object(Path,'read_text',return_value='---\nitem_id: !!python/object:unsafe {}\n---\n본문'):
            with self.assertRaises(ValueError):read_md(Path('bad.md'))
if __name__=='__main__':unittest.main()
