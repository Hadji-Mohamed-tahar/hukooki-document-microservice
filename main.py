import os
import sys
import uuid
from typing import Dict, Any, Optional

# --- 1. حل مشكلة Windows DLLs (إصدار نهائي لضمان النجاح الدائم) ---
# يجب أن يظل هذا الجزء في أعلى الملف تماماً قبل أي استيراد للمكتبات الخارجية
gtk_path = r'C:\msys64\ucrt64\bin'

if os.path.exists(gtk_path):
    # إضافة المسار لمتغيرات البيئة للنظام
    os.environ['PATH'] = gtk_path + os.pathsep + os.environ.get('PATH', '')
    
    # إجبار بايثون الحديث (3.8 إلى 3.13) على الوثوق في هذا المجلد لتحميل ملفات الـ DLL
    if hasattr(os, 'add_dll_directory'):
        try:
            os.add_dll_directory(gtk_path)
        except Exception as e:
            print(f"⚠️ Warning: Could not add DLL directory: {e}")
    
    # إضافة المسار لمسارات البحث الخاصة ببايثون نفسه
    sys.path.append(gtk_path)

# الآن نقوم باستيراد المكتبات بعد تهيئة البيئة بنجاح
try:
    from fastapi import FastAPI, UploadFile, File, HTTPException, Response
    from pydantic import BaseModel
    from weasyprint import HTML, CSS
    from jinja2 import Template
    from fastapi.responses import JSONResponse
except ImportError as e:
    print(f"❌ Error: Missing libraries. Run 'pip install' first. Details: {e}")
    sys.exit(1)

app = FastAPI(title="Hokoki PDF Engine")

# إعداد مجلد القوالب
TEMPLATE_DIR = "./templates"
if not os.path.exists(TEMPLATE_DIR):
    os.makedirs(TEMPLATE_DIR)

# --- 2. نماذج البيانات (Models) ---
class GeneratePdfRequest(BaseModel):
    template_name: Optional[str] = None
    data: Dict[str, Any]
    template_content: Optional[str] = None

# --- 3. الدوال المساعدة (Helper Functions) ---
def unified_response(success: bool, message: str, data: Any = None, status_code: int = 200):
    """دالة لتوحيد شكل الرد مع سيرفر لارفيل"""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": success,
            "message": message,
            "data": data
        }
    )

# --- 4. المسارات (Routes) ---

@app.get("/")
def home():
    return unified_response(True, "محرك توليد الوثائق يعمل بنجاح", {"engine": "WeasyPrint Arabic", "status": "online"})

@app.post("/upload-template")
async def upload_template(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".html", ".htm")):
        return unified_response(False, "فقط ملفات HTML مسموح بها", None, 400)

    file_id = f"{uuid.uuid4()}.html"
    file_path = os.path.join(TEMPLATE_DIR, file_id)
    
    content = await file.read()
    with open(file_path, "wb") as buffer:
        buffer.write(content)
        
    return unified_response(True, "تم رفع القالب بنجاح", {"template_name": file_id})

@app.post("/generate-pdf")
async def generate_pdf(request: GeneratePdfRequest):
    html_content = request.template_content
    
    # التحقق من مصدر محتوى الـ HTML
    if not html_content:
        if not request.template_name:
            return unified_response(False, "يجب توفير اسم القالب أو المحتوى", None, 400)
        
        template_path = os.path.join(TEMPLATE_DIR, request.template_name)
        if not os.path.exists(template_path):
            return unified_response(False, "ملف القالب غير موجود في السيرفر", None, 404)
        
        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()

    try:
        # استخدام Jinja2 لدمج البيانات في القالب
        jinja_template = Template(html_content)
        rendered_html = jinja_template.render(request.data)

        # إعدادات CSS لدعم العربية والخطوط (Amiri هو المفضل لهقوقي)
        arabic_css = CSS(string='''
            @page { size: A4; margin: 2cm; }
            * { direction: rtl; font-family: 'Amiri', 'Arial', sans-serif; }
            body { font-size: 14px; line-height: 1.6; color: #000; }
            .text-center { text-align: center; }
            .text-right { text-align: right; }
        ''')

        # توليد الـ PDF من محتوى الـ HTML المعدل
        pdf_binary = HTML(string=rendered_html).write_pdf(stylesheets=[arabic_css])

        # إعادة الملف فوراً كاستجابة (Binary Response)
        return Response(
            content=pdf_binary,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=hokoki_{uuid.uuid4().hex[:8]}.pdf"
            }
        )
    except Exception as e:
        return unified_response(False, f"فشل توليد الملف: {str(e)}", None, 500)

# --- 5. تشغيل السيرفر ---
if __name__ == "__main__":
    import uvicorn
    # التشغيل على 8001 لتجنب التعارض مع Laravel (8000)
    uvicorn.run(app, host="0.0.0.0", port=8001)