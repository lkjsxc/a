"""Create local, script-free SVG teaching aids. Natural Earth outlines are public domain."""
from __future__ import annotations
import html
import io
import json
import math
from pathlib import Path
import re
import urllib.request
import zipfile

# JIS order, prefecture, reading, capital, reading, label longitude, latitude.
PREFECTURES = [
('北海道','ほっかいどう','札幌市','さっぽろし',142.5,43.4),
('青森県','あおもりけん','青森市','あおもりし',140.9,40.7),
('岩手県','いわてけん','盛岡市','もりおかし',141.4,39.7),
('宮城県','みやぎけん','仙台市','せんだいし',140.95,38.5),
('秋田県','あきたけん','秋田市','あきたし',140.35,39.8),
('山形県','やまがたけん','山形市','やまがたし',140.0,38.5),
('福島県','ふくしまけん','福島市','ふくしまし',140.1,37.35),
('茨城県','いばらきけん','水戸市','みとし',140.3,36.2),
('栃木県','とちぎけん','宇都宮市','うつのみやし',139.8,36.7),
('群馬県','ぐんまけん','前橋市','まえばしし',138.95,36.55),
('埼玉県','さいたまけん','さいたま市','さいたまし',139.35,36.0),
('千葉県','ちばけん','千葉市','ちばし',140.25,35.55),
('東京都','とうきょうと','新宿区','しんじゅくく',139.45,35.68),
('神奈川県','かながわけん','横浜市','よこはまし',139.3,35.4),
('新潟県','にいがたけん','新潟市','にいがたし',138.85,37.7),
('富山県','とやまけん','富山市','とやまし',137.25,36.6),
('石川県','いしかわけん','金沢市','かなざわし',136.75,36.8),
('福井県','ふくいけん','福井市','ふくいし',136.15,35.85),
('山梨県','やまなしけん','甲府市','こうふし',138.65,35.6),
('長野県','ながのけん','長野市','ながのし',138.0,36.2),
('岐阜県','ぎふけん','岐阜市','ぎふし',137.05,35.85),
('静岡県','しずおかけん','静岡市','しずおかし',138.3,35.0),
('愛知県','あいちけん','名古屋市','なごやし',137.1,35.1),
('三重県','みえけん','津市','つし',136.4,34.65),
('滋賀県','しがけん','大津市','おおつし',136.2,35.25),
('京都府','きょうとふ','京都市','きょうとし',135.45,35.2),
('大阪府','おおさかふ','大阪市','おおさかし',135.5,34.7),
('兵庫県','ひょうごけん','神戸市','こうべし',134.9,35.1),
('奈良県','ならけん','奈良市','ならし',135.9,34.35),
('和歌山県','わかやまけん','和歌山市','わかやまし',135.5,33.85),
('鳥取県','とっとりけん','鳥取市','とっとりし',133.85,35.4),
('島根県','しまねけん','松江市','まつえし',132.7,35.0),
('岡山県','おかやまけん','岡山市','おかやまし',133.85,34.85),
('広島県','ひろしまけん','広島市','ひろしまし',132.8,34.55),
('山口県','やまぐちけん','山口市','やまぐちし',131.65,34.2),
('徳島県','とくしまけん','徳島市','とくしまし',134.25,33.9),
('香川県','かがわけん','高松市','たかまつし',134.0,34.25),
('愛媛県','えひめけん','松山市','まつやまし',132.85,33.65),
('高知県','こうちけん','高知市','こうちし',133.45,33.4),
('福岡県','ふくおかけん','福岡市','ふくおかし',130.7,33.55),
('佐賀県','さがけん','佐賀市','さがし',130.15,33.3),
('長崎県','ながさきけん','長崎市','ながさきし',129.8,32.9),
('熊本県','くまもとけん','熊本市','くまもとし',130.75,32.6),
('大分県','おおいたけん','大分市','おおいたし',131.45,33.2),
('宮崎県','みやざきけん','宮崎市','みやざきし',131.2,32.1),
('鹿児島県','かごしまけん','鹿児島市','かごしまし',130.65,31.5),
('沖縄県','おきなわけん','那覇市','なはし',127.8,26.35)]

CLIMATE = {
'A': {'temperature':[9,10,12,15,19,23,26,26,23,18,14,10], 'rain':[90,75,65,40,25,10,5,10,35,70,95,100]},
'B': {'temperature':[15,17,21,26,31,35,37,36,33,27,21,16], 'rain':[3,2,3,2,1,0,0,0,0,1,2,3]}}


def svg_start(width: int, height: int, title: str) -> list[str]:
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">',
            f'<title>{html.escape(title)}</title>',
            '<style>text{font-family:"Noto Sans CJK JP","Yu Gothic",sans-serif;fill:currentColor;font-size:14px}path,line,rect,circle,polyline{stroke:currentColor;fill:none} .label{font-size:12px;font-weight:bold;paint-order:stroke;stroke:white;stroke-width:3px;stroke-linejoin:round}</style>']


def write_svg(path: Path, parts: list[str]) -> None:
    path.write_text('\n'.join(parts + ['</svg>']) + '\n', encoding='utf-8')


def climate_svg(path: Path) -> None:
    # One comparison diagram; each location is labelled, axes and all data are explicit.
    s = svg_start(850, 490, '地点AとBの架空の雨温図。折れ線は気温、棒は降水量。')
    s += ['<text x="25" y="28" style="font-size:20px">月別の気温と降水量（学習用の架空データ）</text>']
    for n, name in enumerate(('A', 'B')):
        ox, oy, w, h = 55 + n*420, 85, 305, 290
        s.append(f'<text x="{ox}" y="60" style="font-size:18px">地点{name}・北半球</text>')
        s.append(f'<rect x="{ox}" y="{oy}" width="{w}" height="{h}"/>')
        s.append(f'<text x="{ox-30}" y="{oy-7}">℃</text><text x="{ox+w+8}" y="{oy-7}">mm</text>')
        for v in range(0, 41, 10):
            y=oy+h-v/40*h
            s.append(f'<line x1="{ox}" x2="{ox+w}" y1="{y}" y2="{y}" stroke-dasharray="2 5" stroke-width="0.5"/>')
            s.append(f'<text x="{ox-8}" y="{y+4}" text-anchor="end">{v}</text>')
            s.append(f'<text x="{ox+w+5}" y="{y+4}">{int(v*3)}</text>')
        pts=[]
        for i,(t,r) in enumerate(zip(CLIMATE[name]['temperature'],CLIMATE[name]['rain'])):
            x=ox+(i+.5)*w/12
            y=oy+h-r/120*h
            s.append(f'<rect x="{x-6:.2f}" y="{y:.2f}" width="12" height="{oy+h-y:.2f}" stroke-width="1.2"/>')
            pts.append(f'{x:.2f},{oy+h-t/40*h:.2f}')
            s.append(f'<text x="{x:.2f}" y="{oy+h+24}" text-anchor="middle" style="font-size:12px">{i+1}</text>')
        s.append(f'<polyline points="{" ".join(pts)}" stroke-width="2.5"/>')
        s.append(f'<text x="{ox}" y="{oy+h+49}">横軸：月　折れ線：気温　棒：降水量</text>')
        s.append(f'<text x="{ox}" y="{oy+h+72}">年間降水量：{sum(CLIMATE[name]["rain"])}mm</text>')
    s.append('<text x="25" y="475">実在都市の観測値ではありません。左右の目盛を区別し、季節配分を比較します。</text>')
    write_svg(path,s)


def contour_svg(path: Path) -> None:
    s=svg_start(760,430,'等高線の模式図。西側Aは東側Bより等高線の間隔が狭い。')
    s.append('<text x="25" y="28" style="font-size:20px">等高線の間隔と斜面（模式図・架空地形）</text>')
    # Nested, shifted ellipses: left intercepts 100,120,140,160 and right 650,570,490,410.
    for i, (left,right,elev) in enumerate([(100,650,100),(120,570,200),(140,490,300),(160,410,400)]):
        rx=(right-left)/2; cx=(right+left)/2; ry=145-i*26
        s.append(f'<ellipse cx="{cx}" cy="210" rx="{rx}" ry="{ry}" fill="none" stroke="currentColor" stroke-width="1.8"/>')
        s.append(f'<text x="{cx}" y="{210-ry-6}" text-anchor="middle">{elev}m</text>')
    s += ['<text x="52" y="215" style="font-size:20px">A</text>', '<text x="676" y="215" style="font-size:20px">B</text>',
          '<line x1="75" y1="210" x2="685" y2="210" stroke-dasharray="5 5"/>',
          '<line x1="690" y1="110" x2="690" y2="70"/><path d="M685,80 L690,70 L695,80"/><text x="682" y="57">北</text>',
          '<text x="25" y="395">等高線の標高差は100m。A側は同じ標高差に対する水平距離が短い。</text>',
          '<text x="25" y="416">水平距離の縮尺は指定していません。この図から実距離や勾配の数値は求められません。</text>']
    write_svg(path,s)


def download_shapes(cache: Path, scale: str, base: str):
    import shapefile
    root=cache/base
    if not (root/(base+'.shp')).exists():
        root.mkdir(parents=True,exist_ok=True)
        url=f'https://naturalearth.s3.amazonaws.com/{scale}_cultural/{base}.zip'
        req=urllib.request.Request(url,headers={'User-Agent':'SocialStudiesEducationalBuild/1.0'})
        with urllib.request.urlopen(req,timeout=90) as response:
            raw=response.read(40_000_000)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            for info in z.infolist():
                # Only expected basename sidecars: no archive traversal.
                if '/' not in info.filename and info.filename.startswith(base+'.'):
                    (root/info.filename).write_bytes(z.read(info))
    return shapefile.Reader(str(root/base),encoding='utf-8')


def paths_for_shape(shape, transform) -> str:
    chunks=[]
    ends=list(shape.parts)+[len(shape.points)]
    for a,b in zip(ends,ends[1:]):
        pts=shape.points[a:b]
        if len(pts)<3: continue
        converted=[transform(lon,lat) for lon,lat in pts]
        chunks.append('M'+' L'.join(f'{x:.1f},{y:.1f}' for x,y in converted)+' Z')
    return ' '.join(chunks)


def maps(out: Path, cache: Path) -> dict:
    world=download_shapes(cache,'110m','ne_110m_admin_0_countries')
    s=svg_start(1040,570,'世界の国々の位置を学ぶ概略図。正距円筒図法。')
    s.append('<text x="20" y="28" style="font-size:20px">世界の位置を確かめる概略図</text>')
    def tr(lon,lat): return (20+(lon+180)*1000/360,60+(85-lat)*450/165)
    for shape in world.shapes():
        s.append(f'<path d="{paths_for_shape(shape,tr)}" stroke-width="0.55"/>')
    for lat in (-60,-30,0,30,60):
        a,y=tr(-180,lat);b,_=tr(180,lat)
        s.append(f'<line x1="{a}" x2="{b}" y1="{y}" y2="{y}" stroke-dasharray="3 6" stroke-width="0.4"/>')
    labels=[('アジア',91,45),('ヨーロッパ',20,57),('アフリカ',18,0),('北アメリカ',-107,45),('南アメリカ',-59,-20),('オセアニア',138,-29),('太平洋',-160,0),('大西洋',-35,16),('インド洋',75,-22)]
    for name,lon,lat in labels:
        x,y=tr(lon,lat);s.append(f'<text class="label" x="{x}" y="{y}" text-anchor="middle">{name}</text>')
    s += ['<text x="20" y="538">Natural Earthをもとに作成。正距円筒図法：高緯度の面積や一般の距離は正しく比較できません。</text>',
          '<text x="20" y="560">位置学習用。細かな島を省略し、境界線は特定の国の領有権の主張を示すものではありません。</text>']
    write_svg(out/'world.svg',s)
    reader=download_shapes(cache,'10m','ne_10m_admin_1_states_provinces')
    records={}
    for sr in reader.iterShapeRecords():
        r=sr.record.as_dict()
        code=str(r.get('iso_3166_2',''))
        if re.fullmatch(r'JP-\d{2}',code): records[int(code[3:])]=sr.shape
    if set(records)!=set(range(1,48)):
        raise ValueError(f'Expected 47 Japanese prefectures, found {sorted(records)}')
    s=svg_start(1120,1050,'日本の47都道府県の番号付き概略図。関東・近畿・沖縄の拡大図付き。')
    s.append('<text x="20" y="30" style="font-size:21px">都道府県の位置（番号は付録の01〜47）</text>')
    panels=[('main',20,65,720,825,128.3,146.5,30,46.3,set(range(1,47))),
            ('kanto',780,80,315,245,138.5,141,34.9,37.5,set(range(8,15))),
            ('kinki',780,390,315,245,134.0,137.0,33.5,36,set(range(24,31))),
            ('okinawa',780,710,315,175,122.7,131.5,23.5,28.5,{47})]
    s.append('<defs>')
    for name,x,y,w,h,*_ in panels:s.append(f'<clipPath id="{name}"><rect x="{x}" y="{y}" width="{w}" height="{h}"/></clipPath>')
    s.append('</defs>')
    for name,x,y,w,h,lo,hi,bot,top,labels in panels:
        # Each inset has its own scale. Equirectangular with latitude correction.
        s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" stroke-width="0.7"/>')
        s.append(f'<g clip-path="url(#{name})">')
        def tf(lon,lat):return x+(lon-lo)/(hi-lo)*w, y+(top-lat)/(top-bot)*h
        for code,shape in records.items():
            a,b,c,d=shape.bbox
            if c<lo or a>hi or d<bot or b>top:continue
            s.append(f'<path d="{paths_for_shape(shape,tf)}" stroke-width="0.7"/>')
        for code in sorted(labels):
            if name=='main' and (8<=code<=14 or 24<=code<=30):continue
            row=PREFECTURES[code-1]; px,py=tf(row[4],row[5])
            s.append(f'<text x="{px:.1f}" y="{py:.1f}" class="label" text-anchor="middle">{code:02}</text>')
        s.append('</g>')
    s += ['<text x="785" y="67">関東（拡大）</text>','<text x="785" y="374">近畿周辺（拡大）</text>','<text x="785" y="695">沖縄（縮尺が異なる）</text>',
          '<text x="20" y="930">関東・近畿の番号は右の拡大図へ。各図の距離・面積を直接比較しないでください。</text>',
          '<text x="20" y="958">Natural Earthをもとにした位置学習用の概略図です。一部の離島や微小な形状を省略しています。</text>',
          '<text x="20" y="984">境界線は領有権の判断を示すものではありません。領土については本文G13と公式資料で確認します。</text>',
          '<text x="20" y="1010">番号を隠した練習：地図を見て名称 → 付録で確認 → 隣接県・地方・海を説明します。</text>']
    write_svg(out/'japan-prefectures.svg',s)
    return {'world_countries':len(world),'japan_prefectures':len(records),'source':'Natural Earth 110m admin0 / 10m admin1, public domain'}


def generate(root: Path) -> dict:
    out=root/'assets';out.mkdir(exist_ok=True)
    climate_svg(out/'climate.svg');contour_svg(out/'contours.svg')
    cache=Path.home()/'.cache'/'social-studies-naturalearth'
    result=maps(out,cache)
    (out/'climate-data.json').write_text(json.dumps({'notice':'学習用の架空データ。実在都市の観測値ではない。','data':CLIMATE},ensure_ascii=False,indent=2)+'\n')
    return result
