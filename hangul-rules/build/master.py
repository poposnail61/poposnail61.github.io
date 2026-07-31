import os as _os
"""마스터별 산출물 이름을 한군데서 정한다.

환경변수 HFS_MASTER 로 태그를 준다. 비어 있으면 지금까지의 이름 그대로다.

    HFS_MASTER=thin  HFS_SOURCE='... Thin'  python3 build/partial.py <font>
"""
TAG = _os.environ.get('HFS_MASTER', '').strip()
SOURCE = _os.environ.get('HFS_SOURCE', 'Noto Sans CJK KR Regular (noto-cjk Sans2.004)')
WGHT = _os.environ.get('HFS_WGHT', '')

def cell(default):
    """기준 셀. HFS_CELL='x0,y0,x1,y1' 이면 그 값을 쓴다.

    마스터마다 잉크 봉투가 달라 셀도 달라진다. 그러면 정규화 좌표가 마스터 간에
    다른 것을 가리켜 보간이 어긋난다. 두 마스터에 같은 셀을 주기 위한 통로다.
    """
    v = _os.environ.get('HFS_CELL', '').strip()
    if not v: return default
    a = tuple(int(float(x)) for x in v.split(','))
    assert len(a) == 4, 'HFS_CELL 은 x0,y0,x1,y1'
    return a

def tmp(name):
    """중간 pkl 이름."""
    if not TAG: return name
    a, b = name.rsplit('.', 1)
    return '%s-%s.%s' % (a, TAG, b)

def out(name):
    """산출 json 이름."""
    return tmp(name)
