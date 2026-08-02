from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.async_api import async_playwright
import ddddocr
import base64

app =FastAPI()

ocr = ddddocr.DdddOcr(show_ad=False)

class CaptchaRequest(BaseModel):
    image_base64: str

@app.post("/solve")
async def solve_captcha(data: CaptchaRequest):
    try:
        img_bytes = base64.b64decode(data.image_base64)

        captcha_text = ocr.classification(img_bytes)

        return {"status":"success","captch_text":captcha_text}
    
    except Exception as e:
        raise HTTPException(status_code=400,detail=str(e))



class PDFRequest(BaseModel):
    url: str
    cookies: dict

@app.post("/generate-pdf")
async def generate_pdf(data: PDFRequest):
    try:
        async with async_playwright() as p:
            # 1. تشغيل متصفح خفي ذكي
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            
            # 2. حقن الكوكيز الخاصة بلارافيل لكي يفتح الصفحة كأنه نفس المستخدم
            await context.add_cookies([
                {"name": k, "value": v, "domain": "the-external-website.com", "path": "/"}
                for k, v in data.cookies.items()
            ])
            
            page = await context.new_page()
            
            # 3. الانتقال لصفحة النتيجة والانتظار حتى تحميل كافة التنسيقات والخطوط تماماً
            await page.goto(data.url, wait_until="networkidle")
            
            # 💡 (اختياري) يمكنك حذف الهيدر والفوتر مباشرة من هنا قبل التوليد بمتصفح بايثون
            await page.evaluate("document.querySelector('header')?.remove();")
            await page.evaluate("document.querySelector('footer')?.remove();")
            
            # 4. حفظ الصفحة كـ PDF رسمي بالتنسيق والألوان الأصلية
            pdf_bytes =  await page.pdf(format="A4", print_background=True, margin={"top": "0.2in", "bottom": "0.2in"})
            await browser.close()
            
            # 5. تشفير الملف وإرساله للارافيل
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
            return {"status": "success", "pdf_content": pdf_base64}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}
