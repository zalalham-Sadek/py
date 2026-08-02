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


class PDFInquiryRequest(BaseModel):
    url: str
    cookies: dict
    searching_type: str
    application_number: str
    passport_number: str
    captcha_text: str

@app.post("/generate-pdf")
async def generate_pdf(data: PDFInquiryRequest):
    try:
        async with async_playwright() as p:
            # 1. تشغيل المتصفح الخفي
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            
            # 2. حقن كوكيز الجلسة الناجحة التي أنشأها لارافيل لربط الكابتشا
            await context.add_cookies([
                {"name": k, "value": v, "domain": "the-external-website.com", "path": "/"} # استبدل بالدومين الحقيقي
                for k, v in data.cookies.items()
            ])
            
            page = await context.new_page()
            
            # 3. الانتقال لصفحة الفورم الرئيسية
            await page.goto(data.url, wait_until="networkidle")
            
            # 4. محاكاة تعبئة الحقول عبر متصفح بايثون الحقيقي
            await page.locator("#SearchingType").select_option(data.searching_type) # حقل الاختيار
            await page.locator("#ApplicationNumber").fill(data.application_number) # رقم الطلب
            await page.locator("#PassportNumber").fill(data.passport_number)       # رقم الجواز
            await page.locator("#Captcha").fill(data.captcha_text)                 # نص الكابتشا الناجح
            
            # 5. النقر على زر التأكيد والانتظار حتى انتهاء طلب الـ Ajax وتحميل النتيجة
            # (استبدل #submit-btn بالـ ID الحقيقي لزر التأكيد في الموقع الخارجي)
            await page.locator("#submit-btn").click() 
            
            # الانتظار حتى تنتهي شبكة الموقع من حقن بيانات النتيجة وتستقر التنسيقات
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000) # تأخير إضافي ثابث لمدة ثانيتين للأمان
            
            # 6. تنظيف الصفحة وحذف الهيدر والفوتر قبل إصدار الـ PDF
            await page.evaluate("document.querySelector('header')?.remove();")
            await page.evaluate("document.querySelector('footer')?.remove();")
            await page.evaluate("document.querySelector('.footer')?.remove();")
            
            # 7. طباعة المستند النهائي بدقة رسمية عالية وحفظ الألوان
            pdf_bytes = await page.pdf(format="A4", print_background=True, margin={"top": "0.1in", "bottom": "0.1in"})
            await browser.close()
            
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
            return {"status": "success", "pdf_content": pdf_base64}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}
