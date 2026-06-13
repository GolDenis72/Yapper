// app.js — Yapper frontend logic

const WS_URL = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`;
let ws = null;
let mediaRecorder = null;
let audioChunks = [];
let sessionActive = false;
let timerInterval = null;
let sessionSeconds = 0;
let lastUserText = "";

// --- DOM refs ---
const $ = id => document.getElementById(id);
const indWhisper = $("ind-whisper");
const indOllama  = $("ind-ollama");
const indMic     = $("ind-mic");
const indWs      = $("ind-ws");
const profileSetup = $("profile-setup");
const mainUi     = $("main-ui");
const btnStart   = $("btn-start");
const btnStop    = $("btn-stop");
const btnMic     = $("btn-mic");
const btnVocab   = $("btn-vocab");
const btnProgress = $("btn-progress");
const btnCloseProgress = $("btn-close-progress");
const messages   = $("messages");
const micStatus  = $("mic-status");
const topicSelect = $("topic-select");
const sessionInfo = $("session-info");
const sessionTopic = $("session-topic");
const sessionTime  = $("session-time");
const micArea    = $("mic-area");
const progressPanel = $("progress-panel");
const progressText  = $("progress-text");

// --- WebSocket ---
function connect() {
  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    setIndicator(indWs, true, "Server");
  };

  ws.onclose = () => {
    setIndicator(indWs, false, "Server");
    setTimeout(connect, 3000);
  };

  ws.onmessage = async (e) => {
    const msg = JSON.parse(e.data);
    await handleMessage(msg);
  };
}

async function handleMessage(msg) {
  switch (msg.type) {

    case "status":
      setIndicator(indWhisper, msg.whisper, "Whisper");
      setIndicator(indOllama, msg.ollama, "Ollama");
      if (!msg.profile) {
        profileSetup.classList.remove("hidden");
        mainUi.classList.add("hidden");
      } else {
        profileSetup.classList.add("hidden");
        mainUi.classList.remove("hidden");
      }
      break;

    case "profile_saved":
      profileSetup.classList.add("hidden");
      mainUi.classList.remove("hidden");
      loadTopics();
      break;

    case "session_started":
      sessionActive = true;
      btnStart.classList.add("hidden");
      btnStop.classList.remove("hidden");
      micArea.classList.remove("hidden");
      sessionInfo.classList.remove("hidden");
      sessionTopic.textContent = `Topic: ${msg.topic}`;
      sessionSeconds = 0;
      timerInterval = setInterval(updateTimer, 1000);
      addMessage("system", `Session started. Topic: ${msg.topic}`);
      break;

    case "session_ended":
      sessionActive = false;
      btnStart.classList.remove("hidden");
      btnStop.classList.add("hidden");
      micArea.classList.add("hidden");
      clearInterval(timerInterval);
      addMessage("system", `Session ended. Duration: ${msg.duration} min. Next topic: ${msg.next_topic}`);
      break;

    case "assistant_message":
      addMessage("assistant", msg.text);
      if (msg.audio) {
        await playAudio(msg.audio);
      }
      micStatus.textContent = "Your turn — hold the button to speak";
      break;

    case "user_message":
      addMessage("user", msg.text);
      lastUserText = msg.text;
      break;

    case "status_text":
      micStatus.textContent = msg.text;
      break;

    case "topic_changed":
      sessionTopic.textContent = `Topic: ${msg.topic}`;
      addMessage("system", `Topic changed to: ${msg.topic}`);
      break;

    case "vocab_flagged":
      addMessage("system", `📝 Vocabulary gap flagged: "${msg.context}"`);
      break;

    case "assessment_started":
      addMessage("system", "Starting level assessment. Just have a natural conversation!");
      break;

    case "assessment_done":
      addMessage("system", `✅ Assessment complete! Your level: ${msg.level}`);
      break;

    case "progress":
      progressText.textContent = msg.report;
      progressPanel.classList.remove("hidden");
      break;

    case "error":
      addMessage("system", `❌ Error: ${msg.message}`);
      break;
  }
}

// --- Audio recording ---
async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    setIndicator(indMic, true, "Mic");
    micStatus.textContent = "Recording...";
    btnMic.classList.add("recording");

    audioChunks = [];
    mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });

    mediaRecorder.ondataavailable = e => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop());
      setIndicator(indMic, false, "Mic");
      btnMic.classList.remove("recording");

      const blob = new Blob(audioChunks, { type: "audio/webm" });
      const arrayBuffer = await blob.arrayBuffer();
      const base64 = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));

      micStatus.textContent = "Processing...";
      ws.send(JSON.stringify({ type: "audio_chunk", data: base64 }));
    };

    mediaRecorder.start();
  } catch (err) {
    micStatus.textContent = `Mic error: ${err.message}`;
    setIndicator(indMic, false, "Mic");
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop();
  }
}

// --- Audio playback ---
async function playAudio(base64) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  const blob = new Blob([bytes], { type: "audio/mpeg" });
  const url = URL.createObjectURL(blob);
  const audio = new Audio(url);
  return new Promise(resolve => {
    audio.onended = resolve;
    audio.play();
  });
}

// --- UI helpers ---
function setIndicator(el, ok, label) {
  el.textContent = `${ok ? "🟢" : "🔴"} ${label}`;
}

function addMessage(role, text) {
  const div = document.createElement("div");
  div.className = `message ${role}`;
  const label = role === "assistant" ? "Yapper" : role === "user" ? "You" : "System";
  div.innerHTML = `<div class="label">${label}</div><div>${text}</div>`;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

function updateTimer() {
  sessionSeconds++;
  const m = Math.floor(sessionSeconds / 60).toString().padStart(2, "0");
  const s = (sessionSeconds % 60).toString().padStart(2, "0");
  sessionTime.textContent = `${m}:${s}`;
}

async function loadTopics() {
  try {
    const r = await fetch("/topics");
    const data = await r.json();
    topicSelect.innerHTML = data.topics.map(t =>
      `<option value="${t}">${t}</option>`
    ).join("");
  } catch (e) {}
}

// --- Event listeners ---
btnStart.onclick = () => {
  ws.send(JSON.stringify({
    type: "start_session",
    topic: topicSelect.value
  }));
};

btnStop.onclick = () => {
  ws.send(JSON.stringify({ type: "stop_session" }));
};

btnMic.addEventListener("mousedown", startRecording);
btnMic.addEventListener("mouseup", stopRecording);
btnMic.addEventListener("touchstart", e => { e.preventDefault(); startRecording(); });
btnMic.addEventListener("touchend", stopRecording);

btnVocab.onclick = () => {
  ws.send(JSON.stringify({ type: "vocab_flag", context: lastUserText }));
};

btnProgress.onclick = () => {
  ws.send(JSON.stringify({ type: "get_progress" }));
};

btnCloseProgress.onclick = () => {
  progressPanel.classList.add("hidden");
};

$("btn-save-profile").onclick = () => {
  const name = $("p-name").value.trim() || "Student";
  const duration = parseInt($("p-duration").value);
  const topics = $("p-topics").value.split(",").map(t => t.trim()).filter(Boolean);
  const prof = $("p-prof").value.split(",").map(t => t.trim()).filter(Boolean);

  ws.send(JSON.stringify({
    type: "save_profile",
    data: {
      name,
      session_duration_minutes: duration,
      preferred_topics: topics.length ? topics : ["travel", "daily life", "technology"],
      professional_topics: prof,
      native_language: "Russian",
      target_level: "B2",
    }
  }));
};

document.getElementById('micTestBtn').addEventListener('click', () => {
    window.open('/static/mictest/', 'mictest', 'width=900,height=700');
});

// F9 hotkey for vocab gap
document.addEventListener("keydown", e => {
  if (e.key === "F9") {
    ws.send(JSON.stringify({ type: "vocab_flag", context: lastUserText }));
  }
});

// --- Init ---
loadTopics();
connect();
