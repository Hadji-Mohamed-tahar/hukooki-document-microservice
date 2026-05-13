from fastapi import FastAPI, Response
from pydantic import BaseModel
from jinja2 import Environment, Undefined

from weasyprint import HTML

import uuid
import os

# =========================
# APP
# =========================
app = FastAPI(title="Arabic PDF Engine")

BASE_DIR = os.path.abspath(".")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
FONT_DIR = os.path.join(BASE_DIR, "fonts")

os.makedirs(TEMPLATE_DIR, exist_ok=True)
os.makedirs(FONT_DIR, exist_ok=True)


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
# LOAD TEMPLATE
# =========================
def load_template(name: str):
    path = os.path.join(TEMPLATE_DIR, name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Template not found: {name}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# =========================
# PDF GENERATOR - TEMPLATE ONLY
# =========================
def generate_pdf(html_content: str) -> bytes:
    """
    Generate PDF using ONLY template CSS.
    No external CSS injection to avoid conflicts.
    """
    html = HTML(
        string=html_content,
        base_url="file:///" + BASE_DIR.replace("\\", "/") + "/"
    )
    # No stylesheets parameter - template handles all CSS
    return html.write_pdf()


# =========================
# API
# =========================
@app.get("/")
def home():
    return {
        "success": True,
        "message": "Arabic PDF Engine Running",
        "note": "Template must include all CSS including @font-face and @page"
    }


@app.post("/generate-pdf")
async def generate_pdf_api(req: GeneratePdfRequest):
    html = req.template_content
    if not html:
        if not req.template_name:
            return {"success": False, "message": "Template required"}
        html = load_template(req.template_name)

    env = Environment(undefined=PlaceholderUndefined, autoescape=False)
    template = env.from_string(html)
    rendered_html = template.render(req.data)

    pdf = generate_pdf(rendered_html)

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=doc_{uuid.uuid4().hex[:8]}.pdf"}
    )


@app.get("/health")
def health_check():
    return {"status": "ready"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)