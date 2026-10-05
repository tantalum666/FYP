from pathlib import Path
import json,re
ROOT=Path('/Users/tantalum/Documents/ChatGPT/FYP')
OUT=ROOT/'output/brand/2026-09-17-senplate-refined-a-v2'
OUT.mkdir(parents=True,exist_ok=True)
GREEN='#163F35'
def path(d,transform=''):
    return '<path fill-rule="evenodd" d="'+d+'"'+(' transform="'+transform+'"' if transform else '')+'/>'
def svg(w,h,body,title='senplate',color=GREEN):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="{color}"><title>{title}</title>{body}</svg>\n'

# Explicit vector control points, not automatic pixel tracing.
dot='M 234 22 C 234 33.046 225.046 42 214 42 C 202.954 42 194 33.046 194 22 C 194 10.954 202.954 2 214 2 C 225.046 2 234 10.954 234 22 Z'
rim='M 157 41 C 85 36 2 55 2 89 C 2 134 75 168 164 168 C 253 168 323 133 323 89 C 323 67 296 50 248 42 C 245 41.5 243.5 42.5 243 45 L 242 49.5 C 241.5 51.5 242.5 52 245 52.5 C 284 61 303 74 303 87 C 303 109 242 127 165 127 C 87 127 22 110 22 89 C 22 68 79 52 141 52 Z'
portion='M 95 99 C 122 75 149 49 168 44 C 178 40 185 43 193 49 C 211 62 226 82 232 97 C 234 101 233 103 228 104 C 183 112 140 110 96 104 C 92 103.5 91.5 102 95 99 Z'
mark=path(dot)+path(rim)+path(portion)
s='M 75 21 L 59 29 C 55 21 47 17 37 17 C 27 17 20 22 20 28 C 20 35 28 37 41 40 C 61 44 77 51 77 68 C 77 85 61 94 39 94 C 19 94 5 87 0 74 L 16 66 C 21 75 28 79 40 79 C 51 79 58 75 58 69 C 58 62 48 60 35 57 C 14 52 2 44 2 29 C 2 12 18 0 38 0 C 55 0 68 7 75 21 Z'
e='M 94 49 C 94 20 75 0 49 0 C 20 0 0 20 0 47 C 0 75 19 94 49 94 C 69 94 85 85 91 70 L 73 63 C 69 72 61 77 49 77 C 32 77 21 68 19 54 L 94 54 Z M 20 38 C 23 24 33 17 48 17 C 62 17 72 25 75 38 Z'
n='M 0 2 H 18 V 12 C 25 4 33 0 44 0 C 66 0 80 15 80 38 V 92 H 61 V 42 C 61 26 54 18 41 18 C 28 18 19 27 19 43 V 92 H 0 Z'
p='M 0 2 H 19 V 12 C 26 4 36 0 49 0 C 75 0 94 20 94 47 C 94 74 75 94 49 94 C 36 94 26 89 19 82 V 125 H 0 Z M 19 47 C 19 30 31 17 48 17 C 64 17 76 30 76 47 C 76 64 64 77 48 77 C 31 77 19 64 19 47 Z'
l='M 1 0 H 18 Q 19 0 19 1 V 119 Q 19 120 18 120 H 1 Q 0 120 0 119 V 1 Q 0 0 1 0 Z'
a='M 74 2 H 93 V 92 H 74 V 82 C 67 90 57 94 44 94 C 19 94 0 74 0 47 C 0 20 19 0 44 0 C 57 0 67 5 74 13 Z M 18 47 C 18 64 30 77 46 77 C 62 77 75 64 75 47 C 75 30 62 17 46 17 C 30 17 18 30 18 47 Z'
t='M 13 0 H 32 V 27 H 49 V 44 H 32 V 86 C 32 95 36 99 45 99 H 49 V 116 C 46 117 42 117 38 117 C 21 117 13 107 13 90 V 44 H 0 V 27 H 13 Z'
capS='M 80 24 L 63 31 C 59 21 50 16 40 16 C 28 16 20 22 20 32 C 20 41 27 45 44 49 C 66 54 81 64 81 84 C 81 106 64 121 40 121 C 18 121 3 110 0 94 L 17 87 C 21 99 29 105 41 105 C 54 105 62 98 62 87 C 62 77 54 72 37 68 C 15 63 1 53 1 34 C 1 13 17 0 40 0 C 59 0 74 8 80 24 Z'
letters=[('s',s,0,29,1),('e',e,86,28,1),('n',n,191,29,1),('p',p,284,28,1),('l',l,386,0,1),('a',a,414,29,1),('t',t,515,3,1),('e',e,568,29,89/94)]
def word(cap=False):
    pieces=[]
    for i,(name,d,x,y,sx) in enumerate(letters):
        if cap and i==0:d=capS;y=0
        pieces.append(path(d,f'translate({x+2} {y+2}) scale({sx} 1)'))
    return ''.join(pieces)
for name,color in [('green',GREEN),('black','#000000'),('white','#FFFFFF')]:
    (OUT/f'senplate-mark-{name}.svg').write_text(svg(325,170,mark,'Senplate symbol',color))
    (OUT/f'senplate-logo-{name}.svg').write_text(svg(1028,170,mark+'<g transform="translate(367 5)">'+word()+'</g>','senplate',color))
(OUT/'senplate-wordmark-green.svg').write_text(svg(661,157,word(),'senplate wordmark'))
(OUT/'senplate-capital-s-comparison.svg').write_text(svg(1028,170,mark+'<g transform="translate(367 5)">'+word(True)+'</g>','Senplate capitalization comparison only'))
report={'method':'Manual low-node Bezier reconstruction, exact circular dot, straight stems, shared curves. No font substitution or automatic bitmap contour in final paths.','mark_path_segments':{name:len(re.findall('[MLHVQCZ]',d)) for name,d in [('dot',dot),('rim',rim),('portion',portion)]},'letter_path_segments':{name:len(re.findall('[MLHVQCZ]',d)) for name,d,*_ in letters},'capital_S_status':'comparison only, not selected','canvas':{'logo':[1028,170],'mark':[325,170],'wordmark':[661,157]}}
(ROOT/'output/qa/senplate-refined-a-v2-2026-09-17/vector-construction.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
