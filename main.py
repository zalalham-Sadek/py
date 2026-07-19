from fastapi import FastAPI, HTTPEception
from pydantic import BaseModel
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
        raise HTTPEception(status_code=400,detail=str(e))
