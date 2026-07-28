"""hangul-font-studio의 composition_tree.rs를 그대로 이식한다."""
CHO='ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'
JUNG='ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'
JONG=['']+list('ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ')
# (compound, bottom-vowel base, side-vowel extension)
COMPOUND_MEDIALS={9:(8,0),10:(8,1),11:(8,20),14:(13,4),15:(13,5),16:(13,20),19:(18,20)}
BOTTOM_MEDIALS={8,12,13,17,18}
COMPOUND_TRAILINGS={3:(1,19),5:(4,22),6:(4,27),9:(8,1),10:(8,16),11:(8,17),
                    12:(8,19),13:(8,25),14:(8,26),15:(8,27),18:(17,19)}
H,V='Horizontal','Vertical'

def tree(li,vi,ti):
    """postorder nodes: (path, kind) where kind = ('leaf',role,idx) or ('group',axis,(a,b))"""
    nodes=[]
    def leaf(path,role,idx): nodes.append((path,('leaf',role,idx))); return len(nodes)-1
    def group(path,axis,ch): nodes.append((path,('group',axis,ch))); return len(nodes)-1
    leading=leaf('Leading','Leading',li)
    if vi in COMPOUND_MEDIALS:
        b,e=COMPOUND_MEDIALS[vi]
        base=leaf('MedialBase','Medial',b)
        bg=group('LeadingMedialBase',V,(leading,base))
        ext=leaf('MedialExtension','Medial',e)
        lm=group('LeadingMedial',H,(bg,ext))
    else:
        med=leaf('Medial','Medial',vi)
        lm=group('LeadingMedial', V if vi in BOTTOM_MEDIALS else H, (leading,med))
    if ti==0:
        root=lm
    else:
        if ti in COMPOUND_TRAILINGS:
            f,s=COMPOUND_TRAILINGS[ti]
            t1=leaf('TrailingFirst','Trailing',f); t2=leaf('TrailingSecond','Trailing',s)
            tr=group('Trailing',H,(t1,t2))
        else:
            tr=leaf('Trailing','Trailing',ti)
        root=group('Root',V,(lm,tr))
    return nodes,root

if __name__=='__main__':
    for ch in '괆과각가고관':
        i=ord(ch)-0xAC00; n,r=tree(i//588,(i%588)//28,i%28)
        print(ch, 'root=%d'%r)
        for j,(p,k) in enumerate(n): print('   %d %-18s %s'%(j,p,k))
