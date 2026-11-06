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


_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}


def photo_uri(path) -> str:
    """사용자가 올린 사진 파일 → <img src="...">에 넣을 수 있는 형태."""
    mime = _MIME.get(path.suffix.lower(), "image/png")
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


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

/* 전체를 조금 크게: Streamlit은 rem 단위를 쓰므로 기준 글자 크기를 16px → 18px로 */
html { font-size: 18px; }
html, body, .stApp, p, li, label, input, textarea, button {
  font-family: 'Gowun Dodum', system-ui, sans-serif;
}
h1, h2, h3, h4 { font-family: 'Jua', system-ui, sans-serif !important; font-weight: 400 !important; }

header[data-testid="stHeader"] { background: transparent; }

/* 입력칸 이름(라벨)과 입력한 글자를 조금 더 크게 */
[data-testid="stWidgetLabel"] p { font-size: 1.12rem !important; }
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea, [data-testid="stDateInput"] input,
[data-testid="stDateInputField"], [data-testid="stDateInputField"] span,
[data-testid="stSelectbox"] input, [data-testid="stSelectbox"] div,
[data-testid="stMultiSelect"] input, [data-testid="stMultiSelect"] div, [data-testid="stMultiSelect"] span {
  font-size: 1.1rem !important;
}
[data-testid="stFileUploaderDropzone"] { font-size: 1.05rem; }
[data-testid="stFileUploaderDropzone"] small { font-size: 0.95rem; }

/* 팝업(로그인 · 회원가입 · 공유 · 삭제): 뒤 화면은 노란색 대신 회색으로 어둡게, 팝업 상자는 흰색 */
[data-testid="stDialog"] { background-color: rgba(31, 43, 36, 0.45) !important; }
[data-testid="stDialog"] > div { background-color: #FFFFFF !important; }

/* 사용자가 입력하는 칸: 테두리를 그려서 어디에 쓰는지 잘 보이게 (폼 · 팝업 · 여행 수정 모두) */
[data-testid="stTextInputRootElement"], [data-testid="stTextAreaRootElement"],
[data-testid="stSelectbox"] [role="group"], [data-testid="stMultiSelect"] [role="group"],
[data-testid="stDateInputField"] {
  border: 1.5px solid #1F2B24 !important; border-radius: 10px !important; background: #FFFFFF !important;
}
[data-testid="stTextInputRootElement"]:focus-within, [data-testid="stTextAreaRootElement"]:focus-within,
[data-testid="stSelectbox"] [role="group"]:focus-within, [data-testid="stMultiSelect"] [role="group"]:focus-within,
[data-testid="stDateInputField"]:focus-within {
  border-color: #F07B2A !important; box-shadow: 0 0 0 2px rgba(240, 123, 42, 0.25);
}
[data-testid="stFileUploaderDropzone"] {
  border: 1.5px dashed #1F2B24 !important; border-radius: 12px !important; background: #FFFFFF !important;
}
.block-container { max-width: 1440px; padding: 2.2rem 3rem 3rem; }

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
.gb-hero img { display: block; margin: 0 auto; width: 230px; height: 230px; }
.gb-hero-name { font-family: 'Jua', sans-serif; font-size: 92px; line-height: 1.1; color: #1F2B24; margin-top: 12px; }
.gb-hero-team { font-weight: 700; letter-spacing: 0.4em; font-size: 16px; color: #1F2B24; }
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
.gb-pv-hint {
  display: inline-block; margin-top: 12px; padding: 4px 12px; border-radius: 10px;
  background: #F6C945; font-family: 'Jua', sans-serif; font-size: 0.9rem; transform: rotate(-2deg);
}
.gb-pv-link { display: flex; align-items: center; gap: 14px; }
.gb-pv-link .gb-pv-card { flex: 0 0 40%; box-shadow: 0 0 0 3px #F07B2A; }
.gb-pv-arrow { font-family: 'Jua', sans-serif; text-align: center; font-size: 1rem; line-height: 1.3; }
.gb-pv-arrow b { display: block; font-size: 1.8rem; font-weight: 400; }
.gb-pv-browser { flex: 1; border: 1.5px solid #1F2B24; border-radius: 12px; background: #fff; overflow: hidden; }
.gb-pv-bar { display: flex; align-items: center; gap: 4px; padding: 6px 8px; background: #FFE8B3; border-bottom: 1.5px solid #1F2B24; }
.gb-pv-bar span { width: 8px; height: 8px; border-radius: 50%; background: #1F2B24; opacity: .5; }
.gb-pv-url { flex: 1; margin-left: 6px; background: #fff; border: 1px solid #1F2B24; border-radius: 6px; padding: 0 6px; font-size: 0.72rem; }
.gb-pv-page { padding: 10px; display: grid; gap: 6px; }
.gb-pv-page i { display: block; height: 8px; border-radius: 4px; background: #EFE6CC; }
.gb-pv-page i:first-child { width: 60%; height: 12px; background: #F6C945; }
.gb-pv-page i:nth-child(3) { width: 80%; }
.gb-pv-files { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.gb-pv-file { border: 1.5px solid #1F2B24; border-radius: 12px; background: #fff; overflow: hidden; font-size: 0.75rem; }
.gb-pv-file img { display: block; width: 100%; }
.gb-pv-file div { padding: 3px 6px; }
.gb-footer { text-align: center; margin: 3rem 0 1rem; font-size: 0.85rem; letter-spacing: 0.2em; }

/* ---------- ④⑤ 메인 화면 ---------- */
.gb-logo-small { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.gb-logo-small img { width: 64px; height: 64px; }
.gb-logo-small span { font-family: 'Jua', sans-serif; font-size: 1.4rem; line-height: 1; }
.gb-tagline { font-size: 1.05rem; line-height: 1.8; }

/* 오른쪽 위: [ID 상자] / 로그아웃(글자 링크) + 프로필 동그라미(아이디 전체) */
.gb-userid {
  border: 2px solid #1F2B24; border-radius: 10px; background: #FFFDF5;
  padding: 6px 12px; font-size: 1rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  text-align: center;
}
.gb-userid b { font-family: 'Jua', sans-serif; font-weight: 400; margin-right: 6px; }
.gb-avatar {
  width: 92px; height: 92px; border-radius: 50%; border: 2px solid #1F2B24;
  background: #F6C945; display: flex; align-items: center; justify-content: center; text-align: center;
  font-family: 'Jua', sans-serif; line-height: 1.1; padding: 8px; box-sizing: border-box;
  overflow-wrap: anywhere; margin: 0 auto;
}
/* 로그아웃: 버튼 대신 파란 밑줄 글자처럼 보이게, 오른쪽 정렬 */
.st-key-logout { align-self: flex-end !important; }
.st-key-logout button {
  border: none !important; background: transparent !important; padding: 0 !important; min-height: 0 !important;
  font-family: 'Gowun Dodum', sans-serif !important; font-size: 0.95rem !important;
  color: #1F56B8 !important; text-decoration: underline; text-underline-offset: 3px;
}
.st-key-logout button:hover { color: #163F87 !important; }

.gb-form-title { font-family: 'Jua', sans-serif; font-size: 1.55rem; margin: -0.2rem 0 0.4rem; }

.gb-section-title { display: flex; align-items: center; gap: 12px; font-family: 'Jua', sans-serif; font-size: 1.8rem; }
.gb-section-title::after { content: ""; flex: 1; height: 3px; background: #1F2B24; border-radius: 2px; }
.gb-share-label { text-align: right; font-size: 0.95rem; padding-top: 0.55rem; }
.gb-chips { display: flex; flex-wrap: wrap; gap: 6px; margin: 0.3rem 0 1rem; }
.gb-chip { background: #FFFDF5; border: 1.5px solid #1F2B24; border-radius: 999px; padding: 2px 12px; font-size: 0.9rem; }

.gb-card-img { margin-bottom: 14px; }  /* 그림과 하트 사이 간격 */
.gb-card-img img { display: block; width: 100%; aspect-ratio: 2 / 1; object-fit: cover; border-radius: 12px; border: 2px solid #1F2B24; }
.gb-card-img a:focus-visible img { outline: 3px solid #F07B2A; outline-offset: 2px; }
.gb-card-name { font-family: 'Jua', sans-serif; font-size: 1.15rem; line-height: 1.3; }
.gb-card-name small { font-family: 'Gowun Dodum', sans-serif; font-size: 0.85rem; }
/* 특징 태그: 그 장소만의 특징은 진하게, 흔한 태그(사진·실내·야외)는 흐리게 */
.gb-tags { display: flex; flex-wrap: wrap; gap: 6px; margin: 2px 0 10px; }
.gb-tag {
  font-size: 0.92rem; font-weight: 700; color: #1F2B24; background: #FFFDF5;
  border: 1.5px solid #1F2B24; border-radius: 8px; padding: 1px 9px;
}
.gb-tag.common { font-weight: 400; color: #6B7068; border-color: #CFC6AE; background: transparent; }
/* 맨 아래 줄: 1인 비용 + 머무는 시간. 카드 테두리와 붙지 않게 아래 여백 */
.gb-card-bottom { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 12px; }
.gb-cost { display: inline-block; background: #F6C945; border-radius: 999px; padding: 2px 12px; font-size: 0.9rem; }
.gb-cost.unknown { background: #EFE6CC; }
.gb-time { display: inline-block; font-size: 0.88rem; color: #3F4A43; }
.gb-save-note { text-align: center; font-size: 0.92rem; color: #3F4A43; margin-top: 4px; }


/* ---------- 김밥 AI 추천 포인트 ---------- */
.gb-ai-reason {
    margin-top: 10px;
    margin-bottom: 12px;
    padding: 12px 14px;
    border-radius: 12px;
    background: #FFFDF5;
    border: 1.5px solid #1F2B24;
}

.gb-ai-reason-badge {
    display: inline-block;
    font-family: 'Jua', sans-serif;
    font-size: 0.85rem;
    color: #1F2B24;
    background: #F6C945;
    border-radius: 8px;
    padding: 3px 10px;
    margin-bottom: 8px;
}

.gb-ai-reason-text {
    font-family: 'Gowun Dodum', sans-serif;
    font-size: 0.9rem;
    line-height: 1.6;
    color: #1F2B24;
    overflow-wrap: anywhere;
}

/* 사물함으로 돌아가기: 로고와 떨어뜨리고, 노란 버튼으로 눈에 띄게 */
.st-key-back_to_locker { margin-top: 1.6rem; }
.st-key-back_to_locker button {
  background: #F6C945 !important; border: 2px solid #1F2B24 !important; border-radius: 999px !important;
  box-shadow: 3px 3px 0 #1F2B24; padding: 0.35rem 1.3rem !important;
}
.st-key-back_to_locker button p { font-family: 'Jua', sans-serif !important; font-size: 1.15rem !important; }
.st-key-back_to_locker button:hover { background: #F9DC7A !important; }

/* ---------- 예전 여행 기획 사물함 ---------- */
.gb-double-line { border-top: 3px solid #1F2B24; border-bottom: 3px solid #1F2B24; height: 6px; margin: 2.6rem 0 1.6rem; }
.gb-locker-title {
  display: inline-block; font-family: 'Jua', sans-serif; font-size: 1.9rem; padding: 0.3rem 1.4rem;
  background: #F6C945; border: 3px dashed #1F2B24; border-radius: 28px; transform: rotate(-1.5deg);
  margin-bottom: 0.4rem;
}
.gb-locker-sub { font-size: 0.95rem; margin-bottom: 1rem; }
.gb-file-img img {
  display: block; width: 100%; aspect-ratio: 16 / 10; object-fit: cover;
  border-radius: 14px; border: 2px solid #1F2B24; box-shadow: 5px 5px 0 #F6C945;
}
.gb-file-meta { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin: 12px 0 6px; }
.gb-file-name { font-family: 'Jua', sans-serif; font-size: 1.1rem; border: 2px solid #1F2B24; border-radius: 8px; padding: 1px 10px; background: #FFFDF5; }
.gb-file-date { font-size: 0.8rem; border: 1.5px solid #1F2B24; border-radius: 6px; padding: 1px 8px; background: #FFFDF5; }
.gb-file-note { font-size: 0.9rem; border-bottom: 1.5px solid #1F2B24; padding-bottom: 4px; min-height: 1.6rem;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.gb-file-shared { display: inline-block; font-size: 0.8rem; background: #3C9A4E; color: #fff; border-radius: 999px; padding: 1px 10px; }

/* ---------- 여행 자세히 보기 ---------- */
.gb-detail-photo img {
  display: block; width: 100%; max-width: 640px; aspect-ratio: 16 / 10; object-fit: cover; margin: 0.6rem auto 0;
  border-radius: 20px; border: 2px solid #1F2B24; box-shadow: 8px 8px 0 #F6C945;
}
.gb-detail-title { font-family: 'Jua', sans-serif; font-size: 2rem; margin: 1rem 0 0.2rem; }
.gb-subtitle { font-family: 'Jua', sans-serif; font-size: 1.35rem; margin: 1.4rem 0 0.4rem; }
/* 공유 상태 글자가 옆의 아이콘 버튼과 같은 높이에 오도록 (Streamlit 기본 아래 여백 -1rem 없애기) */
[data-testid="stMarkdownContainer"]:has(> .gb-share-line) { margin-bottom: 0 !important; }
/* 휴지통: 오른쪽 끝, 마우스를 올리면 빨갛게 */
.st-key-delete_trip { align-self: flex-end !important; width: auto !important; }
.st-key-delete_trip button:hover { color: #C0392B !important; border-color: #C0392B !important; }
.gb-share-line { display: inline-block; background: #FFFDF5; border: 1.5px solid #1F2B24; border-radius: 999px; padding: 3px 14px; margin: 0; }
.gb-fav-box { background: #FFFDF5; border: 2px solid #1F2B24; border-radius: 16px; padding: 10px 16px; margin-bottom: 10px; }
.gb-fav-box b { font-family: 'Jua', sans-serif; font-weight: 400; font-size: 1.1rem; }
.gb-fav-box ul { margin: 6px 0 0; padding-left: 1.2rem; }
</style>
"""
