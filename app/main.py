import os
import uuid
import asyncio
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from . import ocr, template_manager, mapper

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="OCR Template Mapping API")

# Allow all origins for simplicity. Restrict in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Very small HTML page to test PDF uploads from a browser."""
    html_content = """
    <!doctype html>
    <html>
    <head>
        <meta charset=\"utf-8\" />
        <title>PDF Upload</title>
    </head>
    <body>
        <h1>Upload PDF</h1>
        <input type=\"file\" id=\"file\" accept=\"application/pdf\" />
        <button onclick=\"upload()\">Upload</button>
        <pre id=\"result\"></pre>
        <script>
            async function upload() {
                const fileInput = document.getElementById('file');
                if (!fileInput.files.length) {
                    alert('Select a PDF first.');
                    return;
                }
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                const res = await fetch('/upload', { method: 'POST', body: formData });
                const json = await res.json();
                document.getElementById('result').textContent = JSON.stringify(json, null, 2);
            }
        </script>
    </body>
    </html>
    """
    return html_content


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Endpoint that receives a PDF, runs OCR, selects/fills template, and returns JSON."""
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    pdf_id = str(uuid.uuid4())
    pdf_path = os.path.join(UPLOAD_DIR, f"{pdf_id}.pdf")

    # Save the uploaded PDF
    with open(pdf_path, "wb") as out_file:
        out_file.write(await file.read())

    # 1. OCR (run in thread to avoid blocking event loop)
    ocr_json = await asyncio.to_thread(ocr.process_pdf, pdf_path)

    # 2. Template selection / generation (may call OpenAI)
    template = await template_manager.select_or_generate_template(ocr_json)

    # 3. Populate template with OCR-extracted values
    filled = mapper.populate_template(template, ocr_json)

    return JSONResponse(content=filled) 