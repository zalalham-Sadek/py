from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.async_api import async_playwright
import ddddocr
import base64
import asyncio

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



class DirectPDFRequest(BaseModel):
    url: str
    searching_type: str
    application_number: str
    passport_number: str

@app.post("/process-and-capture")
async def process_and_capture(data: DirectPDFRequest):
    async with async_playwright() as p:
        # 1. تشغيل المتصفح الخفي
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        max_attempts = 3
        pdf_base64 = None
        error_message = "فشل غير معروف"

        for attempt in range(1, max_attempts + 1):
            try:
                # الانتقال لصفحة الفورم الرئيسية للموقع الخارجي
                await page.goto(data.url, wait_until="networkidle")
                
                # 2. التقاط صورة الكابتشا المشوهة من الصفحة مباشرة
                captcha_element = page.locator("#CaptchaImage, img[src*='Captcha']") # تأكد من الـ ID أو الكلاس الحقيقي للصورة
                captcha_bytes = await captcha_element.screenshot()
                
                # 3. حل الكابتشا بواسطة الذكاء الاصطناعي محلياً
                captcha_text = ocr.classification(captcha_bytes)
                
                # 4. تعبئة الحقول كاملة داخل المتصفح
                await page.locator("#SearchingType").select_option(data.searching_type)
                await page.locator("#ApplicationNumber").fill(data.application_number)
                await page.locator("#PassportNumber").fill(data.passport_number)
                await page.locator("#Captcha").fill(captcha_text)
                
                # 5. الضغط على زر التأكيد
                await page.locator("#_Form button[type='submit'], #_Form input[type='submit']").first.click()
                
                # 6. الانتظار الذكي: نفحص هل ظهر عنصر النتيجة أم عدنا لصفحة الفورم بسبب خطأ كابتشا؟
                # انتظر 5 ثوانٍ كحد أقصى لرؤية هل ظهر جدول النتيجة الناجحة
                try:
                    # استبدل .result-box بكلاس أو ID حقيقي يظهر فقط في صفحة النتيجة الناجحة
                    await page.wait_for_selector(".result-box, table, #printArea", timeout=5000)
                    
                    # إذا وصلنا هنا، فهذا يعني نجاح تخطي الكابتشا وظهور النتيجة الحقيقية!
                    # تنظيف الصفحة من الهيدر والفوتر قبل إصدار الـ PDF
                    await page.evaluate("document.querySelector('header')?.remove();")
                    await page.evaluate("document.querySelector('footer')?.remove();")
                    
                    # طباعة المستند كـ PDF بالتنسيق والألوان الأصلية
                    pdf_bytes = await page.pdf(format="A4", print_background=True, margin={"top": "0.1in", "bottom": "0.1in"})
                    pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
                    break # الخروج من حلقة المحاولات بنجاح
                    
                except Exception:
                    # إذا انتهت الـ 5 ثوان ولم يظهر عنصر النتيجة، فغالباً الكابتشا خاطئة والموقع أعادنا لنفس الصفحة
                    error_message = "أخطأ الذكاء الاصطناعي في الكابتشا، جاري إعادة المحاولة تلقائياً..."
                    continue # إعادة الدورة وتوليد كابتشا جديدة في المحاولة التالية
                    
            except Exception as e:
                error_message = str(e)
                continue

        await browser.close()
        
        if pdf_base64:
            return {"status": "success", "pdf_content": pdf_base64}
        else:
            return {"status": "error", "message": f"فشل بعد {max_attempts} محاولات. السبب: {error_message}"}
