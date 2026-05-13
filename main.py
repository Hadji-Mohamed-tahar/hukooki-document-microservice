import os
import sys
import uuid
from typing import Dict, Any, Optional

# =========================
# 1. Windows DLL Fix
# =========================
gtk_path = r'C:\msys64\ucrt64\bin'

if os.path.exists(gtk_path):
    os.environ['PATH'] = gtk_path + os.pathsep + os.environ.get('PATH', '')
    if hasattr(os, 'add_dll_directory'):
        try:
            os.add_dll_directory(gtk_path)
        except Exception as e:
            print(f"⚠️ DLL Warning: {e}")
    sys.path.append(gtk_path)

# =========================
# 2. Imports
# =========================
try:
    from fastapi import FastAPI, UploadFile, File, Response
    from pydantic import BaseModel
    from weasyprint import HTML, CSS
    from jinja2 import Environment, Undefined
    from fastapi.responses import JSONResponse
except ImportError as e:
    print(f"Missing dependencies: {e}")
    sys.exit(1)

# =========================
# 3. Safe Undefined (placeholders)
# =========================
class PlaceholderUndefined(Undefined):
    def __str__(self):
        return "...................."

    def __getattr__(self, name):
        return self

# =========================
# 4. App
# =========================
app = FastAPI(title="Hokoki PDF Engine")

TEMPLATE_DIR = "./templates"
os.makedirs(TEMPLATE_DIR, exist_ok=True)

# =========================
# 5. Request Model
# =========================
class GeneratePdfRequest(BaseModel):
    template_name: Optional[str] = None
    data: Dict[str, Any]
    template_content: Optional[str] = None

# =========================
# 6. Helpers
# =========================
def unified_response(success: bool, message: str, data: Any = None, status_code: int = 200):
    return JSONResponse(
        status_code=status_code,
        content={
            "success": success,
            "message": message,
            "data": data
        }
    )

# =========================
# 7. RTL FIX (IMPORTANT)
# =========================
def fix_arabic_data(data: dict):
    """
    يمنع مشاكل copy/paste في PDF العربي
    بإضافة RTL Mark
    """
    rtl_mark = "\u200F"  # Right-to-left mark

    fixed = {}
    for k, v in data.items():
        if isinstance(v, str):
            fixed[k] = rtl_mark + v
        else:
            fixed[k] = v

    return fixed

# =========================
# 8. CSS (FINAL FIX)
# =========================
ARABIC_CSS = CSS(string="""
    @page {
        size: A4;
        margin: 2cm;
    }

    body {
        font-family: 'Amiri', 'Cairo', Arial, sans-serif;
        font-size: 14px;
        line-height: 1.6;
        color: #000;

        direction: rtl;
        unicode-bidi: plaintext;
        text-align: right;
    }

    .a4-page {
        direction: rtl;
        unicode-bidi: plaintext;
        text-align: right;
    }

    p, span, div {
        unicode-bidi: plaintext;
    }

    .text-center {
        text-align: center;
    }

    .text-right {
        text-align: right;
    }
""")

# =========================
# 9. Routes
# =========================
@app.get("/")
def home():
    return unified_response(
        True,
        "PDF Engine Running",
        {"engine": "WeasyPrint Arabic", "status": "online"}
    )

@app.post("/generate-pdf")
async def generate_pdf(request: GeneratePdfRequest):
    try:
        # =========================
        # Load template
        # =========================
        html_content = request.template_content

        if not html_content:
            if not request.template_name:
                return unified_response(False, "Template required", None, 400)

            template_path = os.path.join(TEMPLATE_DIR, request.template_name)

            if not os.path.exists(template_path):
                return unified_response(False, "Template not found", None, 404)

            with open(template_path, "r", encoding="utf-8") as f:
                html_content = f.read()

        # =========================
        # Jinja setup
        # =========================
        env = Environment(undefined=PlaceholderUndefined)
        template = env.from_string(html_content)

        safe_data = fix_arabic_data(request.data)

        rendered_html = template.render(safe_data)

        # =========================
        # PDF generation
        # =========================
        pdf = HTML(string=rendered_html).write_pdf(
            stylesheets=[ARABIC_CSS]
        )

        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=hokoki_{uuid.uuid4().hex[:8]}.pdf"
            }
        )

    except Exception as e:
        return unified_response(False, f"PDF Error: {str(e)}", None, 500)

# =========================
# 10. Upload template
# =========================
@app.post("/upload-template")
async def upload_template(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".html", ".htm")):
        return unified_response(False, "HTML only", None, 400)

    file_id = f"{uuid.uuid4()}.html"
    path = os.path.join(TEMPLATE_DIR, file_id)

    content = await file.read()

    with open(path, "wb") as f:
        f.write(content)

    return unified_response(True, "Uploaded", {"template_name": file_id})

# =========================
# 11. Run server
# =========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)