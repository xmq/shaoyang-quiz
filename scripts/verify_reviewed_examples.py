"""Independently calculate representative electrical and signal answers."""
import cmath
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    bank = {q['id']: q for q in json.loads((ROOT/'questions.json').read_text(encoding='utf-8'))}
    cases = [
        ('uf-ee-001', 1/(1/6+1/6+1/6)),
        ('uf-ee-002', 12*4/(2+4)),
        ('uf-ee-003', 2+3-1.5),
        ('uf-ee-007', (10/(5+5))**2*5),
        ('uf-ee-010', 100000*10e-6),
        ('uf-ee-011', 12*(1-math.exp(-1))),
        ('uf-ee-015', 1/(2*math.pi*50*100e-6)),
        ('uf-ee-017', abs(complex(20,30-15))),
        ('uf-ee-019', 100*4*.8),
        ('uf-ee-020', math.sqrt(3)*380*10*.8/1000),
        ('uf-ee-022', 60*50/2),
        ('uf-ae-004', 10*math.sqrt(2)/math.pi),
        ('uf-ae-007', 100*20e-6*1000),
        ('uf-ae-015', 1+40/10),
        ('ue-analog-003', 12-(12-.7)/470000*100*2000),
        ('ue-analog-006', 100/(1+100*.09)),
        ('ue-analog-009', 12),
        ('uf-de-001', int('101101',2)),
        ('uf-de-010', math.log2(8)),
        ('uf-de-022', 2**8),
        ('sp-elec-digital-011', 3.3/4096*1000),
        ('sp-elec-digital-012', .5/2*100),
        ('uf-cm-003', math.log2(8)),
        ('uf-cm-004', 2400*math.log2(16)),
        ('uf-cm-005', 10**(30/10)),
        ('uf-cm-006', 3000*math.log2(1001)/1000),
        ('uf-cm-017', 2*(5*3+3)),
        ('ue-comm-001', -sum(p*math.log2(p) for p in [.5,.25,.25])),
        ('ap-comm-001', 1*math.log2(4)),
        ('ue-comm-004', 2400*math.log2(4)),
        ('ue-comm-005', 2*5),
        ('ue-comm-006', 2*(75+15)),
        ('ue-comm-009', 1/(2*math.pi*math.sqrt(1e-6*100e-12))/1e6),
        ('gap-signal-001', 2*math.pi/(4*math.pi)),
        ('gap-final-sig-001', 1/4),
        ('gap-final-sig-003', 2**2+1),
        ('gap-final-sig-017', abs(9-10)),
        ('gap-final-sig-018', 5/256*1000),
    ]
    checked = []
    for qid, expected in cases:
        q = bank[qid]
        text = q.get('options',{}).get(q['answer'],q['answer'])
        # Comparator overzero question has a transition, not a scalar answer.
        if qid == 'ue-analog-009':
            assert q['answer'] == 'B' and '-12' in text and '+12' in text
        else:
            actual = float(re.search(r'[-−]?\d+(?:\.\d+)?',text).group().replace('−','-'))
            assert math.isclose(actual,expected,rel_tol=.012,abs_tol=.051), (qid,actual,expected)
        checked.append({'id':qid,'independent_value':expected,'unit':'按题目选项单位'})
    # Exhaustive truth table: mux A selects B or 1, hence A OR B.
    table=[]
    for a in [0,1]:
        for b in [0,1]:
            mux = b if a == 0 else 1
            assert mux == (a|b)
            table.append([a,b,mux])
    # Discrete convolution, independently accumulated by both indices.
    y=[0]*3
    for i,x in enumerate([1,2]):
        for j,h in enumerate([1,-1]): y[i+j] += x*h
    assert y == [1,1,-2]
    gray = 13 ^ (13 >> 1)
    assert format(gray,'04b') == '1011'
    result={'numeric_cases':checked,'mux_truth_table':table,'convolution':y,'gray13':format(gray,'04b')}
    (ROOT/'audit_reports/题库复核_电子独立计算_2026-10-15.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'独立算式核对：{len(checked)}题，MUX穷举、卷积与格雷码通过')


if __name__ == '__main__': main()
