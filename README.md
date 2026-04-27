# 🚀 تشغيل محرك PDF - مشروع هوقوقي (Hokoki)

هذا الدليل المختصر لتشغيل خدمة توليد ملفات PDF باللغة العربية.

---

### 1️⃣ المتطلبات الأساسية (مرة واحدة فقط)
يجب أن يكون برنامج **MSYS2** مثبتاً في المسار الافتراضي:
`C:\msys64\ucrt64\bin`

---

### 2️⃣ التثبيت الأول (إذا كانت أول مرة تشغيل)
افتح الـ PowerShell في مجلد `python-service` ونفذ:
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install fastapi uvicorn weasyprint jinja2 python-multipart pydantic


3️⃣ أمر التشغيل السريع (كل مرة)
انسخ هذا السطر الموحد والصقه في الـ PowerShell وسيعمل كل شيء فوراً:

PowerShell
.\venv\Scripts\activate; $env:PATH = "C:\msys64\ucrt64\bin;" + $env:PATH; uvicorn main:app --reload --port 8001


🔍 كيف أتأكد أن الخدمة تعمل؟
افتح الرابط التالي في متصفحك:
👉 http://127.0.0.1:8001/

إذا ظهرت لك رسالة "محرك توليد الوثائق يعمل بنجاح"، فأنت جاهز!