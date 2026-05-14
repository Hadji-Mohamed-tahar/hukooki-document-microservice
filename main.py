from fastapi import FastAPI, Response
from pydantic import BaseModel
from jinja2 import Environment, Undefined
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
import uuid
import os
import re

# =========================
# APP
# =========================
app = FastAPI(title="Arabic PDF Engine — HarfBuzz Native")

BASE_DIR     = os.path.abspath(".")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
FONT_DIR     = os.path.join(BASE_DIR, "fonts")

os.makedirs(TEMPLATE_DIR, exist_ok=True)
os.makedirs(FONT_DIR, exist_ok=True)

font_config = FontConfiguration()

AMIRI_REGULAR    = os.path.join(FONT_DIR, "Amiri-Regular.ttf").replace("\\", "/")
AMIRI_BOLD       = os.path.join(FONT_DIR, "Amiri-Bold.ttf").replace("\\", "/")
AMIRI_ITALIC     = os.path.join(FONT_DIR, "Amiri-Italic.ttf").replace("\\", "/")
AMIRI_BOLDITALIC = os.path.join(FONT_DIR, "Amiri-BoldItalic.ttf").replace("\\", "/")


# =========================
# MODEL
# =========================
class GeneratePdfRequest(BaseModel):
    template_name:    str | None = None
    template_content: str | None = None
    data: dict = {}


# =========================
# JINJA UNDEFINED
# -------------------------
# حقل غير موجود → نص فارغ
# الخط السفلي في CSS يظهر تلقائياً
# =========================
class EmptyUndefined(Undefined):
    def __str__(self):
        return ""

    def __iter__(self):
        return iter([])

    def __bool__(self):
        return False


# =========================
# UNICODE CLEANER
# =========================
class UnicodeCleaner:

    TATWEEL            = "\u0640"
    ZWJ                = "\u200D"
    DIRECTION_CONTROLS = re.compile(r'[\u202A-\u202E\u2066-\u2069\u200E\u200F]')

    @classmethod
    def _fix_decomposed_hamza(cls, text: str) -> str:
        text = text.replace("\u0627\u0654", "\u0623")  # ا + ٔ → أ
        text = text.replace("\u0627\u0655", "\u0625")  # ا + ٕ → إ
        text = text.replace("\u0648\u0654", "\u0624")  # و + ٔ → ؤ
        text = text.replace("\u064A\u0654", "\u0626")  # ي + ٔ → ئ
        text = text.replace("\u0627\u0653", "\u0622")  # ا + ٓ → آ
        return text

    @classmethod
    def clean(cls, text: str) -> str:
        if not isinstance(text, str) or not text:
            return text
        text = cls._fix_decomposed_hamza(text)
        text = text.replace(cls.TATWEEL, "")
        text = text.replace(cls.ZWJ, "")
        text = cls.DIRECTION_CONTROLS.sub("", text)
        return text

    @classmethod
    def clean_value(cls, value):
        if isinstance(value, str):
            return cls.clean(value)
        elif isinstance(value, list):
            return [cls.clean_value(i) for i in value]
        elif isinstance(value, dict):
            return {k: cls.clean_value(v) for k, v in value.items()}
        return value

    @classmethod
    def clean_data(cls, data: dict) -> dict:
        return cls.clean_value(data)


# =========================
# TEMPLATE CLEANER
# =========================
class TemplateCleaner:

    TATWEEL_PATTERN    = re.compile(r'\u0640+')
    DIRECTION_CONTROLS = re.compile(r'[\u202A-\u202E\u2066-\u2069\u200E\u200F]')
    TAG_PATTERN        = re.compile(r'(<[^>]+>|{[{%#][^}]*[}%#]})')

    @classmethod
    def _fix_decomposed_hamza(cls, text: str) -> str:
        text = text.replace("\u0627\u0654", "\u0623")
        text = text.replace("\u0627\u0655", "\u0625")
        text = text.replace("\u0648\u0654", "\u0624")
        text = text.replace("\u064A\u0654", "\u0626")
        text = text.replace("\u0627\u0653", "\u0622")
        return text

    @classmethod
    def _clean_text_node(cls, text: str) -> str:
        text = cls._fix_decomposed_hamza(text)
        text = cls.TATWEEL_PATTERN.sub("", text)
        text = cls.DIRECTION_CONTROLS.sub("", text)
        return text

    @classmethod
    def clean_template(cls, html: str) -> str:
        parts = cls.TAG_PATTERN.split(html)
        result = []
        for part in parts:
            if part.startswith('<') or part.startswith('{'):
                result.append(part)
            else:
                result.append(cls._clean_text_node(part))
        return "".join(result)


# =========================
# LOAD TEMPLATE
# =========================
def load_template(name: str) -> str:
    path = os.path.join(TEMPLATE_DIR, name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Template not found: {name}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# =========================
# CSS
# =========================
def build_css() -> CSS:
    return CSS(string=f"""
        @font-face {{
            font-family: 'Amiri';
            src: url('file:///{AMIRI_REGULAR}') format('truetype');
            font-weight: normal;
            font-style: normal;
        }}
        @font-face {{
            font-family: 'Amiri';
            src: url('file:///{AMIRI_BOLD}') format('truetype');
            font-weight: bold;
            font-style: normal;
        }}
        @font-face {{
            font-family: 'Amiri';
            src: url('file:///{AMIRI_ITALIC}') format('truetype');
            font-weight: normal;
            font-style: italic;
        }}
        @font-face {{
            font-family: 'Amiri';
            src: url('file:///{AMIRI_BOLDITALIC}') format('truetype');
            font-weight: bold;
            font-style: italic;
        }}

        @page {{
            size: A4;
            margin: 20mm;
        }}

        html {{
            direction: rtl;
        }}

        body {{
            font-family: 'Amiri', serif;
            direction: rtl;
            text-align: right;
            font-size: 14pt;
            line-height: 1.8;
            color: #000;
            text-rendering: optimizeLegibility;
        }}

        p, div, span, li, td, th,
        h1, h2, h3, h4, h5, h6 {{
            direction: rtl;
            unicode-bidi: plaintext;
        }}

        .ltr, .en {{
            direction: ltr;
            text-align: left;
            unicode-bidi: isolate;
            display: inline-block;
        }}

        table {{
            direction: rtl;
            border-collapse: collapse;
            width: 100%;
        }}

        th, td {{
            padding: 8px;
            text-align: right;
            direction: rtl;
            unicode-bidi: plaintext;
        }}

        h1, h2, h3, h4, h5, h6 {{
            font-weight: bold;
            margin-top: 1em;
            margin-bottom: 0.5em;
        }}

        ul, ol {{
            padding-right: 2em;
            padding-left: 0;
        }}

        .page-break {{
            page-break-after: always;
        }}

        p, li {{
            orphans: 3;
            widows: 3;
        }}
    """, font_config=font_config)


# =========================
# PDF GENERATOR
# =========================
def generate_pdf(html_content: str) -> bytes:
    css = build_css()
    html_obj = HTML(
        string=html_content,
        base_url="file:///" + BASE_DIR.replace("\\", "/") + "/"
    )
    return html_obj.write_pdf(
        stylesheets=[css],
        font_config=font_config
    )


# =========================
# DIAGNOSTIC ENDPOINT
# =========================
@app.get("/diagnose-template/{template_name}")
def diagnose_template(template_name: str):
    try:
        content = load_template(template_name)
    except FileNotFoundError as e:
        return {"error": str(e)}

    tatweel_positions  = []
    decomposed_hamza   = []
    direction_controls = []

    i = 0
    while i < len(content):
        ch   = content[i]
        code = ord(ch)

        if code == 0x0640:
            tatweel_positions.append({
                "pos":     i,
                "context": content[max(0, i - 10):i + 10]
            })

        if code == 0x0627 and i + 1 < len(content) and ord(content[i + 1]) in (0x0654, 0x0655, 0x0653):
            decomposed_hamza.append({
                "pos":     i,
                "codes":   [f"U+{ord(c):04X}" for c in content[i:i + 2]],
                "context": content[max(0, i - 5):i + 7]
            })

        if 0x202A <= code <= 0x202E or 0x2066 <= code <= 0x2069 or code in (0x200E, 0x200F):
            direction_controls.append({
                "pos":     i,
                "char":    f"U+{code:04X}",
                "context": content[max(0, i - 5):i + 6]
            })

        i += 1

    return {
        "template":                   template_name,
        "tatweel_count":              len(tatweel_positions),
        "decomposed_hamza_count":     len(decomposed_hamza),
        "direction_controls_count":   len(direction_controls),
        "tatweel_samples":            tatweel_positions[:5],
        "decomposed_hamza_samples":   decomposed_hamza[:5],
        "direction_control_samples":  direction_controls[:5],
    }


# =========================
# API
# =========================
@app.get("/")
def home():
    return {
        "success": True,
        "message": "Arabic PDF Engine — HarfBuzz Native Pipeline",
        "pipeline": [
            "1. load_template",
            "2. TemplateCleaner  → Tatweel + hamza + direction controls",
            "3. UnicodeCleaner   → data Tatweel + hamza + direction controls",
            "4. Jinja2 render    → pure Unicode, empty string for missing fields",
            "5. WeasyPrint       → HarfBuzz shaping + Pango BiDi + Cairo PDF",
        ],
        "removed": [
            "arabic_reshaper",
            "python-bidi",
            "get_display()",
            "NFC normalization",
            "font-feature-settings",
            "PlaceholderUndefined (dots)",
        ]
    }


@app.post("/generate-pdf")
async def generate_pdf_api(req: GeneratePdfRequest):

    # 1. تحميل الـ template
    html = req.template_content
    if not html:
        if not req.template_name:
            return {"success": False, "message": "Template required"}
        html = load_template(req.template_name)

    # 2. تنظيف الـ template
    html = TemplateCleaner.clean_template(html)

    # 3. تنظيف البيانات
    clean_data = UnicodeCleaner.clean_data(req.data)

    # 4. Render — الحقول الغائبة تصبح نص فارغ "" لا نقاط
    env = Environment(undefined=EmptyUndefined, autoescape=False)
    template = env.from_string(html)
    rendered_html = template.render(clean_data)

    # 5. توليد PDF
    pdf = generate_pdf(rendered_html)

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=doc_{uuid.uuid4().hex[:8]}.pdf"
        }
    )


@app.get("/health")
def health_check():
    fonts = {
        "Amiri-Regular.ttf":    os.path.exists(AMIRI_REGULAR),
        "Amiri-Bold.ttf":       os.path.exists(AMIRI_BOLD),
        "Amiri-Italic.ttf":     os.path.exists(AMIRI_ITALIC),
        "Amiri-BoldItalic.ttf": os.path.exists(AMIRI_BOLDITALIC),
    }
    return {
        "status":          "ready" if all(fonts.values()) else "missing_fonts",
        "fonts":           fonts,
        "engine":          "WeasyPrint + HarfBuzz + Pango + Cairo",
        "arabic_reshaper": "NOT USED",
        "python_bidi":     "NOT USED",
        "get_display":     "NOT USED",
        "nfc_normalize":   "NOT USED",
        "missing_fields":  "empty string — no dots",
    }


# =========================
# RUN
# =========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)