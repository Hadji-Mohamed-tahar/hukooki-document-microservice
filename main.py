import os
import sys
import uuid
from typing import Dict, Any, Optional

# --- 1. إعداد مسارات النظام (حل مشكلة Windows DLLs) ---
# التأكد من استخدام مسار UCRT64 الذي ثبتّه عبر MSYS2
gtk_path = r'C:\msys64\ucrt64\bin' 

if os.path.exists(gtk_path):
    # إضافة المسار لبيئة العمل لضمان رؤية ملفات الـ DLL
    os.add_dll_directory(gtk_path)
    os.environ['PATH'] = gtk_path + os.pathsep + os.environ.get('PATH', '')
else:
    print(f"Warning: GTK path not found at {gtk_path}. PDF generation might fail.")

# --- 2. الاستيرادات الأساسية ---
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from pydantic import BaseModel
from weasyprint import HTML, CSS
from jinja2 import Template

app = FastAPI()

# إعداد مجلد القوالب
TEMPLATE_DIR = "./templates"
if not os.path.exists(TEMPLATE_DIR):
    os.makedirs(TEMPLATE_DIR)

# --- 3. نماذج البيانات ---
class GeneratePdfRequest(BaseModel):
    template_name: Optional[str] = None
    data: Dict[str, Any]
    template_content: Optional[str] = None

# --- 4. المسارات (Routes) ---

@app.get("/")
def home():
    return {"status": "Service is running", "engine": "WeasyPrint with Arabic Support"}

@app.post("/upload-template")
async def upload_template(file: UploadFile = File(...)):
    if not file.filename.endswith((".html", ".htm")):
        raise HTTPException(status_code=400, detail="Only HTML files are allowed.")

    file_id = f"{uuid.uuid4()}.html"
    file_path = os.path.join(TEMPLATE_DIR, file_id)
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    return {"message": "Template uploaded successfully", "template_name": file_id}

@app.post("/generate-pdf")
async def generate_pdf(request: GeneratePdfRequest):
    # جلب محتوى القالب
    html_content = request.template_content
    
    if not html_content:
        if not request.template_name:
            raise HTTPException(status_code=400, detail="Provide template_name or template_content.")
        
        template_path = os.path.join(TEMPLATE_DIR, request.template_name)
        if not os.path.exists(template_path):
            raise HTTPException(status_code=404, detail="Template file not found on server.")
        
        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()

    try:
        # استخدام Jinja2 لدمج البيانات باحترافية
        jinja_template = Template(html_content)
        rendered_html = jinja_template.render(request.data)

        # إعدادات CSS لدعم اللغة العربية (RTL) وتنسيق الصفحة
        arabic_css = CSS(string='''
            @page { 
                size: A4; 
                margin: 1.5cm; 
            }
            * { 
                direction: rtl; 
                font-family: 'Amiri', 'Arial', sans-serif; 
            }
            body { 
                font-size: 14px; 
                line-height: 1.8;
                color: #333;
            }
        ''')

        # توليد الـ PDF من النص المنسق
        pdf_binary = HTML(string=rendered_html).write_pdf(stylesheets=[arabic_css])

        # إرسال الملف كاستجابة فورية (Download)
        return Response(
            content=pdf_binary,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=contract_{uuid.uuid4().hex[:8]}.pdf"
            }
        )
    except Exception as e:
        # في حالة فشل التوليد، سنعرف السبب من الرسالة
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

# --- 5. تشغيل السيرفر ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)