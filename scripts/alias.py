"""한글 키워드 → 영문 별칭 사전. 치트시트와 팔레트가 공유한다.

template/cheatsheet_template.html 의 ALIAS 에서 옮겨왔다.
긴 키워드가 먼저 와야 한다 (별점 → 별 순서).
"""

ALIAS = [
    ('별점', 'rating stars score'),
    ('빈별', 'empty star outline'),
    ('별', 'star'),
    ('빈하트', 'empty heart outline'),
    ('하트', 'heart love'),
    ('화살', 'arrow'),
    ('오른', 'right arrow'),
    ('왼', 'left arrow'),
    ('위', 'up arrow'),
    ('아래', 'down arrow'),
    ('양쪽', 'both arrow'),
    ('체크박스', 'checkbox ballot'),
    ('체크', 'check ok done v'),
    ('엑스', 'x cross no'),
    ('겹원', 'double circle'),
    ('빈원', 'empty circle'),
    ('원문', 'circled number'),
    ('원', 'circle'),
    ('네모', 'square box'),
    ('세모', 'triangle'),
    ('삼각', 'triangle play'),
    ('마름모', 'diamond'),
    ('손', 'hand point finger'),
    ('전화', 'phone tel call'),
    ('음표', 'music note melody'),
    ('참고', 'reference mark note'),
    ('낫표', 'corner bracket quote'),
    ('꺾쇠', 'angle bracket'),
    ('검은괄호', 'lenticular bracket'),
    ('줄임', 'ellipsis dots'),
    ('줄표', 'em dash'),
    ('엔대시', 'en dash'),
    ('불릿', 'bullet point'),
    ('점', 'middle dot'),
    ('곱', 'multiply times x'),
    ('나누기', 'divide division'),
    ('플마', 'plus minus'),
    ('다름', 'not equal'),
    ('이상', 'greater equal'),
    ('이하', 'less equal'),
    ('약', 'approximately'),
    ('섭씨', 'celsius temperature degree'),
    ('각도', 'degree angle'),
    ('제곱미터', 'square meter m2'),
    ('세제곱미터', 'cubic meter m3'),
    ('루베', 'cubic meter m3'),
    ('세제곱', 'cubed superscript 3'),
    ('제곱', 'squared superscript 2'),
    ('킬로그램', 'kg kilogram'),
    ('밀리미터', 'mm millimeter'),
    ('센티', 'cm centimeter'),
    ('킬로미터', 'km kilometer'),
    ('밀리리터', 'ml milliliter'),
    ('리터', 'liter litre'),
    ('유로', 'euro eur currency'),
    ('주식', 'corporation company inc'),
    ('등록상표', 'registered r'),
    ('상표', 'trademark tm'),
    ('저작권', 'copyright c'),
    ('로마', 'roman numeral'),
    ('커맨드', 'command cmd'),
    ('옵션', 'option alt'),
    ('시프트', 'shift'),
    ('컨트롤', 'control ctrl'),
    ('토글', 'toggle disclosure'),
]


def alias_for(ko_name, shortcut):
    """항목 이름·단축어에 들어간 키워드로 영문 별칭 문자열을 만든다."""
    base = (ko_name or "") + (shortcut or "")
    hits = []
    for kw, en in ALIAS:
        if kw in base:
            hits.append(en)
    return " ".join(dict.fromkeys(" ".join(hits).split()))
