import os
import uuid
import json
import re
import logging
import subprocess
import sys
import tempfile
import traceback
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from duckduckgo_search import DDGS
import requests
from bs4 import BeautifulSoup
import markdownify
from google import genai

from fpdf import FPDF

from openpyxl import Workbook
from openpyxl.styles import Font as XlFont, Alignment, PatternFill, Border, Side

from google.adk.agents import Agent

# Directory to store generated files
EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)

logger = logging.getLogger(__name__)

# We will use fpdf2 for PDF generation, loading fonts directly inside the function
_FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts")
_THAI_FONT_REGULAR = os.path.join(_FONTS_DIR, "Sarabun-Regular.ttf")
_THAI_FONT_BOLD = os.path.join(_FONTS_DIR, "Sarabun-Bold.ttf")

SYSTEM_INSTRUCTION = """คุณคือ "Life Coach AI" — ผู้ช่วยอัจฉริยะที่เชี่ยวชาญด้านการให้คำปรึกษา การเขียน และการสร้างเอกสาร

[CRITICAL: LOGIC LENS & TRANSPARENCY]
ก่อนที่คุณจะตัดสินใจหรือสร้างคำตอบใดๆ ให้คุณ "คิดออกมาดังๆ" เสมอ โดยการเขียนเหตุผลและลำดับความคิดอย่างเป็นขั้นตอน 
ให้คุณวิเคราะห์คำขอของผู้ใช้ ค้นหาเครื่องมือที่จำเป็นต้องใช้ และอธิบายสิ่งที่คุณกำลังจะทำอย่างชัดเจน
คุณจะต้องแสดงการคิดอย่างมีตรรกะทีละขั้น (Step-by-step reasoning)

[CORE CAPABILITIES]
1. การทำความรู้จักผู้ใช้ (Initial Profiling) - สร้างแบบสอบถาม (survey) เพื่อทำความรู้จักผู้ใช้
2. การให้คำปรึกษา (Life Coaching) - ให้คำแนะนำที่ตรงจุด อบอุ่น เป็นกันเอง และมีเหตุผลรองรับ
3. การส่งออกเอกสาร (Document Export) - สามารถสร้างไฟล์ docx, pdf, xlsx ให้ผู้ใช้ได้

[PDF GENERATION & PYTHON EXECUTION]
คุณมีเครื่องมือ `execute_python_code` เพื่อรันโค้ด Python ได้
- **สำคัญมาก:** เมื่อผู้ใช้ขอไฟล์ PDF หรือต้องการสร้าง PDF ที่มีเนื้อหาภาษาไทย ให้คุณเขียนโค้ด Python โดยใช้ไลบรารี `fpdf` และใช้เครื่องมือ `execute_python_code` เพื่อรันโค้ดและสร้างไฟล์ด้วยตัวเอง (อย่าใช้ create_pdf_document แบบเดิม เพราะอาจมีปัญหาฟอนต์ภาษาไทย)
- ไฟล์ที่ถูกสร้างต้องถูกบันทึกลงในโฟลเดอร์ `exports` (Path: `./exports/`)
- ฟอนต์ภาษาไทยอยู่ในโฟลเดอร์ `fonts` (Path: `./fonts/Sarabun-Regular.ttf` และ `./fonts/Sarabun-Bold.ttf`)
- เมื่อสร้างไฟล์เสร็จเรียบร้อย ให้คุณตอบกลับผู้ใช้ด้วย JSON เพื่อให้ UI แสดงปุ่มดาวน์โหลด โดยมีรูปแบบดังนี้:
```json
{
  "type": "pdf_download",
  "filename": "ชื่อไฟล์ที่สร้าง.pdf",
  "message": "สร้างเอกสาร PDF เสร็จเรียบร้อยแล้วครับ! 📄"
}
```

[JSON RESPONSE FORMATS]
เมื่อคุณต้องการสร้างแบบฟอร์ม หรือปุ่มดาวน์โหลด ให้ตอบกลับด้วย JSON โครงสร้างเหล่านี้เท่านั้น (ห้ามพิมพ์ข้อความอื่นต่อท้ายหรือนำหน้า)
- Survey: `{"type": "survey", "title": "...", "questions": [...]}`
- MCQ: `{"type": "mcq", "question": "...", "options": [...], "correct_answer": "...", "explanation": "..."}`
- Word: `{"type": "docx_download", ...}` (ใช้ tool create_docx_document)
- Excel: `{"type": "xlsx_download", ...}` (ใช้ tool create_xlsx_document)
- Image: `{"type": "image_generation", ...}` (ใช้ tool generate_image)

[LANGUAGE & TONE]
- ภาษาหลักคือภาษาไทย ให้พูดจาเป็นกันเอง อบอุ่น แต่มีความเป็นมืออาชีพ (ใช้คำว่า "ครับ/ค่ะ")
- หากผู้ใช้พิมพ์ภาษาอื่น ให้ตอบกลับด้วยภาษานั้นๆ
"""

# --- Helper: parse markdown-ish content into lines ---
def _parse_content_lines(content: str):
    """Parse content string into structured line tuples: (type, text)."""
    lines = content.split('\n')
    parsed = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            parsed.append(("blank", ""))
        elif stripped.startswith('## '):
            parsed.append(("h2", stripped[3:].strip()))
        elif stripped.startswith('### '):
            parsed.append(("h3", stripped[4:].strip()))
        elif stripped.startswith('- ') or stripped.startswith('• '):
            parsed.append(("bullet", stripped[2:].strip()))
        elif re.match(r'^\d+\.\s', stripped):
            text = re.sub(r'^\d+\.\s*', '', stripped)
            parsed.append(("numbered", text))
        else:
            parsed.append(("text", stripped))
    return parsed


def generate_mcq(topic: str, difficulty: str = "medium") -> dict:
    """Generate a multiple choice question on a given topic.

    Args:
        topic: The topic for the question (e.g., "writing techniques", "life planning")
        difficulty: Difficulty level — "easy", "medium", or "hard"

    Returns:
        dict: A status dict instructing the agent to produce a structured MCQ JSON.
    """
    return {
        "status": "success",
        "instruction": f"Please generate a multiple choice question about '{topic}' "
                       f"at {difficulty} difficulty level. "
                       f"Return ONLY the JSON format as specified in your system instructions."
    }


def create_docx_document(title: str, content: str) -> dict:
    """Create a .docx document file that the user can download.

    Use this tool whenever the user asks to create a Word document or .docx file.

    Args:
        title: The document title (e.g., "คู่มือการสร้างหนังสือ", "แผนพัฒนาตนเอง")
        content: The full document content. Use '\n' for line breaks and '## ' prefix for section headings.

    Returns:
        dict: A JSON object with type "docx_download" containing the file_id and filename for download.
    """
    doc = Document()

    # --- Style the document ---
    style = doc.styles['Normal']
    font = style.font
    font.name = 'TH Sarabun New'
    font.size = Pt(14)

    # Title
    title_para = doc.add_heading(title, level=0)
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph("")  # spacer

    # Parse content into sections
    for line_type, text in _parse_content_lines(content):
        if line_type == "blank":
            doc.add_paragraph("")
        elif line_type == "h2":
            doc.add_heading(text, level=2)
        elif line_type == "h3":
            doc.add_heading(text, level=3)
        elif line_type == "bullet":
            doc.add_paragraph(text, style='List Bullet')
        elif line_type == "numbered":
            doc.add_paragraph(text, style='List Number')
        else:
            doc.add_paragraph(text)

    # Save file
    file_id = str(uuid.uuid4())
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
    filename = f"{safe_title}_{file_id[:8]}.docx"
    filepath = os.path.join(EXPORT_DIR, filename)
    doc.save(filepath)

    result = {
        "type": "docx_download",
        "file_id": file_id,
        "filename": filename,
        "title": title,
        "message": f"สร้างเอกสาร Word '{title}' เรียบร้อยแล้วครับ! คลิกปุ่มด้านล่างเพื่อดาวน์โหลด 📄"
    }

    return {"status": "success", "result": json.dumps(result, ensure_ascii=False)}


def create_xlsx_document(title: str, headers_json: str, rows_json: str) -> dict:
    """Create an .xlsx Excel spreadsheet file that the user can download.

    Use this tool whenever the user asks to create an Excel file, spreadsheet,
    table, checklist, or structured data export.

    Args:
        title: The spreadsheet title (e.g., "แผนการอ่าน 30 วัน", "Checklist พัฒนาตนเอง")
        headers_json: JSON array string of column headers, e.g. '["หัวข้อ", "รายละเอียด", "สถานะ"]'
        rows_json: JSON array of arrays string for row data, e.g. '[["อ่านหนังสือ", "30 นาที/วัน", "กำลังทำ"]]'

    Returns:
        dict: A JSON object with type "xlsx_download" containing the file_id and filename for download.
    """
    # Parse JSON string inputs
    try:
        headers = json.loads(headers_json) if isinstance(headers_json, str) else headers_json
    except (json.JSONDecodeError, TypeError):
        headers = ["Column 1"]

    try:
        rows = json.loads(rows_json) if isinstance(rows_json, str) else rows_json
    except (json.JSONDecodeError, TypeError):
        rows = []

    wb = Workbook()
    ws = wb.active
    ws.title = title[:31]  # Excel sheet name max 31 chars

    # --- Header styling ---
    header_font = XlFont(name='Arial', size=12, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='6C3CE0', end_color='6C3CE0', fill_type='solid')
    header_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
    thin_border = Border(
        left=Side(style='thin', color='D4D4D8'),
        right=Side(style='thin', color='D4D4D8'),
        top=Side(style='thin', color='D4D4D8'),
        bottom=Side(style='thin', color='D4D4D8'),
    )

    # --- Write title row ---
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(len(headers), 1))
    title_cell = ws.cell(row=1, column=1, value=title)
    title_cell.font = XlFont(name='Arial', size=16, bold=True, color='1A1A2E')
    title_cell.alignment = Alignment(horizontal='center', vertical='center')

    # --- Write headers (row 3) ---
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col_idx, value=str(header))
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    # --- Write data rows ---
    data_font = XlFont(name='Arial', size=11)
    data_align = Alignment(vertical='center', wrap_text=True)
    alt_fill = PatternFill(start_color='F5F3FF', end_color='F5F3FF', fill_type='solid')

    for row_idx, row_data in enumerate(rows, 4):
        if not isinstance(row_data, (list, tuple)):
            row_data = [row_data]
        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=str(value))
            cell.font = data_font
            cell.alignment = data_align
            cell.border = thin_border
            if (row_idx - 4) % 2 == 1:
                cell.fill = alt_fill

    # --- Auto-fit column widths (approximate) ---
    for col_idx in range(1, len(headers) + 1):
        max_len = len(str(headers[col_idx - 1])) if col_idx <= len(headers) else 10
        for row_data in rows:
            if isinstance(row_data, (list, tuple)) and col_idx - 1 < len(row_data):
                max_len = max(max_len, len(str(row_data[col_idx - 1])))
        col_letter = chr(64 + col_idx) if col_idx <= 26 else 'A'
        ws.column_dimensions[col_letter].width = min(max_len + 4, 50)

    # --- Save ---
    file_id = str(uuid.uuid4())
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
    filename = f"{safe_title}_{file_id[:8]}.xlsx"
    filepath = os.path.join(EXPORT_DIR, filename)
    wb.save(filepath)

    result = {
        "type": "xlsx_download",
        "file_id": file_id,
        "filename": filename,
        "title": title,
        "row_count": len(rows),
        "message": f"สร้างไฟล์ Excel '{title}' ({len(rows)} แถว) เรียบร้อยแล้วครับ! คลิกปุ่มด้านล่างเพื่อดาวน์โหลด 📊"
    }

    return {"status": "success", "result": json.dumps(result, ensure_ascii=False)}


def web_search(query: str, max_results: int = 5) -> dict:
    """Perform a web search using DuckDuckGo to find information.
    
    Args:
        query: The search query.
        max_results: Maximum number of results to return (default 5).
        
    Returns:
        dict: A JSON object containing the search results (title, url, body) or error.
    """
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(r)
        return {"status": "success", "results": results}
    except Exception as e:
        logger.error("web_search failed for query '%s': %s", query, e, exc_info=True)
        return {"status": "error", "message": "ไม่สามารถค้นหาข้อมูลได้ในขณะนี้ กรุณาลองใหม่"}


def read_url(url: str) -> dict:
    """Extract and summarize content from a given URL.
    
    Args:
        url: The URL to scrape.
        
    Returns:
        dict: A JSON object containing the markdown content of the page or error.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
            
        markdown_text = markdownify.markdownify(str(soup), heading_style="ATX").strip()
        
        # Limit content length to avoid exceeding token limits
        if len(markdown_text) > 15000:
            markdown_text = markdown_text[:15000] + "\n\n...[Content truncated]..."
            
        return {"status": "success", "content": markdown_text}
    except Exception as e:
        logger.error("read_url failed for '%s': %s", url, e, exc_info=True)
        return {"status": "error", "message": "ไม่สามารถอ่านเนื้อหาจาก URL นี้ได้ กรุณาตรวจสอบลิงก์"}


def generate_image(prompt: str) -> dict:
    """Generate an image using the Nano Banana Pro (Gemini 3 Pro Image Preview) model.
    
    Args:
        prompt: A detailed description of the image to generate. Please use English for best results.
        
    Returns:
        dict: A JSON object containing the image generation status and the image URL.
    """
    try:
        # We need a dedicated directory for images in static
        image_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "outputs")
        os.makedirs(image_dir, exist_ok=True)
        
        client = genai.Client()
        
        response = client.models.generate_content(
            model='gemini-3-pro-image-preview',
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            )
        )
        
        if hasattr(response, 'candidates') and response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                data = None
                if getattr(part, "inline_data", None) and hasattr(part.inline_data, "data"):
                    data = part.inline_data.data
                elif getattr(part, "image", None) and hasattr(part.image, "image_bytes"):
                    data = part.image.image_bytes
                    
                if data:
                    file_id = str(uuid.uuid4())[:8]
                    filename = f"generated_{file_id}.png"
                    filepath = os.path.join(image_dir, filename)
                    
                    with open(filepath, "wb") as f:
                        f.write(data)
                    
                    result = {
                        "type": "image_generation",
                        "filename": filename,
                        "url": f"/images/{filename}",
                        "message": f"วาดภาพ '{prompt}' เสร็จเรียบร้อยแล้วครับ! 🎨"
                    }
                    return {"status": "success", "result": json.dumps(result, ensure_ascii=False)}
                    
        return {"status": "error", "message": "ไม่สามารถสร้างภาพได้จาก Model"}
    except Exception as e:
        logger.error("generate_image failed for prompt '%s': %s", prompt, e, exc_info=True)
        return {"status": "error", "message": "ไม่สามารถสร้างภาพได้ในขณะนี้ กรุณาลองใหม่"}


def execute_python_code(code: str) -> dict:
    """Execute Python code and return the output.
    
    This is useful for generating custom files like PDF using fpdf, data analysis, 
    or any task that requires executing dynamic Python scripts.
    
    Args:
        code: The Python code to execute.
        
    Returns:
        dict: A JSON object containing the execution status and output or error.
    """
    try:
        # Create a temporary file to hold the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(code)
            temp_file_path = temp_file.name
            
        # Execute the code
        result = subprocess.run(
            [sys.executable, temp_file_path],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
            cwd=os.path.dirname(os.path.dirname(__file__)) # Execute from the project root so ./exports and ./fonts paths work
        )
        
        # Clean up
        try:
            os.remove(temp_file_path)
        except:
            pass
            
        if result.returncode == 0:
            return {"status": "success", "output": result.stdout}
        else:
            return {"status": "error", "error": result.stderr, "output": result.stdout}
            
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "Execution timed out after 30 seconds."}
    except Exception as e:
        logger.error("execute_python_code failed: %s", e, exc_info=True)
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


root_agent = Agent(
    name="life_coach_agent",
    model="gemini-3.1-pro-preview",
    description="AI Life Coach that helps with writing, self-discovery, life guidance, web searching, URL reading, image generation, and creates downloadable documents (DOCX, PDF, XLSX).",
    instruction=SYSTEM_INSTRUCTION,
    tools=[generate_mcq, create_docx_document, create_xlsx_document, web_search, read_url, generate_image, execute_python_code],
)
