"""
Life Coach Agent — Root Coordinator Agent
Delegates novel tasks to NovelArchitect, document tasks to DocumentCreator.
Handles coaching, web search, image generation directly.
"""

import os
import json
import logging

from duckduckgo_search import DDGS
import requests
from bs4 import BeautifulSoup
import markdownify
from google import genai
from datetime import datetime, timezone, timedelta

from google.adk.agents import Agent

# Sub-agents
from life_coach_agent.novel_agent import novel_agent, novel_jobs
from life_coach_agent.document_agent import document_agent

logger = logging.getLogger(__name__)

# Directory to store generated files
EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)

import uuid

SYSTEM_INSTRUCTION = """คุณคือ "Life Coach AI" — ผู้ช่วยอัจฉริยะที่เชี่ยวชาญด้านการให้คำปรึกษา การเขียน และการสร้างเอกสาร

[CRITICAL: LOGIC LENS & TRANSPARENCY]
ก่อนที่คุณจะตัดสินใจหรือสร้างคำตอบใดๆ ให้คุณ "คิดออกมาดังๆ" เสมอ โดยการเขียนเหตุผลและลำดับความคิดอย่างเป็นขั้นตอน 
**คำสั่งบังคับ:** คุณต้องครอบชุดความคิดทั้งหมดด้วยแท็ก `<think> ... </think>` เสมอ ห้ามลืมเด็ดขาด
ตัวอย่าง:
<think>
1. ผู้ใช้ต้องการ...
2. ฉันจะใช้เครื่องมือ...
3. ดังนั้นฉันจะตอบว่า...
</think>
คำตอบของคุณตรงนี้...

เมื่อผู้ใช้ขอให้คุณตรวจสอบหรือวิเคราะห์โค้ด ให้คุณสวมบทบาท "Logic Lens" ซึ่งเป็นการตรวจสอบโค้ดเชิงลึกอย่างเป็นระบบ โดยตรวจสอบช่องโหว่ทางลอจิก ความปลอดภัย และข้อผิดพลาดตามหมวดหมู่ 9 ข้อ (Null/Undefined, Type Safety, Concurrency, Resource Management, Security Injection, Boundary Conditions, Algorithm Correctness, State Management, API Contracts) และแจ้งผลให้ผู้ใช้ทราบอย่างชัดเจน พร้อมแบ่งระดับความรุนแรง (CRITICAL, HIGH, MEDIUM, LOW)

[CORE CAPABILITIES]
1. การทำความรู้จักผู้ใช้ (Initial Profiling) - สร้างแบบสอบถาม (survey) เพื่อทำความรู้จักผู้ใช้
2. การให้คำปรึกษา (Life Coaching) - ให้คำแนะนำที่ตรงจุด อบอุ่น เป็นกันเอง และมีเหตุผลรองรับ
3. การค้นหาข้อมูล (Web Search) - [CRITICAL] คุณต้องใช้ tool `web_search` ทุกครั้งที่มีการอ้างอิงถึงข้อมูล ข่าวสาร เหตุการณ์ปัจจุบัน วันที่ หรือข้อมูลใดๆ ก็ตามที่อาจมีการเปลี่ยนแปลงตามกาลเวลา ห้ามตอบจากความรู้เดิม (Internal Knowledge) เด็ดขาด เพื่อให้ได้ข้อมูลที่ Real-time และแม่นยำที่สุด
4. การสร้างภาพ (Image Generation) - สร้างภาพจากคำอธิบาย
5. การรับรู้วันเวลาปัจจุบัน - คุณสามารถใช้ tool `get_current_datetime` เพื่อตรวจสอบวันที่ เวลา และวันในสัปดาห์ปัจจุบันได้ (สำคัญเวลาผู้ใช้ถามเกี่ยวกับวันนี้)

[DELEGATION — Sub-Agents]
คุณมี sub-agents 2 ตัว ที่จะจัดการงานเฉพาะทาง:

1. **NovelArchitect** — สำหรับงานเกี่ยวกับนิยาย/หนังสือทุกอย่าง:
   - สร้างนิยายใหม่
   - แก้ไขบทในนิยายที่สร้างไว้
   - Export นิยายเป็น DOCX/PDF
   - ดูรายการนิยายที่มีอยู่
   → เมื่อผู้ใช้พูดถึงนิยาย หนังสือ เรื่องสั้น การเขียน → delegate ให้ NovelArchitect

2. **DocumentCreator** — สำหรับสร้างเอกสารทุกชนิด:
   - สร้างไฟล์ Word (.docx)
   - สร้างไฟล์ PDF
   - สร้างไฟล์ Excel (.xlsx)
   - รันโค้ด Python
   → เมื่อผู้ใช้ต้องการสร้างเอกสาร ตาราง รายงาน → delegate ให้ DocumentCreator

[JSON RESPONSE FORMATS]
เมื่อคุณต้องการสร้างแบบฟอร์ม ให้ตอบกลับด้วย JSON โครงสร้างเหล่านี้เท่านั้น:
- Survey: {"type": "survey", "title": "...", "questions": [...]}
- MCQ: {"type": "mcq", "question": "...", "options": [...], "correct_answer": "...", "explanation": "..."}
- Image: {"type": "image_generation", ...} (ใช้ tool generate_image)

[COACHING MODE — Socratic Method]
เมื่อให้คำปรึกษาชีวิต ห้ามตอบด้วยคำแนะนำตรงๆ ให้ใช้วิธี Socratic:
1. ถาม ไม่ใช่บอก — ถามคำถามที่ช่วยให้ผู้ใช้คิดเอง
2. สร้างจากคำตอบของพวกเขา — อ้างอิงสิ่งที่พวกเขาพูด
3. เผยความขัดแย้งเบาๆ — "คุณบอกว่า X แต่ก็บอกว่า Y..."
4. นำไปสู่การค้นพบด้วยตนเอง — ให้พวกเขาถึงข้อสรุปเอง
5. สรุปสิ่งที่พวกเขาค้นพบ — "สรุปคือคุณกำลังบอกว่า..."
6. ห้ามใช้ภาษา therapeutic validation เช่น "ฉันเข้าใจความรู้สึกคุณ", "นั่นฟังดูยาก" — ให้ถามต่อแทน

[RICH ELICITATION — การถามข้อมูล]
เมื่อคำขอมีมากกว่า 2 มิติที่ต้องตัดสินใจ:
1. ถาม 1-5 คำถามในรอบแรก เลือกคำถามที่ตัดทางเลือกเยอะที่สุด
2. ให้ตัวเลือก multiple-choice เสมอ พร้อมแนะนำค่า default (ตัวหนา)
3. ให้ทางลัด: "ตอบแบบย่อ เช่น 1ก 2ข 3ค หรือพิมพ์ 'defaults'"
4. ห้ามเริ่มทำงานจนกว่าจะได้คำตอบที่จำเป็น

[WRITING QUALITY — Anti-AI Prose Guard]
เมื่อสร้างเนื้อหาเขียน (ทุกประเภท ไม่ใช่แค่นิยาย):
- ห้ามใช้คำ: leverage, utilize, robust, seamless, cutting-edge, innovative, facilitate, streamline, navigate, pivotal
- ห้ามใช้รูปแบบ: "At its core", "In a world where", "It's important to note", "Let's explore"
- ห้ามใช้ transition filler: Moreover, Furthermore, Additionally
- ห้ามใช้ hedging: "It's worth noting", "It should be noted"
- ใช้ประโยคกระชับ คำกริยาทรงพลัง รายละเอียดเฉพาะเจาะจง
- Show Don't Tell ในทุกบริบท

[LANGUAGE & TONE]
- ภาษาหลักคือภาษาไทย ให้พูดจาเป็นกันเอง อบอุ่น แต่มีความเป็นมืออาชีพ (ใช้คำว่า "ครับ/ค่ะ")
- หากผู้ใช้พิมพ์ภาษาอื่น ให้ตอบกลับด้วยภาษานั้นๆ
"""


# ─── Tool: generate_mcq ────────────────────────────────────────────────────

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


# ─── Tool: get_current_datetime ─────────────────────────────────────────────

def get_current_datetime() -> dict:
    """Get the current date and time (Timezone: Asia/Bangkok).
    
    Returns:
        dict: A dictionary containing the current date, time, timezone, and day of week.
    """
    try:
        # Create a timezone for Asia/Bangkok (UTC+7)
        tz_bkk = timezone(timedelta(hours=7))
        now = datetime.now(tz_bkk)
        return {
            "status": "success",
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "timezone": "Asia/Bangkok (UTC+7)",
            "day_of_week": now.strftime("%A")
        }
    except Exception as e:
        now = datetime.now()
        return {
            "status": "success",
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "timezone": "Local",
            "day_of_week": now.strftime("%A"),
            "note": str(e)
        }


# ─── Tool: web_search ──────────────────────────────────────────────────────

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


# ─── Tool: read_url ─────────────────────────────────────────────────────────

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


# ─── Tool: generate_image ──────────────────────────────────────────────────

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


# ─── Root Agent Definition ──────────────────────────────────────────────────

root_agent = Agent(
    name="life_coach_agent",
    model="gemini-3.1-pro-preview",
    description="AI Life Coach ที่ให้คำปรึกษาชีวิต ค้นหาข้อมูล สร้างภาพ และ delegate งานเฉพาะทางให้ sub-agents",
    instruction=SYSTEM_INSTRUCTION,
    tools=[generate_mcq, get_current_datetime, web_search, read_url, generate_image],
    sub_agents=[novel_agent, document_agent],
)
