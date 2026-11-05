"""화면 꾸미기 전용 파일: 색, 글꼴, 로고, 분류별 그림.

ui.py는 화면 구조만, 이 파일은 "어떻게 보이는지"만 담당한다.
색을 바꾸고 싶으면 아래 COLORS만 고치면 된다.
"""

import base64

# 김밥 재료에서 가져온 색
COLORS = {
    "seaweed": "#1F2B24",  # 김 (글자, 테두리)
    "rice": "#FFFDF5",     # 밥 (카드 배경)
    "egg": "#F6C945",      # 계란 (포인트 노랑)
    "bg": "#FFF6D8",       # 화면 전체 배경 (연한 노랑)
    "carrot": "#F07B2A",   # 당근
    "spinach": "#3C9A4E",  # 시금치
    "radish": "#F5B800",   # 단무지
    "crab": "#E5483B",     # 맛살
}


def svg_data_uri(svg: str) -> str:
    """SVG 글자를 <img src="...">에 바로 넣을 수 있는 형태로 바꾼다."""
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


# =====================================================================
# 로고: B안(김밥 나침반)
# =====================================================================
LOGO_MARK_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240">
<circle cx="120" cy="120" r="112" fill="#1F2B24"/>
<g fill="#F3E6BF">
<ellipse cx="205.2" cy="179.7" rx="3.6" ry="1.7" transform="rotate(125 205.2 179.7)"/>
<ellipse cx="29.9" cy="172" rx="3.6" ry="1.7" transform="rotate(60 29.9 172)"/>
<ellipse cx="34.8" cy="60.3" rx="3.6" ry="1.7" transform="rotate(-55 34.8 60.3)"/>
<ellipse cx="199.7" cy="53.1" rx="3.6" ry="1.7" transform="rotate(50 199.7 53.1)"/>
<ellipse cx="110.9" cy="223.6" rx="3.6" ry="1.7" transform="rotate(5 110.9 223.6)"/>
<ellipse cx="160" cy="18.5" rx="3.6" ry="1.7" transform="rotate(20 160 18.5)"/>
</g>
<circle cx="120" cy="120" r="96" fill="#FFFDF5"/>
<g fill="#EDE5D0">
<ellipse cx="64" cy="92" rx="5" ry="2.6" transform="rotate(-30 64 92)"/>
<ellipse cx="70" cy="160" rx="5" ry="2.6" transform="rotate(40 70 160)"/>
<ellipse cx="176" cy="84" rx="5" ry="2.6" transform="rotate(35 176 84)"/>
<ellipse cx="172" cy="160" rx="5" ry="2.6" transform="rotate(-35 172 160)"/>
<ellipse cx="90" cy="196" rx="5" ry="2.6" transform="rotate(60 90 196)"/>
<ellipse cx="152" cy="198" rx="5" ry="2.6" transform="rotate(-55 152 198)"/>
</g>
<g fill="#1F2B24">
<rect x="118" y="28" width="4" height="14" rx="2" transform="rotate(90 120 120)"/>
<rect x="118" y="28" width="4" height="14" rx="2" transform="rotate(180 120 120)"/>
<rect x="118" y="28" width="4" height="14" rx="2" transform="rotate(270 120 120)"/>
<rect x="118.5" y="28" width="3" height="8" rx="1.5" transform="rotate(45 120 120)"/>
<rect x="118.5" y="28" width="3" height="8" rx="1.5" transform="rotate(135 120 120)"/>
<rect x="118.5" y="28" width="3" height="8" rx="1.5" transform="rotate(225 120 120)"/>
<rect x="118.5" y="28" width="3" height="8" rx="1.5" transform="rotate(315 120 120)"/>
</g>
<text x="120" y="48" fill="#1F2B24" font-family="system-ui, sans-serif" font-size="19" font-weight="800" text-anchor="middle">N</text>
<polygon points="120,62 120,120 103,120" fill="#F07B2A"/>
<polygon points="120,62 137,120 120,120" fill="#D9621A"/>
<polygon points="120,178 120,120 103,120" fill="#3C9A4E"/>
<polygon points="120,178 137,120 120,120" fill="#2F7F3F"/>
<circle cx="120" cy="120" r="11" fill="#F9DC7A" stroke="#1F2B24" stroke-width="3"/>
</svg>"""

LOGO_MARK_URI = svg_data_uri(LOGO_MARK_SVG)


def logo_html(size: str = "big") -> str:
    """로고(나침반 + '김밥' 글자). size: 'big'(첫 화면) / 'small'(메인 화면 왼쪽 위)"""
    if size == "big":
        return f"""
<div class="gb-hero">
  <img src="{LOGO_MARK_URI}" alt="김밥 로고: 김밥 단면 모양의 나침반" width="190" height="190">
  <div class="gb-hero-name">김밥</div>
  <div class="gb-hero-team">TEAM GIMBAP</div>
</div>"""
    return f"""
<div class="gb-logo-small">
  <img src="{LOGO_MARK_URI}" alt="김밥 로고" width="56" height="56">
  <span>김밥</span>
</div>"""


# =====================================================================
# 분류별 그림 (사진이 없을 때 카드에 넣는 그림)
# =====================================================================
_STROKE = 'stroke="#1F2B24" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"'

_ICONS = {
    "음식점": f"""
<path d="M110 100 H210 A50 50 0 0 1 110 100 Z" fill="#FFFDF5" {_STROKE}/>
<path d="M118 100 Q160 72 202 100" fill="#FFFDF5" {_STROKE}/>
<circle cx="142" cy="93" r="5" fill="#F07B2A"/><circle cx="160" cy="88" r="5" fill="#3C9A4E"/><circle cx="178" cy="93" r="5" fill="#F5B800"/>
<line x1="176" y1="88" x2="226" y2="44" {_STROKE}/><line x1="188" y1="92" x2="238" y2="54" {_STROKE}/>
<line x1="142" y1="156" x2="178" y2="156" {_STROKE}/>""",
    "카페": f"""
<path d="M120 80 H190 V125 A25 25 0 0 1 165 150 H145 A25 25 0 0 1 120 125 Z" fill="#FFFDF5" {_STROKE}/>
<path d="M190 92 A16 16 0 0 1 190 124" fill="none" {_STROKE}/>
<line x1="108" y1="162" x2="202" y2="162" {_STROKE}/>
<path d="M140 68 q-8 -12 0 -24" fill="none" {_STROKE}/><path d="M160 68 q-8 -12 0 -24" fill="none" {_STROKE}/><path d="M180 68 q-8 -12 0 -24" fill="none" {_STROKE}/>""",
    "맛집": f"""
<circle cx="160" cy="105" r="44" fill="#FFFDF5" {_STROKE}/>
<circle cx="160" cy="105" r="28" fill="none" stroke="#1F2B24" stroke-width="3"/>
<path d="M150 106 l7 7 l14 -16" fill="none" stroke="#F07B2A" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
<line x1="96" y1="66" x2="96" y2="148" {_STROKE}/><line x1="88" y1="66" x2="88" y2="88" {_STROKE}/><line x1="104" y1="66" x2="104" y2="88" {_STROKE}/>
<path d="M88 88 Q96 98 104 88" fill="none" {_STROKE}/>
<path d="M224 66 Q240 94 224 110 V148" fill="none" {_STROKE}/>""",
    "문화체험": f"""
<path d="M160 52 C110 52 92 90 98 118 C104 146 130 156 150 150 C166 145 158 128 172 126 C190 124 222 130 224 102 C226 74 200 52 160 52 Z" fill="#FFFDF5" {_STROKE}/>
<circle cx="130" cy="90" r="9" fill="#F07B2A"/><circle cx="160" cy="76" r="9" fill="#3C9A4E"/><circle cx="192" cy="86" r="9" fill="#F5B800"/><circle cx="124" cy="122" r="9" fill="#E5483B"/>
<line x1="204" y1="152" x2="240" y2="116" stroke="#1F2B24" stroke-width="8" stroke-linecap="round"/>""",
    "여가활동": f"""
<path d="M100 70 H220 V92 A12 12 0 0 0 220 116 V138 H100 V116 A12 12 0 0 0 100 92 Z" fill="#FFFDF5" {_STROKE}/>
<line x1="182" y1="76" x2="182" y2="132" stroke="#1F2B24" stroke-width="4" stroke-dasharray="7 7"/>
<path d="M140 88 l6 12 l13 2 l-10 9 l3 13 l-12 -7 l-12 7 l3 -13 l-10 -9 l13 -2 z" fill="#F07B2A"/>""",
    "랜드마크": f"""
<line x1="108" y1="162" x2="212" y2="162" {_STROKE}/>
<path d="M132 162 L150 112 H170 L188 162" fill="#FFFDF5" {_STROKE}/>
<line x1="160" y1="112" x2="160" y2="40" {_STROKE}/>
<ellipse cx="160" cy="100" rx="28" ry="11" fill="#F5B800" {_STROKE}/>
<circle cx="160" cy="36" r="5" fill="#E5483B"/>""",
    "팝업스토어": f"""
<rect x="106" y="94" width="108" height="66" fill="#FFFDF5" {_STROKE}/>
<path d="M98 94 L110 62 H210 L222 94 Z" fill="#F07B2A" {_STROKE}/>
<line x1="140" y1="62" x2="134" y2="94" stroke="#FFFDF5" stroke-width="5"/><line x1="160" y1="62" x2="160" y2="94" stroke="#FFFDF5" stroke-width="5"/><line x1="180" y1="62" x2="186" y2="94" stroke="#FFFDF5" stroke-width="5"/>
<rect x="146" y="118" width="28" height="42" fill="#F6C945" {_STROKE}/>""",
    "소품샵": f"""
<rect x="112" y="96" width="96" height="64" fill="#FFFDF5" {_STROKE}/>
<rect x="104" y="78" width="112" height="20" fill="#F5B800" {_STROKE}/>
<rect x="153" y="78" width="14" height="82" fill="#E5483B"/>
<ellipse cx="145" cy="68" rx="14" ry="9" fill="none" {_STROKE}/><ellipse cx="175" cy="68" rx="14" ry="9" fill="none" {_STROKE}/>""",
    "쇼핑": f"""
<path d="M112 80 H208 L200 160 H120 Z" fill="#FFFDF5" {_STROKE}/>
<path d="M138 80 V68 A22 22 0 0 1 182 68 V80" fill="none" {_STROKE}/>
<circle cx="160" cy="118" r="12" fill="#3C9A4E"/>""",
    "전시": f"""
<rect x="104" y="56" width="112" height="98" rx="4" fill="#F5B800" {_STROKE}/>
<rect x="118" y="70" width="84" height="70" fill="#FFFDF5" stroke="#1F2B24" stroke-width="4"/>
<path d="M122 136 L148 104 L166 124 L178 112 L198 136 Z" fill="#3C9A4E"/>
<circle cx="184" cy="88" r="8" fill="#F07B2A"/>""",
}

_DEFAULT_ICON = f"""
<path d="M160 160 C140 130 120 112 120 88 A40 40 0 0 1 200 88 C200 112 180 130 160 160 Z" fill="#FFFDF5" {_STROKE}/>
<circle cx="160" cy="88" r="14" fill="#F07B2A"/>"""

_BG = {
    "음식점": "#FFE08A", "카페": "#FFE8B3", "맛집": "#FFD166", "문화체험": "#FCE38A",
    "여가활동": "#FFEFC1", "랜드마크": "#FFDCA8", "팝업스토어": "#FFE7A0",
    "소품샵": "#FBE3B2", "쇼핑": "#F9D976", "전시": "#FFD8A6",
}


def category_image_uri(category: str) -> str:
    """분류 이름 → 노란 톤 그림(data URI)."""
    icon = _ICONS.get(category, _DEFAULT_ICON)
    bg = _BG.get(category, "#FFE8B3")
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 200">
<rect width="320" height="200" fill="{bg}"/>
<g fill="#FFFFFF" opacity="0.55">
<ellipse cx="40" cy="36" rx="7" ry="3.5" transform="rotate(-25 40 36)"/>
<ellipse cx="278" cy="40" rx="7" ry="3.5" transform="rotate(30 278 40)"/>
<ellipse cx="54" cy="164" rx="7" ry="3.5" transform="rotate(35 54 164)"/>
<ellipse cx="270" cy="160" rx="7" ry="3.5" transform="rotate(-30 270 160)"/>
</g>
{icon}
</svg>"""
    return svg_data_uri(svg)


# =====================================================================
# 전체 화면 CSS
# =====================================================================
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Jua&family=Gowun+Dodum&display=swap');

html, body, .stApp, p, li, label, input, textarea, button {
  font-family: 'Gowun Dodum', system-ui, sans-serif;
}
h1, h2, h3, h4 { font-family: 'Jua', system-ui, sans-serif !important; font-weight: 400 !important; }

header[data-testid="stHeader"] { background: transparent; }
.block-container { max-width: 1040px; padding-top: 2.2rem; }

/* 버튼: 둥글고 Jua 글꼴 */
.stButton button, .stFormSubmitButton button {
  font-family: 'Jua', system-ui, sans-serif;
  font-size: 1.05rem;
  border-radius: 999px;
  border: 2px solid #1F2B24;
}

/* 입력 폼과 카드: 밥알처럼 하얀 배경 */
[data-testid="stForm"] {
  background: #FFFDF5;
  border: 2px solid #1F2B24;
  border-radius: 22px;
  padding: 1.4rem 1.8rem;
}
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 18px; }

/* ---------- ① 첫 화면 ---------- */
.gb-intro {
  border: 2px solid #1F2B24; border-radius: 999px; background: #FFFDF5;
  padding: 0.45rem 1.1rem; display: inline-block; font-size: 0.98rem;
}
.gb-hero { text-align: center; margin: 2.2rem 0 0.6rem; }
.gb-hero img { display: block; margin: 0 auto; }
.gb-hero-name { font-family: 'Jua', sans-serif; font-size: 76px; line-height: 1.1; color: #1F2B24; margin-top: 10px; }
.gb-hero-team { font-weight: 700; letter-spacing: 0.4em; font-size: 14px; color: #1F2B24; }
.gb-scroll { text-align: center; margin: 2.4rem 0 2.8rem; font-size: 0.95rem; color: #1F2B24; }
.gb-scroll .gb-arrow { display: block; font-size: 1.6rem; animation: gb-bounce 1.6s infinite; }
@keyframes gb-bounce { 0%,100% { transform: translateY(0); } 50% { transform: translateY(8px); } }
@media (prefers-reduced-motion: reduce) { .gb-scroll .gb-arrow { animation: none; } }

.gb-feature-title {
  font-family: 'Jua', sans-serif; font-size: 1.7rem; display: inline-block;
  border-bottom: 6px solid #F6C945; line-height: 1.2; margin-bottom: 0.6rem;
}
.gb-feature-text { font-size: 1.05rem; line-height: 1.7; }
.gb-preview {
  background: #FFFDF5; border: 2px solid #1F2B24; border-radius: 20px;
  padding: 18px; box-shadow: 6px 6px 0 #F6C945;
}
.gb-pv-row { display: flex; align-items: center; gap: 8px; margin: 8px 0; font-size: 0.85rem; }
.gb-pv-field { flex: 1; height: 22px; border: 1.5px solid #1F2B24; border-radius: 8px; background: #fff; }
.gb-pv-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 12px; }
.gb-pv-card { border: 1.5px solid #1F2B24; border-radius: 12px; overflow: hidden; background: #fff; font-size: 0.8rem; }
.gb-pv-card img { display: block; width: 100%; }
.gb-pv-card div { padding: 4px 8px; }
.gb-pv-btn { display: inline-block; margin-top: 10px; padding: 4px 16px; border-radius: 999px; background: #1F2B24; color: #FFFDF5; font-family: 'Jua', sans-serif; }
.gb-footer { text-align: center; margin: 3rem 0 1rem; font-size: 0.85rem; letter-spacing: 0.2em; }

/* ---------- ④⑤ 메인 화면 ---------- */
.gb-logo-small { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.gb-logo-small span { font-family: 'Jua', sans-serif; font-size: 1.3rem; line-height: 1; }
.gb-tagline { font-size: 1.02rem; line-height: 1.9; }
.gb-tagline span { border-bottom: 2px solid #1F2B24; }
.gb-userid {
  border: 2px solid #1F2B24; border-radius: 12px; background: #FFFDF5;
  padding: 6px 12px; font-family: 'Jua', sans-serif; font-size: 1.1rem; text-align: center;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.gb-avatar {
  width: 58px; height: 58px; border-radius: 50%; border: 2px solid #1F2B24;
  background: #F6C945; display: flex; align-items: center; justify-content: center;
  font-family: 'Jua', sans-serif; font-size: 1.6rem; margin: 0 auto;
}
.gb-slider-ends { display: flex; justify-content: space-between; font-size: 0.9rem; margin-top: -0.6rem; }

.gb-section-title { display: flex; align-items: center; gap: 12px; font-family: 'Jua', sans-serif; font-size: 1.8rem; }
.gb-section-title::after { content: ""; flex: 1; height: 3px; background: #1F2B24; border-radius: 2px; }
.gb-share-label { text-align: right; font-size: 0.95rem; padding-top: 0.55rem; }
.gb-chips { display: flex; flex-wrap: wrap; gap: 6px; margin: 0.3rem 0 1rem; }
.gb-chip { background: #FFFDF5; border: 1.5px solid #1F2B24; border-radius: 999px; padding: 2px 12px; font-size: 0.9rem; }

.gb-card-img img { display: block; width: 100%; height: 170px; object-fit: cover; border-radius: 12px; border: 2px solid #1F2B24; }
.gb-card-img a:focus-visible img { outline: 3px solid #F07B2A; outline-offset: 2px; }
.gb-card-name { font-family: 'Jua', sans-serif; font-size: 1.15rem; line-height: 1.3; }
.gb-card-name small { font-family: 'Gowun Dodum', sans-serif; font-size: 0.85rem; }
.gb-card-line { font-size: 0.92rem; color: #3F4A43; }
.gb-cost { display: inline-block; margin-top: 4px; background: #F6C945; border-radius: 999px; padding: 1px 10px; font-size: 0.88rem; }
.gb-cost.unknown { background: #EFE6CC; }
</style>
"""
