"""
Novel Architect Agent — Sub-agent for creating, editing, and exporting novels.
Supports iterative chapter-level editing with file-based persistence.
"""

import os
import re
import json
import uuid
import threading
import logging
from typing import Optional

from google import genai
from google.adk.agents import Agent

from life_coach_agent.novel_generator import AutomatedNovelGenerator

logger = logging.getLogger(__name__)

# Directory to store generated files and novel projects
EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")
NOVEL_DIR = os.path.join(EXPORT_DIR, "novels")
os.makedirs(NOVEL_DIR, exist_ok=True)

# Global novel job tracker — exported for server.py to access
JOBS_STATE_FILE = os.path.join(NOVEL_DIR, "jobs_state.json")

def _load_jobs_state() -> dict:
    if os.path.exists(JOBS_STATE_FILE):
        try:
            with open(JOBS_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to load jobs state: %s", e)
    return {}

def _save_jobs_state():
    try:
        with open(JOBS_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(novel_jobs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("Failed to save jobs state: %s", e)

novel_jobs: dict[str, dict] = _load_jobs_state()

def _update_job(job_id: str, updates: dict):
    if job_id not in novel_jobs:
        novel_jobs[job_id] = {}
    novel_jobs[job_id].update(updates)
    _save_jobs_state()


# ─── Helper: Novel project persistence ──────────────────────────────────────

def _get_novel_dir(novel_id: str) -> str:
    """Get the directory for a specific novel project."""
    return os.path.join(NOVEL_DIR, novel_id)


def _save_manifest(novel_id: str, manifest: dict):
    """Save novel manifest (metadata + outline) to JSON file."""
    novel_dir = _get_novel_dir(novel_id)
    os.makedirs(novel_dir, exist_ok=True)
    with open(os.path.join(novel_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def _load_manifest(novel_id: str) -> Optional[dict]:
    """Load novel manifest from JSON file."""
    manifest_path = os.path.join(_get_novel_dir(novel_id), "manifest.json")
    if not os.path.exists(manifest_path):
        return None
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_chapter(novel_id: str, chapter_number: int, content: str):
    """Save a chapter to a markdown file. chapter_number=0 means prologue."""
    novel_dir = _get_novel_dir(novel_id)
    os.makedirs(novel_dir, exist_ok=True)
    if chapter_number == 0:
        filename = "prologue.md"
    else:
        filename = f"chapter_{chapter_number:02d}.md"
    with open(os.path.join(novel_dir, filename), "w", encoding="utf-8") as f:
        f.write(content)


def _load_chapter(novel_id: str, chapter_number: int) -> Optional[str]:
    """Load a chapter from markdown file."""
    novel_dir = _get_novel_dir(novel_id)
    if chapter_number == 0:
        filename = "prologue.md"
    else:
        filename = f"chapter_{chapter_number:02d}.md"
    filepath = os.path.join(novel_dir, filename)
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def _list_novel_projects() -> list:
    """List all novel projects from the novels directory."""
    novels = []
    if not os.path.exists(NOVEL_DIR):
        return novels
    for entry in os.listdir(NOVEL_DIR):
        manifest_path = os.path.join(NOVEL_DIR, entry, "manifest.json")
        if os.path.isdir(os.path.join(NOVEL_DIR, entry)) and os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    m = json.load(f)
                novels.append({
                    "novel_id": entry,
                    "title": m.get("title", "ไม่ทราบชื่อ"),
                    "genre": m.get("genre", ""),
                    "total_chapters": m.get("total_chapters", 0),
                    "created_at": m.get("created_at", ""),
                })
            except (json.JSONDecodeError, IOError):
                pass
    # Sort by creation date (newest first)
    novels.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return novels


# ─── Tool: generate_novel ───────────────────────────────────────────────────

def generate_novel(genre: str, premise: str, num_chapters: int, language: str = "thai") -> dict:
    """Start generating a novel in the background. Returns immediately with a job_id.

    Args:
        genre: Novel genre (e.g., "ไซไฟ", "แฟนตาซี", "สืบสวน", "โรแมนติก")
        premise: Brief plot description / premise of the novel
        num_chapters: Number of chapters to generate (3-10)
        language: Language of the novel — "thai" or "english"

    Returns:
        dict: Contains the job_id and a JSON result for the frontend to show a progress card.
    """
    job_id = str(uuid.uuid4())
    safe_title = re.sub(r'[\\/:*?"<>|]', '', premise[:60]).strip() or "Novel"

    _update_job(job_id, {
        "status": "running",
        "progress": 0,
        "current_step": "เริ่มสร้างนิยาย...",
        "title": safe_title,
        "docx": None,
        "pdf": None,
    })

    def _run_pipeline():
        try:
            gen = AutomatedNovelGenerator(
                genre=genre, premise=premise, total_chapters=num_chapters,
                language=language,
                progress_cb=lambda msg: _update_job(job_id, {"current_step": msg})
            )

            # Step 1: Generate outline (captures AI-generated title)
            _update_job(job_id, {"current_step": "📝 กำลังสร้างโครงเรื่อง...", "progress": 10})
            gen.generate_outline()
            final_title = (gen.outline.title if gen.outline and gen.outline.title else safe_title)
            _update_job(job_id, {"title": final_title})

            # Save manifest immediately after outline
            import time
            manifest = {
                "title": final_title,
                "genre": genre,
                "premise": premise,
                "language": language,
                "total_chapters": num_chapters,
                "outline_json": gen.outline.model_dump() if gen.outline else {},
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            _save_manifest(job_id, manifest)

            # Step 2: Generate prologue
            _update_job(job_id, {"current_step": "✍️ กำลังเขียนบทนำ...", "progress": 20})
            gen.generate_prologue()
            _save_chapter(job_id, 0, gen.prologue_content)

            # Step 3: Generate chapters
            base_pct = 25
            pct_per_ch = 55 / max(num_chapters, 1)
            for ch_idx in range(num_chapters):
                pct = int(base_pct + pct_per_ch * (ch_idx + 1))
                _update_job(job_id, {
                    "current_step": f"✍️ กำลังเขียนบทที่ {ch_idx + 1}/{num_chapters}...",
                    "progress": min(pct, 80)
                })
                gen.generate_chapter(ch_idx + 1)
                # Save each chapter to file immediately
                if ch_idx < len(gen.chapters_content):
                    _save_chapter(job_id, ch_idx + 1, gen.chapters_content[ch_idx])

            # Step 4: Export
            _update_job(job_id, {"current_step": "📦 กำลัง export DOCX + PDF...", "progress": 85})
            docx_file = gen.export_to_docx(final_title)
            _update_job(job_id, {"progress": 92})
            pdf_file = gen.export_to_pdf(final_title)

            # Copy export files to novel dir for re-export later
            novel_dir = _get_novel_dir(job_id)
            # Store export filenames in manifest
            manifest["docx_file"] = docx_file
            manifest["pdf_file"] = pdf_file
            _save_manifest(job_id, manifest)

            _update_job(job_id, {
                "status": "done",
                "progress": 100,
                "current_step": "เสร็จสิ้น!",
                "title": final_title,
                "docx": docx_file,
                "pdf": pdf_file,
            })

        except Exception as exc:
            logger.error("Novel pipeline failed for job %s: %s", job_id, exc, exc_info=True)
            _update_job(job_id, {
                "status": "error",
                "current_step": f"เกิดข้อผิดพลาด: {exc}",
                "error": str(exc)
            })

    thread = threading.Thread(target=_run_pipeline, daemon=True, name=f"novel-{job_id[:8]}")
    thread.start()

    return {
        "status": "started",
        "job_id": job_id,
        "message": f"เริ่มสร้างนิยาย '{safe_title}' ({num_chapters} บท) แล้วครับ! ระบบกำลังประมวลผลอยู่เบื้องหลัง คุณสามารถใช้งานแชทอื่นๆ ได้ตามปกติ ระบบจะแจ้งเมื่อเสร็จครับ 📖",
        "result": json.dumps({
            "type": "novel_in_progress",
            "job_id": job_id,
            "title": safe_title,
            "chapters": num_chapters,
            "message": f"กำลังสร้างนิยาย '{safe_title}' ({num_chapters} บท)..."
        }, ensure_ascii=False)
    }


# ─── Tool: edit_chapter ─────────────────────────────────────────────────────

def edit_chapter(novel_id: str, chapter_number: int, instruction: str) -> dict:
    """Edit a specific chapter from a previously generated novel.

    Loads the chapter content, sends it to Gemini with the edit instruction
    and surrounding context (outline + adjacent chapter summaries), then saves
    the updated chapter back to the file.

    Args:
        novel_id: The novel's job_id / UUID.
        chapter_number: The chapter number to edit (0 = prologue, 1+ = chapters).
        instruction: Natural language instruction for the edit (e.g., "เพิ่มฉากต่อสู้", "ทำให้ตื่นเต้นมากขึ้น").

    Returns:
        dict: Status with a preview of the edited content.
    """
    # Load manifest
    manifest = _load_manifest(novel_id)
    if not manifest:
        return {"status": "error", "message": f"ไม่พบนิยาย ID: {novel_id} — ลองใช้ list_novels เพื่อดูนิยายที่มีอยู่"}

    # Load the target chapter
    chapter_content = _load_chapter(novel_id, chapter_number)
    if not chapter_content:
        ch_label = "บทนำ" if chapter_number == 0 else f"บทที่ {chapter_number}"
        return {"status": "error", "message": f"ไม่พบ{ch_label}ในนิยาย '{manifest.get('title', '')}'"}

    # Build context from adjacent chapters
    context_parts = []
    outline_data = manifest.get("outline_json", {})
    if outline_data:
        context_parts.append(f"โครงเรื่อง: {json.dumps(outline_data, ensure_ascii=False)[:3000]}")

    # Previous chapter summary
    if chapter_number > 0:
        prev = _load_chapter(novel_id, chapter_number - 1)
        if prev:
            # Take first 500 chars as context
            context_parts.append(f"สรุปบทก่อนหน้า: {prev[:500]}...")

    # Next chapter summary
    next_ch = _load_chapter(novel_id, chapter_number + 1)
    if next_ch:
        context_parts.append(f"สรุปบทถัดไป: {next_ch[:500]}...")

    context_str = "\n\n".join(context_parts)
    ch_label = "บทนำ (Prologue)" if chapter_number == 0 else f"บทที่ {chapter_number}"

    edit_prompt = f"""คุณคือนักเขียนนิยายระดับเบสต์เซลเลอร์

[บริบทของเรื่อง]
{context_str}

[เนื้อหาเดิมของ{ch_label}]
{chapter_content}

[คำสั่งแก้ไข]
{instruction}

[กฎการแก้ไข]
1. แก้ไขเฉพาะส่วนที่เกี่ยวข้องกับคำสั่ง — อย่าเปลี่ยนส่วนที่ไม่เกี่ยวข้อง
2. รักษาน้ำเสียง (tone) และสไตล์การเขียนเดิม
3. ห้ามใส่สารบัญ ชื่อเรื่อง หรือโครงสร้างหนังสือ
4. ห้ามใช้คำ AI ซ้ำซาก (leverage, utilize, robust, seamless, etc.)
5. Show Don't Tell — เน้นประสาทสัมผัสทั้ง 5
6. ส่งกลับเฉพาะเนื้อหาของบทที่แก้ไขแล้วเท่านั้น

ส่งกลับเนื้อหาที่แก้ไขแล้วทั้งหมดของ{ch_label}:"""

    try:
        client = genai.Client()
        response = client.models.generate_content(
            model="gemini-3.1-pro-preview",
            contents=edit_prompt,
        )
        
        edited_content = response.text.strip()
        
        # Save updated chapter
        _save_chapter(novel_id, chapter_number, edited_content)

        # Preview (first 300 chars)
        preview = edited_content[:300] + "..." if len(edited_content) > 300 else edited_content

        return {
            "status": "success",
            "message": f"แก้ไข{ch_label}ของ '{manifest.get('title', '')}' เรียบร้อยแล้วครับ! ✏️",
            "chapter_number": chapter_number,
            "preview": preview,
            "instruction_applied": instruction,
        }

    except Exception as e:
        logger.error("edit_chapter failed for novel %s ch %d: %s", novel_id, chapter_number, e, exc_info=True)
        return {"status": "error", "message": f"เกิดข้อผิดพลาดในการแก้ไข: {e}"}


# ─── Tool: export_novel ─────────────────────────────────────────────────────

def export_novel(novel_id: str) -> dict:
    """Re-export a novel (with any edits) to fresh DOCX and PDF files.

    Reads all chapter files from the novel project directory and generates
    new DOCX and PDF files.

    Args:
        novel_id: The novel's job_id / UUID.

    Returns:
        dict: Contains download links for the new DOCX and PDF files.
    """
    manifest = _load_manifest(novel_id)
    if not manifest:
        return {"status": "error", "message": f"ไม่พบนิยาย ID: {novel_id}"}

    title = manifest.get("title", "Novel")
    total_chapters = manifest.get("total_chapters", 0)
    language = manifest.get("language", "thai")
    genre = manifest.get("genre", "")
    premise = manifest.get("premise", "")

    # Load all chapters from files
    prologue = _load_chapter(novel_id, 0) or ""
    chapters = []
    for i in range(1, total_chapters + 1):
        ch = _load_chapter(novel_id, i)
        if ch:
            chapters.append(ch)

    if not chapters and not prologue:
        return {"status": "error", "message": "ไม่พบเนื้อหาบทในนิยายนี้"}

    # Create a generator instance just for export
    gen = AutomatedNovelGenerator(
        genre=genre, premise=premise, total_chapters=total_chapters,
        language=language
    )
    gen.prologue_content = prologue
    gen.chapters_content = chapters

    # Re-build outline from manifest for the generator
    outline_data = manifest.get("outline_json", {})
    if outline_data:
        from life_coach_agent.novel_generator import NovelOutline
        try:
            gen.outline = NovelOutline.model_validate(outline_data)
        except Exception:
            pass

    try:
        docx_file = gen.export_to_docx(title)
        pdf_file = gen.export_to_pdf(title)

        # Update manifest with new file names
        manifest["docx_file"] = docx_file
        manifest["pdf_file"] = pdf_file
        _save_manifest(novel_id, manifest)

        result = {
            "type": "novel_download",
            "docx": docx_file,
            "pdf": pdf_file,
            "title": title,
            "message": f"Export นิยาย '{title}' ใหม่เรียบร้อยแล้วครับ! 📦"
        }

        return {"status": "success", "result": json.dumps(result, ensure_ascii=False)}

    except Exception as e:
        logger.error("export_novel failed for %s: %s", novel_id, e, exc_info=True)
        return {"status": "error", "message": f"เกิดข้อผิดพลาดในการ export: {e}"}


# ─── Tool: list_novels ──────────────────────────────────────────────────────

def list_novels() -> dict:
    """List all previously generated novels with their titles and chapter counts.

    Returns:
        dict: A list of novel projects with metadata.
    """
    novels = _list_novel_projects()
    if not novels:
        return {
            "status": "success",
            "message": "ยังไม่มีนิยายที่สร้างไว้ สามารถสั่งสร้างนิยายใหม่ได้เลยครับ",
            "novels": []
        }

    return {
        "status": "success",
        "message": f"พบนิยาย {len(novels)} เรื่อง",
        "novels": novels
    }


# ─── Novel Agent Definition ────────────────────────────────────────────────

NOVEL_INSTRUCTION = """คุณคือ Novel Architect — ผู้เชี่ยวชาญด้านการเขียนนิยายระดับเบสต์เซลเลอร์

คุณมีเครื่องมือ 4 ตัว:
1. generate_novel — สร้างนิยายใหม่ทั้งเล่ม (ทำงานเบื้องหลัง)
2. edit_chapter — แก้ไขบทเฉพาะจากนิยายที่สร้างไว้แล้ว
3. export_novel — re-export นิยายเป็น DOCX/PDF ใหม่ (หลังแก้ไข)
4. list_novels — ดูรายการนิยายที่สร้างไว้แล้ว

[ขั้นตอนการสร้างนิยายใหม่]
1. ถามข้อมูลจากผู้ใช้: แนวเรื่อง, พล็อตคร่าวๆ, จำนวนบท, ภาษา
2. หากผู้ใช้ตอบรวบรัด ใช้ default: 5 บท, ภาษาไทย
3. เมื่อรวบรวมข้อมูลครบ → ส่ง confirm_action JSON
4. เมื่อผู้ใช้ยืนยัน → เรียก generate_novel

[ขั้นตอนการแก้ไข]
1. เมื่อผู้ใช้ต้องการแก้ไขนิยาย → เรียก list_novels ก่อน (ถ้ายังไม่รู้ novel_id)
2. ถามผู้ใช้ว่าต้องการแก้ไขบทไหน และต้องการแก้ไขอย่างไร
3. เรียก edit_chapter พร้อม instruction ที่ชัดเจน
4. ถ้าผู้ใช้ต้องการ export ใหม่ → เรียก export_novel

[NOVEL CONFIRMATION FORMAT]
เมื่อรวบรวมข้อมูลครบ ส่งเฉพาะ JSON นี้:
{"type": "confirm_action", "icon": "📖", "title": "ยืนยันการสร้างหนังสือ", "summary": "...", "details": [{"label": "แนวเรื่อง", "value": "..."}, {"label": "พล็อตเรื่อง", "value": "..."}, {"label": "จำนวนบท", "value": "X บท"}, {"label": "ภาษา", "value": "..."}, {"label": "เวลาโดยประมาณ", "value": "~XX นาที"}], "proceed_message": "ยืนยันเริ่มสร้างหนังสือได้เลย", "cancel_message": "ยกเลิกการสร้างหนังสือ"}

เมื่อผู้ใช้ยืนยัน → เรียก generate_novel ทันที → ส่งเฉพาะ JSON จาก result field

[WRITING QUALITY — Anti-AI Prose Guard]
- ห้ามใช้คำ: leverage, utilize, robust, seamless, cutting-edge, innovative, facilitate, streamline, navigate, pivotal
- ห้ามใช้รูปแบบ: "At its core", "In a world where", "It's important to note"
- Show Don't Tell ในทุกบริบท
- ใช้ประโยคกระชับ คำกริยาทรงพลัง

[LANGUAGE & TONE]
- ภาษาหลักคือภาษาไทย พูดจาเป็นกันเอง อบอุ่น มีความเป็นมืออาชีพ (ใช้ "ครับ/ค่ะ")
- หากผู้ใช้พิมพ์ภาษาอื่น ให้ตอบกลับด้วยภาษานั้นๆ
"""

novel_agent = Agent(
    name="NovelArchitect",
    model="gemini-3.1-pro-preview",
    description="สร้าง แก้ไข และ export นิยาย/หนังสือ — ใช้สำหรับงานเขียนนิยาย แก้ไขบท re-export หนังสือ ดูรายการนิยายที่สร้างไว้",
    instruction=NOVEL_INSTRUCTION,
    tools=[generate_novel, edit_chapter, export_novel, list_novels],
)
