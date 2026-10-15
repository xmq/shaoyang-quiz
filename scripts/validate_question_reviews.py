"""Check that every released item has an actual review or a maintained new task."""
import json
from collections import Counter
from pathlib import Path
from question_reviews import apply_reviews, load_additions, load_edits, load_removals

ROOT=Path(__file__).resolve().parents[1]
REPORTS=(
    '题库复核_基础办公多媒体_2026-10-15.json',
    '题库复核_四门核心_2026-10-15.json',
    '题库复核_程序组成软件安全_2026-10-15.json',
    '题库复核_电子通信信号_2026-10-15.json',
)


def main():
    records=[]
    for name in REPORTS:
        payload=json.loads((ROOT/'audit_reports'/name).read_text(encoding='utf-8'))
        rows=payload if isinstance(payload,list) else payload['questions']
        for row in rows:
            reason=row.get('reason') or row.get('check') or row.get('independent_check') or ''
            if not row.get('id') or not row.get('verdict') or len(reason.strip())<6:
                raise ValueError(f'逐题审查缺少结论或理由：{name} {row.get("id")}')
        records.extend(rows)
    ids=[row['id'] for row in records]
    duplicates=[qid for qid,n in Counter(ids).items() if n>1]
    if duplicates or len(ids)!=2436:
        raise ValueError(f'本轮基线应逐题记录2436题，实际{len(ids)}，重复{duplicates[:10]}')
    reviewed=set(ids)
    removed=load_removals()
    edits=load_edits()
    additions=load_additions()
    new_ids={q['id'] for q in additions}
    bank=json.loads((ROOT/'questions.json').read_text(encoding='utf-8'))
    bank_ids={q['id'] for q in bank}
    if len(new_ids)!=len(additions): raise ValueError('新增复核题ID重复')
    if bank!=apply_reviews(bank): raise ValueError('复核修订未进入题库')
    if removed-reviewed: raise ValueError('有未逐题审查的移除项')
    if set(edits)-reviewed-new_ids: raise ValueError('有不存在的修订题号')
    missing=reviewed-bank_ids-removed
    extra=bank_ids-reviewed-new_ids
    if missing or extra: raise ValueError(f'审查覆盖不完整，丢失{sorted(missing)[:10]}，无记录{sorted(extra)[:10]}')
    if removed&bank_ids: raise ValueError('已移除题仍在题库')
    if new_ids-bank_ids: raise ValueError('新增复核题未进入题库')
    print(f'逐题复核记录：{len(reviewed)}题；修订{len(edits)}；移除{len(removed)}；补题{len(new_ids)}；发布{len(bank)}')


if __name__=='__main__': main()
