from fastapi import FastAPI, Response
from pydantic import BaseModel
from jinja2 import Environment, Undefined
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

import uuid
import os
import unicodedata

app = FastAPI(title="Arabic PDF Engine - PRO FIX FINAL")

BASE_DIR = os.path.abspath(".")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
FONT_DIR = os.path.join(BASE_DIR, "fonts")

os.makedirs(TEMPLATE_DIR, exist_ok=True)
os.makedirs(FONT_DIR, exist_ok=True)

# 🔥 IMPORTANT: SINGLE SOURCE OF TRUTH
font_config = FontConfiguration()

FONT_PATH = os.path.join(
    FONT_DIR,
    "NotoNaskhArabic-Regular.ttf"
).replace("\\", "/")


# =========================
# MODEL
# =========================
class GeneratePdfRequest(BaseModel):
    template_name: str | None = None
    template_content: str | None = None
    data: dict = {}


# =========================
# SAFE JINJA
# =========================
class PlaceholderUndefined(Undefined):
    def __str__(self):
        return "...................."


# =========================
# CLEAN DATA (ONLY NORMALIZATION)
# =========================
def normalize(value):
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)  # 🔥 مهم (NFC وليس NFKC)
    return value


def clean_data(data: dict):
    return {k: normalize(v) for k, v in (data or {}).items()}


# =========================
# TEMPLATE
# =========================
def load_template(name: str):
    path = os.path.join(TEMPLATE_DIR, name)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# =========================
# CSS (MINIMAL + CORRECT)
# =========================
def build_css():
    return CSS(string=f"""
        @font-face {{
            font-family: 'NotoNaskh';
            src: url('file:///{FONT_PATH}');
        }}

        @page {{
            size: A4;
            margin: 20mm;
        }}

        body {{
            font-family: 'NotoNaskh';
            direction: rtl;
            text-align: right;

            font-size: 14pt;
            line-height: 1.9;
            color: #000;

            /* 🔥 THIS IS THE REAL FIX */
            unicode-bidi: plaintext;

            text-rendering: optimizeLegibility;
        }}

        * {{
            font-family: 'NotoNaskh' !important;
        }}

        p, div, span {{
            direction: rtl;
            unicode-bidi: plaintext;
        }}

        .ltr {{
            direction: ltr;
            unicode-bidi: embed;
        }}
    """)

# =========================
# PDF ENGINE
# =========================
def generate_pdf(html_content: str) -> bytes:
    css = build_css()

    html = HTML(
        string=html_content,
        base_url=FONT_DIR
    )

    return html.write_pdf(
        stylesheets=[css],
        font_config=font_config  # 🔥 THIS IS CRITICAL
    )


# =========================
# API
# =========================
@app.post("/generate-pdf")
async def generate_pdf_api(req: GeneratePdfRequest):

    html = req.template_content
    if not html:
        html = load_template(req.template_name)

    safe_data = clean_data(req.data)

    env = Environment(
        undefined=PlaceholderUndefined,
        autoescape=False
    )

    template = env.from_string(html)
    rendered = template.render(safe_data)

    pdf = generate_pdf(rendered)

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=doc_{uuid.uuid4().hex[:8]}.pdf"
        }
    )