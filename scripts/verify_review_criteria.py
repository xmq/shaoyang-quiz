"""Protect numerical answers and meaningful words when deriving review points."""
from enrich_question_metadata import derive_short_rubric


def check(source, expected):
    question = {'answer': '参见各项', 'explanation': '评分点：' + source}
    actual = [item['criterion'] for item in derive_short_rubric(question)]
    assert actual == expected, (source, actual, expected)


check('63.2%、二者边界、一个算法、三种状态。', ['63.2%', '二者边界', '一个算法', '三种状态'])
check('1. 初值；（2）终值；三、单位。', ['初值', '终值', '单位'])
check('1.5倍；10 MHz；2^n种；一级缓存。', ['1.5倍', '10 MHz', '2^n种', '一级缓存'])
print('核对要点：小数、数量和词义完整；仅去除明确枚举编号。')
