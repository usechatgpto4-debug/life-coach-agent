/**
 * Life Coach AI — Frontend Application
 * Handles chat, sessions, and MCQ modal interactions.
 */

// --- State ---
let currentSessionId = null;
let currentMcqData = null;
let selectedAnswer = null;

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
    if (!confirm('ลบแชตนี้?')) return;
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
    messages.forEach((m) => appendMessage(m.role, m.content, m.msg_type, false));
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

    if (msgType === 'mcq' && role === 'agent') {
        let mcqData;
        try {
            mcqData = JSON.parse(content);
        } catch {
            msgEl.innerHTML = buildTextMessage(avatarContent, content, role);
            chatMessages.appendChild(msgEl);
            return;
        }

        msgEl.innerHTML = `
            <div class="message-avatar">${avatarContent}</div>
            <div class="message-content">
                <div class="mcq-chat-card" data-mcq='${escapeHtml(content)}'>
                    <div class="mcq-chat-label">📝 แบบทดสอบ</div>
                    <div class="mcq-chat-preview">${escapeHtml(mcqData.question)}</div>
                    <div class="mcq-chat-hint">คลิกเพื่อเริ่มทำข้อสอบ →</div>
                </div>
            </div>
        `;

        const card = msgEl.querySelector('.mcq-chat-card');
        card.addEventListener('click', () => openMcqModal(mcqData));
    } else {
        msgEl.innerHTML = buildTextMessage(avatarContent, content, role);
    }

    if (animate) {
        msgEl.style.animation = 'msgSlideIn 0.3s ease';
    }

    chatMessages.appendChild(msgEl);
    scrollToBottom();
}

function buildTextMessage(avatar, content, role) {
    return `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <div class="message-bubble">${formatMessageText(content)}</div>
        </div>
    `;
}

function formatMessageText(text) {
    let html = escapeHtml(text);
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\n/g, '<br>');
    return html;
}

// --- Typing Indicator ---
function showTypingIndicator() {
    const el = document.createElement('div');
    el.className = 'typing-indicator';
    el.id = 'typingIndicator';
    el.innerHTML = `
        <div class="message-avatar" style="background: var(--gradient-accent); color: white; box-shadow: var(--shadow-glow);">✦</div>
        <div class="typing-dots"><span></span><span></span><span></span></div>
    `;
    chatMessages.appendChild(el);
    scrollToBottom();
}

function hideTypingIndicator() {
    const el = document.getElementById('typingIndicator');
    if (el) el.remove();
}

// --- Send Message ---
async function sendMessage(text) {
    if (!text.trim()) return;
    if (!currentSessionId) {
        await createNewSession();
    }

    appendMessage('user', text, 'text');
    messageInput.value = '';
    autoResize();
    updateSendButton();

    setLoading(true);
    showTypingIndicator();

    try {
        const response = await api.post('/api/chat', {
            session_id: currentSessionId,
            message: text,
        });

        hideTypingIndicator();
        appendMessage('agent', response.reply, response.msg_type);

        if (response.msg_type === 'mcq') {
            try {
                const mcqData = JSON.parse(response.reply);
                setTimeout(() => openMcqModal(mcqData), 400);
            } catch {
                // Not valid JSON
            }
        }

        await loadSessions();
    } catch (err) {
        hideTypingIndicator();
        appendMessage('agent', `❌ เกิดข้อผิดพลาด: ${err.message}`, 'text');
    } finally {
        setLoading(false);
    }
}

// --- MCQ Modal ---
function openMcqModal(data) {
    currentMcqData = data;
    selectedAnswer = null;

    mcqQuestion.textContent = data.question;
    mcqOptions.innerHTML = '';
    mcqResult.style.display = 'none';
    btnSubmitAnswer.style.display = '';
    btnSubmitAnswer.disabled = true;
    btnCloseResult.style.display = 'none';

    data.options.forEach((opt) => {
        const btn = document.createElement('button');
        btn.className = 'mcq-option';
        btn.innerHTML = `
            <span class="option-key">${opt.key}</span>
            <span class="option-text">${escapeHtml(opt.text)}</span>
        `;
        btn.addEventListener('click', () => selectOption(opt.key, btn));
        mcqOptions.appendChild(btn);
    });

    mcqModal.classList.add('active');
}

function selectOption(key, btnEl) {
    selectedAnswer = key;
    mcqOptions.querySelectorAll('.mcq-option').forEach((el) => el.classList.remove('selected'));
    btnEl.classList.add('selected');
    btnSubmitAnswer.disabled = false;
}

function submitAnswer() {
    if (!selectedAnswer || !currentMcqData) return;

    const isCorrect = selectedAnswer === currentMcqData.correct_answer;

    mcqOptions.querySelectorAll('.mcq-option').forEach((el) => {
        el.classList.add('disabled');
        const key = el.querySelector('.option-key').textContent;
        if (key === currentMcqData.correct_answer) {
            el.classList.add('correct');
        } else if (key === selectedAnswer && !isCorrect) {
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
    mcqModal.classList.remove('active');
    currentMcqData = null;
    selectedAnswer = null;
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
    btnSend.disabled = !messageInput.value.trim();
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

btnToggle.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
});

btnDelete.addEventListener('click', deleteCurrentSession);

btnSubmitAnswer.addEventListener('click', submitAnswer);
btnCloseModal.addEventListener('click', closeModal);
btnCloseResult.addEventListener('click', closeModal);
mcqModal.addEventListener('click', (e) => {
    if (e.target === mcqModal) closeModal();
});

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
})();
