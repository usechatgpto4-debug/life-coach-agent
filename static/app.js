/**
 * Life Coach AI — Frontend Application
 * Handles chat, sessions, and MCQ modal interactions.
 */

// --- State ---
let currentSessionId = null;
let currentMcqData = null;
let selectedAnswer = null;
let pendingFiles = [];  // files waiting to be sent with next message

// --- DOM Elements ---
const $ = (sel) => document.querySelector(sel);
const sidebar       = $('#sidebar');
const sessionList   = $('#sessionList');
const chatMessages  = $('#chatMessages');
const welcomeScreen = $('#welcomeScreen');
const chatTitle     = $('#chatTitle');
const messageInput  = $('#messageInput');
const btnSend       = $('#btnSend');
const btnNewChat    = $('#btnNewChat');
const btnToggle     = $('#btnToggleSidebar');
const btnDelete     = $('#btnDeleteSession');
const btnAttach     = $('#btnAttach');
const fileInput     = $('#fileInput');
const filePreview   = $('#filePreview');
const loadingBar    = $('#loadingIndicator');

const mcqModal        = $('#mcqModal');
const mcqQuestion     = $('#mcqQuestion');
const mcqOptions      = $('#mcqOptions');
const mcqResult       = $('#mcqResult');
const resultIcon      = $('#resultIcon');
const resultText      = $('#resultText');
const resultExplanation = $('#resultExplanation');
const btnSubmitAnswer = $('#btnSubmitAnswer');
const btnCloseModal   = $('#btnCloseModal');
const btnCloseResult  = $('#btnCloseResult');
const btnNextQuestion = $('#btnNextQuestion');
const btnUserProfile  = $('#btnUserProfile');
const profileModal    = $('#profileModal');
const btnCloseProfileModal = $('#btnCloseProfileModal');
const profileSummaryContainer = $('#profileSummaryContainer');
let currentSurveyStep = 0;

const defaultOnboardingSurvey = {
    "type": "survey",
    "title": "ทำความรู้จักกันก่อนเริ่มโค้ชชิ่ง",
    "questions": [
        {
            "id": "q_prof",
            "question": "คุณทำอาชีพอะไรอยู่?",
            "inputType": "text"
        },
        {
            "id": "q_inc",
            "question": "คุณมีรายได้ประมาณเท่าไหร่? (ตัวเลขคร่าวๆ หรือช่วงรายได้)",
            "inputType": "text"
        },
        {
            "id": "q_fin",
            "question": "คุณต้องการต่อยอดเรื่องการเงินยังไงบ้าง?",
            "inputType": "text"
        },
        {
            "id": "q_goal",
            "question": "เป้าหมาย (Goal) สูงสุดของคุณคืออะไร? (เล่ารายละเอียดได้เต็มที่เลยครับ)",
            "inputType": "textarea"
        },
        {
            "id": "q1",
            "question": "ถ้าให้บรรยายความเป็นตัวเอง ค่านิยม (Values) ใดที่เป็นแกนหลักในการตัดสินใจของคุณมากที่สุด?",
            "options": [
                {"key": "A", "text": "อิสระและการเรียนรู้สิ่งใหม่ (Freedom & Growth)"},
                {"key": "B", "text": "ความมั่นคงปลอดภัยและความสงบ (Stability & Peace)"},
                {"key": "C", "text": "การสร้างอิมแพคและการช่วยเหลือผู้อื่น (Impact & Contribution)"},
                {"key": "D", "text": "ความสำเร็จและการได้รับการยอมรับ (Success & Recognition)"},
                {"key": "Other", "text": "อื่นๆ (โปรดระบุ)"}
            ]
        },
        {
            "id": "q2",
            "question": "สไตล์การทำงานหรือการจัดการชีวิตแบบไหนที่ตรงกับคุณมากที่สุด?",
            "options": [
                {"key": "A", "text": "ชอบวางแผนล่วงหน้าชัดเจน เป๊ะทุกขั้นตอน"},
                {"key": "B", "text": "มีเป้าหมายหลวมๆ แล้วชอบแก้ปัญหาเฉพาะหน้าเอา"},
                {"key": "C", "text": "ทำตามความรู้สึกและสัญชาตญาณเป็นหลัก"},
                {"key": "D", "text": "รับฟังความเห็นคนอื่นเยอะๆ แล้วค่อยตัดสินใจ"},
                {"key": "Other", "text": "อื่นๆ (โปรดระบุ)"}
            ]
        },
        {
            "id": "q3",
            "question": "อะไรคือความท้าทาย หรือสิ่งที่มักจะฉุดรั้งการพัฒนาตัวเองของคุณบ่อยที่สุด?",
            "options": [
                {"key": "A", "text": "ความสับสน ลังเล ไม่รู้จะไปทางไหนดี"},
                {"key": "B", "text": "ทำหลายอย่างเกินไป จัดสรรเวลาไม่ได้ (Burnout)"},
                {"key": "C", "text": "ผลัดวันประกันพรุ่ง ขาดแรงจูงใจและวินัย"},
                {"key": "D", "text": "ขาดความมั่นใจในตัวเอง กลัวความล้มเหลว"},
                {"key": "Other", "text": "อื่นๆ (โปรดระบุ)"}
            ]
        },
        {
            "id": "q4",
            "question": "คุณอยากให้ AI Life Coach ช่วยเหลือคุณด้วยสไตล์แบบไหนมากที่สุด?",
            "options": [
                {"key": "A", "text": "เน้นให้กำลังใจ ซัพพอร์ต เป็นผู้ฟังที่ดี 💖"},
                {"key": "B", "text": "ตรงไปตรงมา กระตุ้นให้คิด ท้าทายให้ออกจาก Comfort Zone 🤔"},
                {"key": "C", "text": "มีโครงสร้างชัดเจน เป็นขั้นเป็นตอน เน้นวิธีแก้ปัญหา 📊"},
                {"key": "D", "text": "เน้นไอเดียสร้างสรรค์ ชวนเปิดมุมมองและวิธีคิดใหม่ๆ 🎨"},
                {"key": "Other", "text": "อื่นๆ (โปรดระบุ)"}
            ]
        }
    ]
};

// --- API Helpers ---
const api = {
    async post(url, body) {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        return res.json();
    },
    async get(url) {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        return res.json();
    },
    async del(url) {
        const res = await fetch(url, { method: 'DELETE' });
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        return res.json();
    },
};

// --- Loading State ---
function setLoading(on) {
    loadingBar.style.display = on ? 'block' : 'none';
    btnSend.disabled = on || !messageInput.value.trim();
    messageInput.disabled = on;
}

// --- Sessions ---
async function loadSessions() {
    const sessions = await api.get('/api/sessions');
    renderSessionList(sessions);
}

function renderSessionList(sessions) {
    sessionList.innerHTML = '';
    sessions.forEach((s) => {
        const el = document.createElement('div');
        el.className = `session-item${s.id === currentSessionId ? ' active' : ''}`;
        el.innerHTML = `
            <span class="session-icon">💬</span>
            <span class="session-title">${escapeHtml(s.title)}</span>
        `;
        el.addEventListener('click', () => switchSession(s.id, s.title));
        sessionList.appendChild(el);
    });
}

async function createNewSession() {
    const data = await api.post('/api/sessions', { title: 'New Chat' });
    currentSessionId = data.id;
    chatTitle.textContent = 'New Chat';
    clearMessages();
    showWelcome(true);
    await loadSessions();
}

async function switchSession(id, title) {
    currentSessionId = id;
    chatTitle.textContent = title;
    clearMessages();
    showWelcome(false);
    await loadSessions();
    await loadMessages(id);
}

async function deleteCurrentSession() {
    if (!currentSessionId) return;
    const confirmed = await showConfirmModal('ลบแชตนี้?');
    if (!confirmed) return;
    await api.del(`/api/sessions/${currentSessionId}`);
    currentSessionId = null;
    chatTitle.textContent = 'Life Coach AI';
    clearMessages();
    showWelcome(true);
    await loadSessions();
}

// --- Messages ---
async function loadMessages(sessionId) {
    const messages = await api.get(`/api/sessions/${sessionId}/messages`);
    if (messages.length === 0) {
        showWelcome(true);
        return;
    }
    showWelcome(false);
    messages.forEach((m) => {
        if (m.role === 'user' && m.content.startsWith('[System]')) return;
        appendMessage(m.role, m.content, m.msg_type, false);
    });
    scrollToBottom();
}

function clearMessages() {
    const msgs = chatMessages.querySelectorAll('.message, .typing-indicator');
    msgs.forEach((m) => m.remove());
}

function showWelcome(show) {
    if (welcomeScreen) {
        welcomeScreen.style.display = show ? 'flex' : 'none';
    }
}

function appendMessage(role, content, msgType = 'text', animate = true) {
    showWelcome(false);

    const msgEl = document.createElement('div');
    msgEl.className = `message ${role}`;

    const avatarContent = role === 'agent' ? '✦' : '👤';

    if ((msgType === 'mcq' || msgType === 'survey') && role === 'agent') {
        let mcqData;
        try {
            mcqData = JSON.parse(content);
        } catch {
            msgEl.innerHTML = buildTextMessage(avatarContent, content, role);
            chatMessages.appendChild(msgEl);
            return;
        }

        const isSurvey = msgType === 'survey';
        const label = isSurvey ? '📋 แบบสอบถาม' : '📝 แบบทดสอบ';
        const hint = isSurvey ? 'คลิกเพื่อตอบแบบสอบถาม →' : 'คลิกเพื่อเริ่มทำข้อสอบ →';

        msgEl.innerHTML = `
            <div class="message-avatar">${avatarContent}</div>
            <div class="message-content">
                <div class="mcq-chat-card" data-mcq='${escapeHtml(content)}'>
                    <div class="mcq-chat-label">${label}</div>
                    <div class="mcq-chat-preview">${escapeHtml(mcqData.question)}</div>
                    <div class="mcq-chat-hint">${hint}</div>
                </div>
            </div>
        `;

        const card = msgEl.querySelector('.mcq-chat-card');
        card.addEventListener('click', () => openMcqModal(mcqData));

    } else if (msgType === 'file' && role === 'agent') {
        let fileData;
        try {
            fileData = JSON.parse(content);
        } catch {
            msgEl.innerHTML = buildTextMessage(avatarContent, content, role);
            chatMessages.appendChild(msgEl);
            return;
        }

        if (fileData.type === 'image_generation') {
            msgEl.innerHTML = `
                <div class="message-avatar">${avatarContent}</div>
                <div class="message-content">
                    <div class="image-generation-card" style="background: var(--card-bg); padding: 12px; border-radius: 12px; border: 1px solid var(--border-color);">
                        <img src="${escapeHtml(fileData.url)}" alt="Generated Image" style="max-width: 100%; border-radius: 8px; margin-bottom: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                        <div style="font-size: 0.9em; color: var(--text-muted);">${escapeHtml(fileData.message || 'Generated Image')}</div>
                    </div>
                </div>
            `;
            chatMessages.appendChild(msgEl);
            return;
        }

        // Determine icon & color by file type
        const typeInfo = {
            'docx_download': { icon: '📄', label: 'Word Document', accent: '#3b82f6' },
            'pdf_download':  { icon: '📕', label: 'PDF Document',  accent: '#ef4444' },
            'xlsx_download': { icon: '📊', label: 'Excel Spreadsheet', accent: '#22c55e' },
        };
        const info = typeInfo[fileData.type] || typeInfo['docx_download'];

        msgEl.innerHTML = `
            <div class="message-avatar">${avatarContent}</div>
            <div class="message-content">
                <div class="file-download-card" style="--file-accent: ${info.accent}">
                    <div class="file-card-icon">${info.icon}</div>
                    <div class="file-card-info">
                        <div class="file-card-label">${info.label}</div>
                        <div class="file-card-title">${escapeHtml(fileData.title || 'เอกสาร')}</div>
                        <div class="file-card-filename">${escapeHtml(fileData.filename || 'document')}</div>
                        <div class="file-card-message">${escapeHtml(fileData.message || 'สร้างเรียบร้อยแล้ว!')}</div>
                    </div>
                    <a href="/api/download/${encodeURIComponent(fileData.filename)}" 
                       class="file-download-btn" style="background: linear-gradient(135deg, ${info.accent}, ${info.accent}dd)" download>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                            <polyline points="7 10 12 15 17 10"/>
                            <line x1="12" y1="15" x2="12" y2="3"/>
                        </svg>
                        ดาวน์โหลด
                    </a>
                </div>
            </div>
        `;

    } else {
        if (role === 'agent' && animate && msgType === 'text') {
            // Agent text: use typewriter effect
            msgEl.innerHTML = `
                <div class="message-avatar" style="background: var(--gradient-accent); color: white; box-shadow: var(--shadow-glow);">${avatarContent}</div>
                <div class="message-content">
                    <div class="message-bubble"><span class="tw-cursor">▍</span></div>
                </div>
            `;
            msgEl.style.animation = 'msgSlideIn 0.3s ease';
            chatMessages.appendChild(msgEl);
            scrollToBottom();

            const bubble = msgEl.querySelector('.message-bubble');
            typewriterEffect(bubble, content);
            return;
        } else {
            msgEl.innerHTML = buildTextMessage(avatarContent, content, role);
        }
    }

    if (animate) {
        msgEl.style.animation = 'msgSlideIn 0.3s ease';
    }

    chatMessages.appendChild(msgEl);
    scrollToBottom();
}

function buildTextMessage(avatar, content, role) {
    const avatarStyle = role === 'agent'
        ? ' style="background: var(--gradient-accent); color: white; box-shadow: var(--shadow-glow);"'
        : '';
        
    let displayContent = content;
    if (role === 'user' && displayContent.startsWith('[ตอบแบบสอบถาม]')) {
        displayContent = '📋 ' + displayContent.replace('[ตอบแบบสอบถาม]', '').trim();
    }
        
    return `
        <div class="message-avatar"${avatarStyle}>${avatar}</div>
        <div class="message-content">
            <div class="message-bubble">${formatMessageText(displayContent)}</div>
        </div>
    `;
}

// --- Rich Markdown Parser ---
function formatMessageText(text) {
    if (!text) return '';

    // Escape HTML first
    let html = escapeHtml(text);

    // Code blocks (``` ... ```)
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
        return `<pre class="md-code-block"><code>${code.trim()}</code></pre>`;
    });
    html = html.replace(/```([\s\S]*?)```/g, (_, code) => {
        return `<pre class="md-code-block"><code>${code.trim()}</code></pre>`;
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code class="md-inline-code">$1</code>');

    // Headers (### > ## > #)
    html = html.replace(/^### (.+)$/gm, '<h4 class="md-h4">$1</h4>');
    html = html.replace(/^## (.+)$/gm, '<h3 class="md-h3">$1</h3>');
    html = html.replace(/^# (.+)$/gm, '<h2 class="md-h2">$1</h2>');

    // Bold + Italic
    html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, '<em>$1</em>');

    // Blockquote
    html = html.replace(/^&gt; (.+)$/gm, '<blockquote class="md-quote">$1</blockquote>');

    // Horizontal rule
    html = html.replace(/^---$/gm, '<hr class="md-hr">');

    // Unordered lists (- or •)
    html = html.replace(/^[\-•] (.+)$/gm, '<li class="md-li">$1</li>');
    html = html.replace(/((?:<li class="md-li">.*<\/li>\n?)+)/g, '<ul class="md-ul">$1</ul>');

    // Ordered lists
    html = html.replace(/^\d+\. (.+)$/gm, '<li class="md-oli">$1</li>');
    html = html.replace(/((?:<li class="md-oli">.*<\/li>\n?)+)/g, '<ol class="md-ol">$1</ol>');

    // Line breaks (but not inside block elements)
    html = html.replace(/\n/g, '<br>');

    // Clean up excessive <br> around block elements
    html = html.replace(/<br>\s*(<\/?(?:h[2-4]|ul|ol|li|pre|blockquote|hr))/g, '$1');
    html = html.replace(/(<\/(?:h[2-4]|ul|ol|pre|blockquote|hr)>)\s*<br>/g, '$1');

    return html;
}

// --- Typewriter Effect ---
function typewriterEffect(bubbleEl, text) {
    const words = text.split(/(\s+)/);
    let currentIdx = 0;
    const wordsPerTick = 2;
    const baseSpeed = 25;  // ms per tick

    function tick() {
        if (currentIdx >= words.length) {
            // Done — show final rendered text, remove cursor
            bubbleEl.innerHTML = formatMessageText(text);
            bubbleEl.classList.add('tw-done');
            scrollToBottom();
            return;
        }

        const end = Math.min(currentIdx + wordsPerTick, words.length);
        const partial = words.slice(0, end).join('');
        currentIdx = end;

        bubbleEl.innerHTML = formatMessageText(partial) + '<span class="tw-cursor">▍</span>';
        scrollToBottom();

        // Vary speed slightly for natural feel
        const jitter = Math.random() * 15;
        setTimeout(tick, baseSpeed + jitter);
    }

    // Small delay before starting
    setTimeout(tick, 150);
}

// --- Activity Timeline ---
function showActivityTimeline() {
    const el = document.createElement('div');
    el.className = 'message agent activity-timeline-wrapper';
    el.id = 'activityTimeline';
    el.innerHTML = `
        <div class="message-avatar" style="background: var(--gradient-accent); color: white; box-shadow: var(--shadow-glow);">✦</div>
        <div class="message-content">
            <div class="activity-timeline">
                <div class="activity-timeline-header">
                    <span class="activity-pulse-dot"></span>
                    <span class="activity-title">กำลังประมวลผล...</span>
                </div>
                <div class="activity-steps" id="activitySteps"></div>
            </div>
        </div>
    `;
    chatMessages.appendChild(el);
    scrollToBottom();
}

function addActivityStep(text) {
    const stepsContainer = document.getElementById('activitySteps');
    if (!stepsContainer) return;

    // Mark previous active step as completed
    const prevActive = stepsContainer.querySelector('.activity-step.active');
    if (prevActive) {
        prevActive.classList.remove('active');
        prevActive.classList.add('completed');
    }

    const step = document.createElement('div');
    step.className = 'activity-step active';
    step.setAttribute('data-tool', '');
    step.innerHTML = `<span class="step-text">${escapeHtml(text)}</span>`;
    stepsContainer.appendChild(step);
    scrollToBottom();
}

function addToolCode(toolName, code) {
    const stepsContainer = document.getElementById('activitySteps');
    if (!stepsContainer) return;

    // Find the last step (it should be the tool step we just added)
    const lastStep = stepsContainer.querySelector('.activity-step:last-child');
    if (!lastStep) return;

    // Create collapsible code block
    const codeWrapper = document.createElement('div');
    codeWrapper.className = 'tool-code-wrapper';
    codeWrapper.innerHTML = `
        <button class="tool-code-toggle" onclick="this.parentElement.classList.toggle('expanded')">
            <svg class="toggle-chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>
            <span>ดู Code ที่ Agent เรียกใช้</span>
        </button>
        <div class="tool-code-content">
            <pre class="tool-code-block">${escapeHtml(code)}</pre>
        </div>
    `;
    lastStep.appendChild(codeWrapper);
    scrollToBottom();
}

function addThinkingLog(text) {
    const stepsContainer = document.getElementById('activitySteps');
    if (!stepsContainer) return;

    let logViewer = stepsContainer.querySelector('.thinking-log-viewer:last-child');
    let contentDiv = null;
    
    if (!logViewer || logViewer.classList.contains('closed-log')) {
        logViewer = document.createElement('div');
        logViewer.className = 'thinking-log-viewer expanded';
        logViewer.innerHTML = `
            <div class="thinking-log-header" onclick="this.parentElement.classList.toggle('expanded')">
                <svg class="chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>
                <span>Agent Thinking...</span>
            </div>
            <div class="thinking-log-content"></div>
        `;
        stepsContainer.appendChild(logViewer);
        contentDiv = logViewer.querySelector('.thinking-log-content');
    } else {
        contentDiv = logViewer.querySelector('.thinking-log-content');
    }

    contentDiv.textContent += text;
    scrollToBottom();
}

function addToolResult(toolName, status) {
    const stepsContainer = document.getElementById('activitySteps');
    if (!stepsContainer) return;

    const logViewer = stepsContainer.querySelector('.thinking-log-viewer.expanded');
    if (logViewer) {
        logViewer.classList.remove('expanded');
        logViewer.classList.add('closed-log');
    }

    const step = document.createElement('div');
    step.className = `tool-execution-status ${status === 'running' ? 'active' : ''}`;
    step.innerHTML = `
        <i><svg class="tool-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg></i>
        <span>Tool ${status}: <strong>${escapeHtml(toolName)}</strong></span>
    `;
    stepsContainer.appendChild(step);
    scrollToBottom();
}

function removeActivityTimeline() {
    const el = document.getElementById('activityTimeline');
    if (el) {
        el.style.animation = 'fadeOut 0.3s ease forwards';
        setTimeout(() => el.remove(), 300);
    }
}

// Legacy fallback wrappers
function showTypingIndicator() { showActivityTimeline(); }
function hideTypingIndicator() { removeActivityTimeline(); }

// --- Send Message ---
async function sendMessage(text, isHidden = false) {
    if (!text.trim() && pendingFiles.length === 0) return;
    if (!currentSessionId) {
        await createNewSession();
    }

    if (!isHidden) {
        const displayText = pendingFiles.length > 0
            ? `📎 ${pendingFiles.map(f => f.name).join(', ')}${text.trim() ? '\n' + text : ''}`
            : text;
        appendMessage('user', displayText, 'text');
    }
    messageInput.value = '';
    autoResize();
    updateSendButton();

    setLoading(true);
    showActivityTimeline();

    try {
        // Upload files and collect results
        let fileContext = '';
        let imageRefs = [];
        if (pendingFiles.length > 0) {
            const extractions = [];
            for (const file of pendingFiles) {
                const formData = new FormData();
                formData.append('file', file);
                const uploadRes = await fetch('/api/upload', { method: 'POST', body: formData });
                if (!uploadRes.ok) {
                    const err = await uploadRes.json().catch(() => ({}));
                    throw new Error(err.detail || `อัปโหลดไฟล์ ${file.name} ล้มเหลว`);
                }
                const result = await uploadRes.json();
                if (result.type === 'image') {
                    imageRefs.push(result.image_ref);
                } else {
                    extractions.push(`[ไฟล์: ${result.filename}]${result.truncated ? ' (ตัดเนื้อหาส่วนเกิน)' : ''}\n${result.extracted_text}`);
                }
            }
            fileContext = extractions.join('\n\n---\n\n');
            clearPendingFiles();
        }

        const defaultMsg = imageRefs.length > 0
            ? 'กรุณาดูและวิเคราะห์ภาพที่แนบมา'
            : 'กรุณาอ่านและวิเคราะห์ไฟล์ที่แนบมา';

        // --- SSE Streaming ---
        const sseBody = {
            session_id: currentSessionId,
            message: text || defaultMsg,
            file_context: fileContext,
            image_refs: imageRefs,
        };

        const response = await fetch('/api/chat/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(sseBody),
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let finalReply = '';
        let finalMsgType = 'text';
        const toolCodes = []; // Collect tool calls for persistent display

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // keep incomplete line in buffer

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const jsonStr = line.slice(6).trim();
                if (!jsonStr) continue;

                try {
                    const event = JSON.parse(jsonStr);

                    if (event.type === 'step') {
                        addActivityStep(event.text);
                    } else if (event.type === 'thinking') {
                        addThinkingLog(event.text);
                    } else if (event.type === 'tool_result') {
                        addToolResult(event.tool, event.status);
                    } else if (event.type === 'tool_code') {
                        addToolCode(event.tool, event.code);
                        toolCodes.push({ tool: event.tool, code: event.code });
                    } else if (event.type === 'final') {
                        finalReply = event.text;
                        finalMsgType = event.msg_type || 'text';
                    } else if (event.type === 'error') {
                        removeActivityTimeline();
                        appendMessage('agent', `❌ ${event.text}`, 'text');
                        return;
                    } else if (event.type === 'done') {
                        // Stream complete
                    }
                } catch (e) {
                    // skip malformed JSON
                }
            }
        }

        // Remove timeline and show final response
        removeActivityTimeline();
        if (finalReply) {
            appendMessage('agent', finalReply, finalMsgType);

            // Append persistent Execution Log if tools were used
            if (toolCodes.length > 0) {
                appendExecutionLog(toolCodes);
            }

            if (finalMsgType === 'mcq' || finalMsgType === 'survey') {
                try {
                    const mcqData = JSON.parse(finalReply);
                    setTimeout(() => openMcqModal(mcqData), 400);
                } catch {
                    // Not valid JSON
                }
            }
        }

        await loadSessions();
    } catch (err) {
        removeActivityTimeline();
        appendMessage('agent', `❌ เกิดข้อผิดพลาด: ${err.message}`, 'text');
    } finally {
        setLoading(false);
    }
}

/**
 * Render a persistent Execution Log card in chat.
 * Shows all tool calls with their arguments in collapsible code blocks.
 */
function appendExecutionLog(toolCodes) {
    const container = document.createElement('div');
    container.className = 'message agent execution-log-message';
    
    const codeItems = toolCodes.map((tc, i) => {
        const id = `exec-code-${Date.now()}-${i}`;
        return `
            <div class="exec-log-item" id="item-${id}">
                <button class="exec-log-toggle" onclick="document.getElementById('item-${id}').classList.toggle('expanded')">
                    <svg class="toggle-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>
                    <span class="exec-log-tool-name">${escapeHtml(tc.tool)}</span>
                </button>
                <div class="exec-log-code">
                    <pre>${escapeHtml(tc.code)}</pre>
                </div>
            </div>`;
    }).join('');

    container.innerHTML = `
        <div class="message-avatar" style="background: var(--bg-tertiary); border: 1px solid var(--border-hover); color: var(--text-tertiary); font-size: 0.8rem;">⚙</div>
        <div class="message-content">
            <div class="exec-log-card">
                <div class="exec-log-header">
                    <span class="exec-log-icon">🔧</span>
                    <span class="exec-log-title">Execution Log</span>
                    <span class="exec-log-count">${toolCodes.length} tool${toolCodes.length > 1 ? 's' : ''} used</span>
                </div>
                <div class="exec-log-items">${codeItems}</div>
            </div>
        </div>
    `;
    chatMessages.appendChild(container);
    scrollToBottom();
}

// --- MCQ & Survey Modal ---
let selectedAnswers = {}; // Map of qId -> selected key or text

function openMcqModal(data) {
    currentMcqData = data;
    selectedAnswers = {}; // Reset
    currentSurveyStep = 0; // Reset step

    const surveyTitle = document.getElementById('surveyTitle');
    const questionsContainer = document.getElementById('surveyQuestionsContainer');
    
    questionsContainer.innerHTML = '';
    mcqResult.style.display = 'none';
    btnSubmitAnswer.style.display = '';
    btnSubmitAnswer.disabled = true;
    btnCloseResult.style.display = 'none';
    
    const isSurvey = data.type === 'survey';
    if (isSurvey) {
        btnCloseModal.style.display = 'none';
        surveyTitle.style.display = 'block';
        surveyTitle.textContent = data.title || 'ทำความรู้จักกันสักนิด';
        
        data.questions.forEach((q, qIndex) => {
            const qDiv = document.createElement('div');
            qDiv.className = 'survey-question-block';
            qDiv.style.marginBottom = '20px';
            qDiv.style.display = qIndex === 0 ? 'block' : 'none'; // Only show first question initially
            
            const qText = document.createElement('p');
            qText.className = 'mcq-question';
            qText.textContent = `${qIndex + 1}. ${q.question}`;
            qDiv.appendChild(qText);
            
            if (q.inputType === 'text' || q.inputType === 'textarea') {
                const textContainer = document.createElement('div');
                textContainer.className = 'survey-custom-input-container';
                textContainer.style.display = 'block';
                textContainer.style.marginTop = '12px';
                
                let input;
                if (q.inputType === 'textarea') {
                    input = document.createElement('textarea');
                    input.rows = 4;
                } else {
                    input = document.createElement('input');
                    input.type = 'text';
                }
                input.className = 'survey-custom-input';
                input.placeholder = 'โปรดระบุรายละเอียด...';
                input.style.width = '100%';
                input.style.boxSizing = 'border-box';
                input.addEventListener('input', checkSurveyCompletion);
                
                textContainer.appendChild(input);
                qDiv.appendChild(textContainer);
            } else {
                const optionsDiv = document.createElement('div');
                optionsDiv.className = 'mcq-options';
                
                const customInputContainer = document.createElement('div');
                customInputContainer.className = 'survey-custom-input-container';
                customInputContainer.style.display = 'none';
                customInputContainer.style.marginTop = '12px';
                
                const customInput = document.createElement('input');
                customInput.type = 'text';
                customInput.className = 'survey-custom-input';
                customInput.placeholder = 'โปรดระบุรายละเอียดเพิ่มเติม...';
                customInput.style.width = '100%';
                customInput.style.boxSizing = 'border-box';
                customInputContainer.appendChild(customInput);
                
                q.options.forEach(opt => {
                    const btn = document.createElement('button');
                    btn.className = 'mcq-option';
                    btn.innerHTML = `
                        <span class="option-key">${opt.key}</span>
                        <span class="option-text">${escapeHtml(opt.text)}</span>
                    `;
                    btn.addEventListener('click', () => {
                        optionsDiv.querySelectorAll('.mcq-option').forEach(el => el.classList.remove('selected'));
                        btn.classList.add('selected');
                        
                        if (opt.key.toLowerCase() === 'other' || opt.text.includes('อื่นๆ')) {
                            customInputContainer.style.display = 'block';
                            customInput.focus();
                        } else {
                            customInputContainer.style.display = 'none';
                            customInput.value = '';
                        }
                        checkSurveyCompletion();
                    });
                    optionsDiv.appendChild(btn);
                });
                
                customInput.addEventListener('input', checkSurveyCompletion);
                
                qDiv.appendChild(optionsDiv);
                qDiv.appendChild(customInputContainer);
            }
            
            questionsContainer.appendChild(qDiv);
        });
        btnNextQuestion.style.display = 'none';
        
    } else {
        btnCloseModal.style.display = '';
        surveyTitle.style.display = 'none';
        btnNextQuestion.style.display = 'none';
        
        const qText = document.createElement('p');
        qText.className = 'mcq-question';
        qText.textContent = data.question;
        questionsContainer.appendChild(qText);
        
        const optionsDiv = document.createElement('div');
        optionsDiv.className = 'mcq-options';
        
        data.options.forEach((opt) => {
            const btn = document.createElement('button');
            btn.className = 'mcq-option';
            btn.innerHTML = `
                <span class="option-key">${opt.key}</span>
                <span class="option-text">${escapeHtml(opt.text)}</span>
            `;
            btn.addEventListener('click', () => {
                optionsDiv.querySelectorAll('.mcq-option').forEach((el) => el.classList.remove('selected'));
                btn.classList.add('selected');
                selectedAnswers['single'] = opt.key;
                btnSubmitAnswer.disabled = false;
            });
            optionsDiv.appendChild(btn);
        });
        questionsContainer.appendChild(optionsDiv);
    }

    mcqModal.classList.add('active');
}

function checkSurveyCompletion() {
    if (!currentMcqData) return;

    if (currentMcqData.type === 'survey') {
        const blocks = document.querySelectorAll('.survey-question-block');
        const currentBlock = blocks[currentSurveyStep];
        if (!currentBlock) return;

        let answeredCurrent = false;
        const qData = currentMcqData.questions[currentSurveyStep];
        
        if (qData.inputType === 'text' || qData.inputType === 'textarea') {
            const input = currentBlock.querySelector('.survey-custom-input');
            if (input && input.value.trim()) {
                answeredCurrent = true;
            }
        } else {
            const selectedBtn = currentBlock.querySelector('.mcq-option.selected');
            if (selectedBtn) {
                answeredCurrent = true;
                const customContainer = currentBlock.querySelector('.survey-custom-input-container');
                if (customContainer && customContainer.style.display === 'block') {
                    const input = customContainer.querySelector('input');
                    if (!input.value.trim()) {
                        answeredCurrent = false;
                    }
                }
            }
        }

        if (currentSurveyStep < blocks.length - 1) {
            // Not the last question, show "Next"
            btnNextQuestion.style.display = '';
            btnNextQuestion.disabled = !answeredCurrent;
            btnSubmitAnswer.style.display = 'none';
        } else {
            // Last question, show "Submit"
            btnNextQuestion.style.display = 'none';
            btnSubmitAnswer.style.display = '';
            btnSubmitAnswer.disabled = !answeredCurrent;
        }
    } else {
        // Single MCQ logic handled on click
    }
}

function submitAnswer() {
    if (btnSubmitAnswer.disabled || !currentMcqData) return;

    if (currentMcqData.type === 'survey') {
        const blocks = document.querySelectorAll('.survey-question-block');
        let finalAnswers = [];
        
        blocks.forEach((block, idx) => {
            const qData = currentMcqData.questions[idx];
            let answerText = '';
            
            if (qData.inputType === 'text' || qData.inputType === 'textarea') {
                const input = block.querySelector('.survey-custom-input');
                if (input) {
                    answerText = input.value.trim();
                }
            } else {
                const selectedBtn = block.querySelector('.mcq-option.selected');
                const key = selectedBtn.querySelector('.option-key').textContent;
                
                answerText = key;
                const selectedOpt = qData.options.find(o => o.key === key);
                if (selectedOpt) answerText = selectedOpt.text;
                
                const customContainer = block.querySelector('.survey-custom-input-container');
                if (customContainer && customContainer.style.display === 'block') {
                    const input = customContainer.querySelector('input');
                    if (input.value.trim()) {
                        answerText = input.value.trim();
                    }
                }
            }
            
            finalAnswers.push(`**คำถาม:** ${qData.question}\n**คำตอบ:** ${answerText}\n`);
        });

        mcqModal.classList.remove('active');
        sendMessage(`[ตอบแบบสอบถาม]\n` + finalAnswers.join('\n'));
        btnCloseModal.style.display = '';
        return;
    }

    const selectedKey = selectedAnswers['single'];
    const isCorrect = selectedKey === currentMcqData.correct_answer;

    const optionsDiv = document.querySelector('.mcq-options');
    optionsDiv.querySelectorAll('.mcq-option').forEach((el) => {
        el.classList.add('disabled');
        const key = el.querySelector('.option-key').textContent;
        if (key === currentMcqData.correct_answer) {
            el.classList.add('correct');
        } else if (key === selectedKey && !isCorrect) {
            el.classList.add('incorrect');
        }
    });

    mcqResult.style.display = 'block';
    mcqResult.className = `mcq-result ${isCorrect ? 'correct' : 'incorrect'}`;
    resultIcon.textContent = isCorrect ? '🎉' : '💡';
    resultText.textContent = isCorrect ? 'ถูกต้อง! เก่งมาก!' : `ไม่ถูกต้อง — คำตอบที่ถูกคือ ${currentMcqData.correct_answer}`;
    resultExplanation.textContent = currentMcqData.explanation || '';

    btnSubmitAnswer.style.display = 'none';
    btnCloseResult.style.display = '';
}

function closeModal() {
    if (currentMcqData && currentMcqData.type === 'survey') {
        return; // Disable closing for surveys to force onboarding
    }
    mcqModal.classList.remove('active');
    currentMcqData = null;
    selectedAnswers = {};
}

// --- Utilities ---
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function scrollToBottom() {
    requestAnimationFrame(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    });
}

function autoResize() {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + 'px';
}

function updateSendButton() {
    btnSend.disabled = !messageInput.value.trim() && pendingFiles.length === 0;
}

// --- File Upload ---
const IMAGE_EXTS = ['png', 'jpg', 'jpeg', 'gif', 'webp'];
const DOC_EXTS = ['txt', 'pdf', 'docx', 'xlsx', 'csv'];
const ALL_ALLOWED = [...DOC_EXTS, ...IMAGE_EXTS];

function handleFileSelect(files) {
    for (const file of files) {
        const ext = file.name.split('.').pop().toLowerCase();
        if (!ALL_ALLOWED.includes(ext)) {
            alert(`ไฟล์ .${ext} ไม่รองรับ\nรองรับ: ${ALL_ALLOWED.map(e => '.' + e).join(', ')}`);
            continue;
        }
        if (file.size > 10 * 1024 * 1024) {
            alert(`ไฟล์ ${file.name} ใหญ่เกิน 10 MB`);
            continue;
        }
        // Create preview URL for images
        if (IMAGE_EXTS.includes(ext)) {
            file._previewUrl = URL.createObjectURL(file);
        }
        pendingFiles.push(file);
    }
    renderFilePreview();
    updateSendButton();
}

function renderFilePreview() {
    if (pendingFiles.length === 0) {
        filePreview.style.display = 'none';
        filePreview.innerHTML = '';
        return;
    }
    filePreview.style.display = 'flex';
    filePreview.innerHTML = pendingFiles.map((f, i) => {
        const ext = f.name.split('.').pop().toLowerCase();
        const isImage = IMAGE_EXTS.includes(ext);
        const size = f.size < 1024 ? `${f.size} B`
            : f.size < 1048576 ? `${(f.size / 1024).toFixed(1)} KB`
            : `${(f.size / 1048576).toFixed(1)} MB`;

        if (isImage && f._previewUrl) {
            return `
                <div class="file-chip file-chip-image">
                    <img src="${f._previewUrl}" class="file-chip-thumb" alt="preview" />
                    <div class="file-chip-info">
                        <span class="file-chip-name">${escapeHtml(f.name)}</span>
                        <span class="file-chip-size">${size}</span>
                    </div>
                    <button class="file-chip-remove" data-idx="${i}" title="ลบ">&times;</button>
                </div>
            `;
        }

        const icons = { txt: '📝', pdf: '📕', docx: '📄', xlsx: '📊', csv: '📋' };
        const icon = icons[ext] || '📎';
        return `
            <div class="file-chip">
                <span class="file-chip-icon">${icon}</span>
                <span class="file-chip-name">${escapeHtml(f.name)}</span>
                <span class="file-chip-size">${size}</span>
                <button class="file-chip-remove" data-idx="${i}" title="ลบ">&times;</button>
            </div>
        `;
    }).join('');

    filePreview.querySelectorAll('.file-chip-remove').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const idx = parseInt(e.target.dataset.idx);
            // Revoke object URL if it was an image
            if (pendingFiles[idx]._previewUrl) {
                URL.revokeObjectURL(pendingFiles[idx]._previewUrl);
            }
            pendingFiles.splice(idx, 1);
            renderFilePreview();
            updateSendButton();
        });
    });
}

function clearPendingFiles() {
    pendingFiles = [];
    fileInput.value = '';
    renderFilePreview();
}

// --- Event Listeners ---
btnSend.addEventListener('click', () => sendMessage(messageInput.value));

messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage(messageInput.value);
    }
});

messageInput.addEventListener('input', () => {
    autoResize();
    updateSendButton();
});

btnNewChat.addEventListener('click', createNewSession);

btnAttach.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
        handleFileSelect(fileInput.files);
        fileInput.value = '';  // reset so same file can be re-selected
    }
});

btnToggle.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
});

btnDelete.addEventListener('click', deleteCurrentSession);

btnUserProfile.addEventListener('click', async () => {
    profileSummaryContainer.innerHTML = '<div style="text-align: center; padding: 20px;"><div class="loading-dots" style="justify-content: center;"><span></span><span></span><span></span></div><p style="margin-top:10px; color:var(--text-muted);">AI กำลังวิเคราะห์ข้อมูลของคุณ...</p></div>';
    profileModal.classList.add('active');
    
    try {
        const response = await fetch('/api/profile_summary');
        if (response.ok) {
            const data = await response.json();
            profileSummaryContainer.innerHTML = data.summary;
        } else {
            profileSummaryContainer.innerHTML = '<p style="color: var(--error-color);">ไม่สามารถโหลดข้อมูลได้</p>';
        }
    } catch (err) {
        console.error("Error fetching profile summary:", err);
        profileSummaryContainer.innerHTML = '<p style="color: var(--error-color);">ไม่สามารถโหลดข้อมูลได้</p>';
    }
});

btnCloseProfileModal.addEventListener('click', () => {
    profileModal.classList.remove('active');
});

btnSubmitAnswer.addEventListener('click', submitAnswer);
btnNextQuestion.addEventListener('click', () => {
    if (!currentMcqData || currentMcqData.type !== 'survey') return;
    
    const blocks = document.querySelectorAll('.survey-question-block');
    if (currentSurveyStep < blocks.length - 1) {
        blocks[currentSurveyStep].style.display = 'none'; // Hide current
        currentSurveyStep++;
        blocks[currentSurveyStep].style.display = 'block'; // Show next
        checkSurveyCompletion();
    }
});

btnCloseModal.addEventListener('click', closeModal);
btnCloseResult.addEventListener('click', closeModal);
mcqModal.addEventListener('click', (e) => {
    if (e.target === mcqModal && !(currentMcqData && currentMcqData.type === 'survey')) {
        closeModal();
    }
});

function showConfirmModal(message) {
    return new Promise((resolve) => {
        const confirmModal = document.getElementById('confirmModal');
        const confirmMessage = document.getElementById('confirmMessage');
        const btnConfirmCancel = document.getElementById('btnConfirmCancel');
        const btnConfirmOk = document.getElementById('btnConfirmOk');

        if (!confirmModal || !confirmMessage || !btnConfirmCancel || !btnConfirmOk) {
            resolve(confirm(message));
            return;
        }

        confirmMessage.textContent = message;
        confirmModal.classList.add('active');

        const cleanup = () => {
            confirmModal.classList.remove('active');
            btnConfirmCancel.removeEventListener('click', onCancel);
            btnConfirmOk.removeEventListener('click', onOk);
        };

        const onCancel = () => {
            cleanup();
            resolve(false);
        };

        const onOk = () => {
            cleanup();
            resolve(true);
        };

        btnConfirmCancel.addEventListener('click', onCancel);
        btnConfirmOk.addEventListener('click', onOk);
    });
}

// Settings Logic
const settingsModal = document.getElementById('settingsModal');
const btnOpenSettings = document.getElementById('btnOpenSettings');
const btnCloseSettingsModal = document.getElementById('btnCloseSettingsModal');
const btnClearAllChats = document.getElementById('btnClearAllChats');
const btnClearProfileData = document.getElementById('btnClearProfileData');
const btnExportData = document.getElementById('btnExportData');

if (btnOpenSettings) {
    btnOpenSettings.addEventListener('click', () => {
        settingsModal.classList.add('active');
    });
}

if (btnCloseSettingsModal) {
    btnCloseSettingsModal.addEventListener('click', () => {
        settingsModal.classList.remove('active');
    });
}

settingsModal.addEventListener('click', (e) => {
    if (e.target === settingsModal) {
        settingsModal.classList.remove('active');
    }
});

if (btnClearAllChats) {
    btnClearAllChats.addEventListener('click', async () => {
        const confirmed = await showConfirmModal('คุณแน่ใจหรือไม่ว่าต้องการลบประวัติการสนทนาทั้งหมด? (การกระทำนี้กู้คืนไม่ได้)');
        if (!confirmed) return;
        try {
            await api.del('/api/sessions/all');
            currentSessionId = null;
            chatTitle.textContent = 'Life Coach AI';
            clearMessages();
            showWelcome(true);
            await loadSessions();
            settingsModal.classList.remove('active');
        } catch (e) {
            alert('ไม่สามารถลบประวัติแชทได้: ' + e.message);
        }
    });
}

if (btnClearProfileData) {
    btnClearProfileData.addEventListener('click', async () => {
        const confirmed = await showConfirmModal('คุณแน่ใจหรือไม่ว่าต้องการล้างข้อมูลส่วนตัวทั้งหมด? ระบบจะเริ่มทำความรู้จักคุณใหม่');
        if (!confirmed) return;
        try {
            await api.del('/api/profile');
            // delete current session and reload
            if (currentSessionId) {
                await api.del(`/api/sessions/${currentSessionId}`);
                currentSessionId = null;
            }
            chatTitle.textContent = 'Life Coach AI';
            clearMessages();
            showWelcome(true);
            await loadSessions();
            settingsModal.classList.remove('active');
            
            // force onboarding
            openMcqModal(defaultOnboardingSurvey);
        } catch (e) {
            alert('ไม่สามารถล้างข้อมูลได้: ' + e.message);
        }
    });
}

if (btnExportData) {
    btnExportData.addEventListener('click', async () => {
        try {
            const data = await api.get('/api/export');
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `life-coach-export-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch (e) {
            alert('ไม่สามารถดาวน์โหลดข้อมูลได้: ' + e.message);
        }
    });
}

document.querySelectorAll('.welcome-card').forEach((card) => {
    card.addEventListener('click', () => {
        const prompt = card.dataset.prompt;
        if (prompt) {
            messageInput.value = prompt;
            sendMessage(prompt);
        }
    });
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && mcqModal.classList.contains('active')) {
        closeModal();
    }
});

// --- Initialize ---
(async function init() {
    await loadSessions();
    
    try {
        const data = await api.get('/api/profile');
        if (!data.profile || data.profile.length === 0) {
            // Trigger onboarding regardless of messages because we want it to pop up immediately
            openMcqModal(defaultOnboardingSurvey);
        }
    } catch (e) {
        console.error("Failed to fetch profile", e);
    }
})();
