from fastapi import FastAPI, Response
from pydantic import BaseModel
from jinja2 import Environment, Undefined

from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

import arabic_reshaper
from bidi.algorithm import get_display

import uuid
import os
import re

# =========================
# APP
# =========================
app = FastAPI(title="Arabic PDF Engine - Amiri Edition")

BASE_DIR = os.path.abspath(".")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
FONT_DIR = os.path.join(BASE_DIR, "fonts")

os.makedirs(TEMPLATE_DIR, exist_ok=True)
os.makedirs(FONT_DIR, exist_ok=True)

# =========================
# FONT CONFIG
# =========================
font_config = FontConfiguration()

# Amiri Font
AMIRI_REGULAR = os.path.join(FONT_DIR, "Amiri-Regular.ttf").replace("\\", "/")
AMIRI_BOLD = os.path.join(FONT_DIR, "Amiri-Bold.ttf").replace("\\", "/")
AMIRI_ITALIC = os.path.join(FONT_DIR, "Amiri-Italic.ttf").replace("\\", "/")
AMIRI_BOLDITALIC = os.path.join(FONT_DIR, "Amiri-BoldItalic.ttf").replace("\\", "/")

# =========================
# MODEL
# =========================
class GeneratePdfRequest(BaseModel):
    template_name: str | None = None
    template_content: str | None = None
    data: dict = {}


# =========================
# JINJA SAFE PLACEHOLDER
# =========================
class PlaceholderUndefined(Undefined):
    def __str__(self):
        return "...................."


# =========================
# ARABIC TEXT PROCESSOR
# =========================
class ArabicTextProcessor:
    
    ARABIC_RANGE = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
    
    @classmethod
    def contains_arabic(cls, text: str) -> bool:
        if not text:
            return False
        return bool(cls.ARABIC_RANGE.search(str(text)))
    
    @classmethod
    def reshape_arabic(cls, text: str) -> str:
        if not text or not cls.contains_arabic(text):
            return text
        
        try:
            # Remove any existing tatweel from source text
            text = text.replace("\u0640", "")
            
            configuration = {
                'delete_harakat': False,
                'support_ligatures': True,
                'RIAL SIGN': True,
                'delete_tatweel': True,
                'use_unshaped_instead_of_isolated': False,
            }
            
            reshaped = arabic_reshaper.reshape(text, configuration=configuration)
            # return get_display(reshaped)
        except Exception as e:
            print(f"Arabic reshaping warning: {e}")
            return text
    
    @classmethod
    def process_value(cls, value):
        if isinstance(value, str):
            return cls.reshape_arabic(value)
        elif isinstance(value, list):
            return [cls.process_value(item) for item in value]
        elif isinstance(value, dict):
            return {k: cls.process_value(v) for k, v in value.items()}
        return value
    
    @classmethod
    def process_data_dict(cls, data: dict) -> dict:
        return cls.process_value(data)


# =========================
# LOAD TEMPLATE
# =========================
def load_template(name: str):
    path = os.path.join(TEMPLATE_DIR, name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Template not found: {name}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# =========================
# CSS (FINAL FIX)
# =========================
def build_css():
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

        body {{
            font-family: 'Amiri', 'Arial', sans-serif;
            direction: rtl;
            text-align: right;
            font-size: 14pt;
            line-height: 1.8;
            color: #000;
            font-feature-settings: "liga" 0, "calt" 0, "ccmp" 0, "dlig" 0;
            text-rendering: geometricPrecision;
        }}

        * {{
            font-family: 'Amiri', 'Arial', sans-serif !important;
        }}

        p, div, span, td, th, li {{
            direction: rtl;
        }}

        .ltr {{
            direction: ltr;
            text-align: left;
        }}
        
        table {{
            direction: rtl;
            border-collapse: collapse;
        }}
        
        th, td {{
            padding: 8px;
            # border: 1px solid #333;
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
    """)


# =========================
# PDF GENERATOR
# =========================
def generate_pdf(html_content: str) -> bytes:
    css = build_css()
    html = HTML(
        string=html_content,
        base_url="file:///" + BASE_DIR.replace("\\", "/") + "/"
    )
    return html.write_pdf(
        stylesheets=[css],
        font_config=font_config
    )


# =========================
# API
# =========================
@app.get("/")
def home():
    return {
        "success": True,
        "message": "Arabic PDF Engine (Amiri Edition) Running",
        "features": [
            "Arabic text reshaping with arabic-reshaper",
            "Bidirectional text support with python-bidi",
            "Amiri font optimized for Arabic typography",
            "Improved text extraction from PDF",
            "Fixed tatweel issue in text layer"
        ]
    }


@app.post("/generate-pdf")
async def generate_pdf_api(req: GeneratePdfRequest):
    html = req.template_content
    if not html:
        if not req.template_name:
            return {
                "success": False,
                "message": "Template required (template_name or template_content)"
            }
        html = load_template(req.template_name)

    processed_data = ArabicTextProcessor.process_data_dict(req.data)

    env = Environment(
        undefined=PlaceholderUndefined,
        autoescape=False
    )
    template = env.from_string(html)
    rendered_html = template.render(processed_data)

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
    fonts_status = {
        "Amiri-Regular.ttf": os.path.exists(AMIRI_REGULAR),
        "Amiri-Bold.ttf": os.path.exists(AMIRI_BOLD),
        "Amiri-Italic.ttf": os.path.exists(AMIRI_ITALIC),
        "Amiri-BoldItalic.ttf": os.path.exists(AMIRI_BOLDITALIC),
    }
    all_ready = all(fonts_status.values())
    return {
        "status": "ready" if all_ready else "missing_fonts",
        "fonts": fonts_status,
        "message": "All fonts ready" if all_ready else "Please download Amiri fonts to fonts/ directory"
    }


# =========================
# RUN
# =========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )