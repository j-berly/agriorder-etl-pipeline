from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from PIL import Image
from ocr_functions import ocr_paddle_func, ocr_tesseract_func, ocr_easyocr_func, pdf_to_images
from error_corrector import pycorrect_spell_correct, ollama_spell_correct
import io


app = FastAPI()


def image_bytes_to_pil(img_bytes: bytes) -> Image.Image:
    """
    PNG/JPG等bytes转为PIL.Image对象
    """
    return Image.open(io.BytesIO(img_bytes))


@app.post("/ocr_fileparse")
async def ocr_fileparse(file: UploadFile = File(...), tool: str = 'PaddleOCR'):
    """
    自动根据上传文件类型，针对图片类文件/ PDF 自动多页，PaddleOCR。
    返回各引擎结果和图片保存路径(供人肉对比)。
    """
    try:
        contents = await file.read()
        text = ''
        if file.content_type == 'application/pdf':
            # 处理PDF多页
            filetype = 'pdf'
            images = pdf_to_images(contents)
            for idx, img in enumerate(images):
                if tool == 'PaddleOCR':
                    text += ocr_paddle_func(img)
                elif tool == 'Tesseract':
                    text += ocr_tesseract_func(img)
                elif tool == 'EasyOCR':
                    text += ocr_easyocr_func(img)
                else:
                    continue

        elif file.content_type in {'image/png', 'image/jpeg', 'image/jpg'}:
            # 处理单张图片
            filetype = 'image'
            img = image_bytes_to_pil(contents)
            if tool == 'PaddleOCR':
                text = ocr_paddle_func(img)
            elif tool == 'Tesseract':
                text = ocr_tesseract_func(img)
            elif tool == 'EasyOCR':
                text = ocr_easyocr_func(img)
            else:
                return

        else:
            return JSONResponse({"status": "unsupported", "msg": "不支持的文件类型"})

        return JSONResponse({
            "status": "success",
            "filetype": filetype,
            "file_name": file.filename,
            "text": text
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "fail", "msg": str(e)})


@app.post("/correct_text")
async def correct_text_api(data: dict):
    """输入 {'text': '需要纠错内容'}，返回纠错结果"""
    return pycorrect_spell_correct(data.get("text", ""))


# 集成流程用法1: n8n分别调两个服务（http节点）
# 集成流程用法2: 写个全自动服务
@app.post("/ocr_and_llmcorrect")
async def ocr_and_llmcorrect(file: UploadFile = File(...)):
    contents = await file.read()
    text = ''
    if file.content_type == 'application/pdf':
        images = pdf_to_images(contents)
        for idx, img in enumerate(images):
            text += ocr_paddle_func(img)
    else:
        img = image_bytes_to_pil(contents)
        text = ocr_paddle_func(img)

    correct0 = ollama_spell_correct(text)
    print(correct0)


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='localhost', port=8000)
