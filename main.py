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


# تأكد من إضافة هذا النموذج لاستلام النص
class HTMLPDFRequest(BaseModel):
    html_content: str

@app.post("/generate-pdf")
async def generate_pdf(data: HTMLPDFRequest):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # 🌟 حقن كود الـ HTML للنتيجة مباشرة داخل المتصفح الخفي دون الحاجة لزيارة الموقع
            await page.set_content(data.html_content, wait_until="networkidle")
            
            # (اختياري) حذف الهيدر والفوتر إن رغبت من النتيجة
            await page.evaluate("document.querySelector('header')?.remove();")
            await page.evaluate("document.querySelector('footer')?.remove();")
            
            # حفظ المستند الحقيقي كـ PDF بالتنسيق والألوان الرسمية
            pdf_bytes = await page.pdf(format="A4", print_background=True, margin={"top": "0.1in", "bottom": "0.1in"})
            await browser.close()
            
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
            return {"status": "success", "pdf_content": pdf_base64}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}
