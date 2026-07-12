const API_BASE = "http://localhost:8000";
const STORAGE_KEY = "contact-center-auth";

const app = document.getElementById("app");

const state = {
  auth: loadAuth(),
  mediaRecorder: null,
  chunks: [],
  recordedBlob: null,
};

function loadAuth() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
  } catch {
    return null;
  }
}

function saveAuth(auth) {
  state.auth = auth;
  if (auth) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(auth));
  } else {
    localStorage.removeItem(STORAGE_KEY);
  }
}

function authHeaders() {
  if (!state.auth?.token) return {};
  return { Authorization: `Bearer ${state.auth.token}` };
}

function decodeBase64Utf8(value) {
  if (!value) return "";
  const bytes = Uint8Array.from(atob(value), (char) => char.charCodeAt(0));
  return new TextDecoder("utf-8").decode(bytes);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatStatusLabel(record) {
  if (record.status === "out_of_scope") return "Sin información";
  if (record.status === "answered") return "Respondida";
  if (record.status === "failed") return "Error";
  return record.status;
}

async function apiFetch(path, options = {}) {
  return fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options.headers || {}),
      ...authHeaders(),
    },
  });
}

function render() {
  if (!state.auth) return renderLogin();
  if (state.auth.role === "admin") return renderAdmin();
  return renderUser();
}

function renderLogin() {
  app.innerHTML = `
    <div class="shell">
      <div class="container hero">
        <section class="card stack">
          <span class="badge">Contact Center IA · Panel Web</span>
          <div>
            <h1 class="title">Bienvenido al prototipo web del Contact Center</h1>
            <p class="subtitle">
              Ingresa con un usuario predefinido. El sistema separa el acceso por rol:
              usuario final para la conversación por voz y administrador para documentos y auditoría.
            </p>
          </div>
          <div class="status-box">
            <p class="status-line"><strong>Usuario final:</strong> habla, escucha la respuesta automática y lee el texto.</p>
            <p class="status-line"><strong>Administrador:</strong> gestiona documentos y revisa historial, trazabilidad y métricas.</p>
          </div>
        </section>
        <section class="card">
          <form id="login-form" class="login-box">
            <h2 class="panel-title">Iniciar sesión</h2>
            <div class="field">
              <label for="username">Usuario</label>
              <input id="username" name="username" placeholder="usuario o admin" required />
            </div>
            <div class="field">
              <label for="password">Contraseña</label>
              <input id="password" name="password" type="password" placeholder="••••••••" required />
            </div>
            <button type="submit">Ingresar</button>
            <p id="login-message" class="footer-note"></p>
          </form>
        </section>
      </div>
    </div>
  `;

  document.getElementById("login-form").addEventListener("submit", handleLogin);
}

async function handleLogin(event) {
  event.preventDefault();
  const message = document.getElementById("login-message");
  message.textContent = "Validando credenciales...";
  message.className = "footer-note";

  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value.trim();

  try {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "No se pudo iniciar sesión.");

    saveAuth({
      token: payload.access_token,
      role: payload.role,
      username: payload.username,
    });
    render();
  } catch (error) {
    message.textContent = error.message;
    message.className = "footer-note error";
  }
}

function logout() {
  saveAuth(null);
  state.recordedBlob = null;
  render();
}

function renderUser() {
  app.innerHTML = `
    <div class="shell">
      <div class="container stack">
        <div class="topbar">
          <div>
            <h1>Bienvenido, ${escapeHtml(state.auth.username)}</h1>
            <p class="subtitle">Habla con el asistente documental y escucha la respuesta automáticamente.</p>
          </div>
          <div class="actions">
            <button class="secondary" id="logout-btn">Cerrar sesión</button>
          </div>
        </div>

        <div class="grid-2">
          <section class="card stack">
            <div>
              <h2 class="panel-title">Consulta por voz</h2>
              <p class="panel-text">Graba tu audio, envíalo y el sistema responderá en texto y audio automáticamente.</p>
            </div>
            <div class="actions">
              <button id="start-recording">Iniciar grabación</button>
              <button id="stop-recording" class="danger" disabled>Detener</button>
              <button id="send-audio" class="success" disabled>Enviar audio</button>
            </div>
            <div class="status-box">
              <p class="status-line" id="recording-status">Estado: en espera</p>
              <p class="footer-note">El administrador no accede a esta vista; este canal es exclusivo del usuario final.</p>
            </div>
          </section>

          <section class="card stack">
            <div class="transcript-box">
              <h3 class="panel-title">Transcripción</h3>
              <p class="big-text" id="transcript-text">Aún no hay transcripción.</p>
            </div>
            <div class="response-box">
              <h3 class="panel-title">Respuesta</h3>
              <p class="big-text" id="response-text">Aquí aparecerá la respuesta textual del sistema.</p>
              <audio id="response-audio" controls class="hidden"></audio>
            </div>
          </section>
        </div>
      </div>
    </div>
  `;

  document.getElementById("logout-btn").addEventListener("click", logout);
  document.getElementById("start-recording").addEventListener("click", startRecording);
  document.getElementById("stop-recording").addEventListener("click", stopRecording);
  document.getElementById("send-audio").addEventListener("click", sendRecordedAudio);
}

async function startRecording() {
  const status = document.getElementById("recording-status");
  const startBtn = document.getElementById("start-recording");
  const stopBtn = document.getElementById("stop-recording");
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.chunks = [];
    state.mediaRecorder = new MediaRecorder(stream);
    state.mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) state.chunks.push(event.data);
    };
    state.mediaRecorder.onstop = () => {
      state.recordedBlob = new Blob(state.chunks, { type: "audio/webm" });
      document.getElementById("send-audio").disabled = false;
      status.textContent = "Estado: audio listo para enviar";
      stream.getTracks().forEach((track) => track.stop());
    };
    state.mediaRecorder.start();
    status.textContent = "Estado: grabando...";
    startBtn.disabled = true;
    stopBtn.disabled = false;
  } catch (error) {
    status.textContent = `Estado: no se pudo acceder al micrófono (${error.message})`;
  }
}

function stopRecording() {
  const startBtn = document.getElementById("start-recording");
  const stopBtn = document.getElementById("stop-recording");
  if (state.mediaRecorder && state.mediaRecorder.state !== "inactive") state.mediaRecorder.stop();
  stopBtn.disabled = true;
  startBtn.disabled = false;
}

async function sendRecordedAudio() {
  const status = document.getElementById("recording-status");
  const transcript = document.getElementById("transcript-text");
  const answer = document.getElementById("response-text");
  const audioEl = document.getElementById("response-audio");

  if (!state.recordedBlob) {
    status.textContent = "Estado: primero debes grabar un audio.";
    return;
  }

  status.textContent = "Estado: enviando audio al backend...";
  answer.textContent = "Procesando...";

  const formData = new FormData();
  formData.append("file", state.recordedBlob, "consulta.webm");

  try {
    const response = await apiFetch("/voz/interactuar?top_k=3", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorPayload = await response.json();
      throw new Error(errorPayload.detail || "No se pudo procesar el audio.");
    }

    transcript.textContent = decodeBase64Utf8(response.headers.get("X-Transcript-B64")) || "Sin transcripción";
    answer.textContent = decodeBase64Utf8(response.headers.get("X-Answer-B64")) || "Sin respuesta";

    const blob = await response.blob();
    const audioUrl = URL.createObjectURL(blob);
    audioEl.src = audioUrl;
    audioEl.classList.remove("hidden");
    audioEl.play().catch(() => null);
    status.textContent = `Estado: respuesta recibida (${response.headers.get("X-Voice-Latency-Ms") || "n/d"} ms)`;
  } catch (error) {
    status.textContent = `Estado: ${error.message}`;
    answer.textContent = "Ocurrió un error al consultar el sistema.";
  }
}

function renderAdmin() {
  app.innerHTML = `
    <div class="shell">
      <div class="container stack">
        <div class="topbar">
          <div>
            <h1>Panel de administración</h1>
            <p class="subtitle">Gestiona documentos del RAG y revisa historial, trazabilidad y métricas del sistema.</p>
          </div>
          <div class="actions">
            <button class="secondary" id="logout-btn">Cerrar sesión</button>
          </div>
        </div>

        <div class="grid-2">
          <section class="card stack">
            <div>
              <h2 class="panel-title">Carga de PDFs</h2>
              <p class="panel-text">Sube los documentos que formarán parte de la base documental del motor RAG.</p>
            </div>
            <input id="pdf-file" type="file" accept="application/pdf" />
            <button id="upload-pdf" class="success">Subir documento</button>
            <div class="status-box">
              <p class="status-line" id="pdf-status">Estado: sin carga reciente</p>
            </div>
          </section>

          <section class="card stack">
            <div>
              <h2 class="panel-title">Resumen de auditoría</h2>
              <p class="panel-text">Visualiza las métricas acumuladas del sistema auditado.</p>
            </div>
            <div class="metric-grid" id="audit-summary"></div>
            <button id="refresh-audit" class="secondary">Actualizar panel</button>
          </section>
        </div>

        <section class="card stack">
          <div>
            <h2 class="panel-title">Documentos cargados</h2>
            <p class="panel-text">Visualiza los PDFs disponibles para el RAG y elimínalos cuando sea necesario.</p>
          </div>
          <div class="table-box table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Documento</th>
                  <th>Páginas</th>
                  <th>Chunks</th>
                  <th>Fecha</th>
                  <th>Acción</th>
                </tr>
              </thead>
              <tbody id="documents-table-body"></tbody>
            </table>
          </div>
        </section>

        <section class="card stack">
          <div>
            <h2 class="panel-title">Historial de consultas</h2>
            <p class="panel-text">Revisa qué se preguntó, si fue respondido y cuánto tardó el sistema.</p>
          </div>
          <div class="table-box table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Fecha</th>
                  <th>Consulta</th>
                  <th>Estado</th>
                  <th>Latencia</th>
                  <th>Score</th>
                  <th>Detalle</th>
                </tr>
              </thead>
              <tbody id="audit-table-body"></tbody>
            </table>
          </div>
        </section>

        <section class="card stack">
          <div>
            <h2 class="panel-title">Detalle de trazabilidad</h2>
            <p class="panel-text">Consulta, respuesta, documentos usados y fragmentos recuperados.</p>
          </div>
          <div class="status-box" id="audit-detail-box">
            <p class="status-line">Selecciona una interacción del historial para ver su detalle.</p>
          </div>
        </section>
      </div>
    </div>
  `;

  document.getElementById("logout-btn").addEventListener("click", logout);
  document.getElementById("upload-pdf").addEventListener("click", uploadPdf);
  document.getElementById("refresh-audit").addEventListener("click", refreshAdminPanel);
  document.getElementById("documents-table-body").addEventListener("click", handleDocumentActions);
  document.getElementById("audit-table-body").addEventListener("click", handleAuditActions);
  refreshAdminPanel();
}

async function refreshAdminPanel() {
  await Promise.all([loadAuditData(), loadDocuments()]);
}

async function uploadPdf() {
  const status = document.getElementById("pdf-status");
  const fileInput = document.getElementById("pdf-file");
  const file = fileInput.files[0];

  if (!file) {
    status.textContent = "Estado: selecciona un PDF antes de subirlo.";
    return;
  }

  status.textContent = "Estado: procesando documento...";
  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await apiFetch("/documentos/subir?chunk_size=500&chunk_overlap=50", {
      method: "POST",
      body: formData,
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "No se pudo subir el documento.");
    status.textContent = `Estado: ${payload.document} procesado con ${payload.total_chunks} chunks e indexado en ${payload.collection}.`;
    await refreshAdminPanel();
  } catch (error) {
    status.textContent = `Estado: ${error.message}`;
  }
}

async function loadDocuments() {
  const tbody = document.getElementById("documents-table-body");
  tbody.innerHTML = `<tr><td colspan="6">Cargando documentos...</td></tr>`;

  try {
    const response = await apiFetch("/documentos");
    const documents = await response.json();
    if (!response.ok) throw new Error(documents.detail || "No se pudieron cargar los documentos.");

    if (!documents.length) {
      tbody.innerHTML = `<tr><td colspan="6">No hay documentos registrados.</td></tr>`;
      return;
    }

    tbody.innerHTML = documents
      .map(
        (item) => `
        <tr>
          <td>${item.id}</td>
          <td>${escapeHtml(item.document_name)}</td>
          <td>${item.pages}</td>
          <td>${item.indexed_chunks}</td>
          <td>${new Date(item.created_at).toLocaleString()}</td>
          <td><button class="danger" data-action="delete-document" data-id="${item.id}">Eliminar</button></td>
        </tr>
      `
      )
      .join("");
  } catch (error) {
    tbody.innerHTML = `<tr><td colspan="6">${escapeHtml(error.message)}</td></tr>`;
  }
}

async function handleDocumentActions(event) {
  const button = event.target.closest("button[data-action='delete-document']");
  if (!button) return;
  const documentId = button.dataset.id;
  if (!window.confirm("¿Eliminar este documento y sus chunks indexados?")) return;

  try {
    const response = await apiFetch(`/documentos/${documentId}`, { method: "DELETE" });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "No se pudo eliminar el documento.");
    document.getElementById("pdf-status").textContent = `Estado: documento ${payload.document_name} eliminado correctamente.`;
    await refreshAdminPanel();
  } catch (error) {
    document.getElementById("pdf-status").textContent = `Estado: ${error.message}`;
  }
}

async function loadAuditData() {
  const summaryEl = document.getElementById("audit-summary");
  const tbody = document.getElementById("audit-table-body");
  summaryEl.innerHTML = `<div class="metric"><span>Cargando</span><strong>...</strong></div>`;
  tbody.innerHTML = `<tr><td colspan="7">Cargando historial...</td></tr>`;

  try {
    const [summaryResp, recordsResp] = await Promise.all([
      apiFetch("/auditoria/resumen"),
      apiFetch("/auditoria/registros?limit=20&interaction_type=voice"),
    ]);
    const summary = await summaryResp.json();
    const records = await recordsResp.json();

    if (!summaryResp.ok) throw new Error(summary.detail || "No se pudo cargar el resumen.");
    if (!recordsResp.ok) throw new Error(records.detail || "No se pudo cargar el historial.");

    summaryEl.innerHTML = `
      <div class="metric"><span>Total registros</span><strong>${summary.total_records}</strong></div>
      <div class="metric"><span>Latencia promedio</span><strong>${summary.average_latency_ms} ms</strong></div>
      <div class="metric"><span>Alta latencia</span><strong>${summary.high_latency_count}</strong></div>
      <div class="metric"><span>Low confidence</span><strong>${summary.low_confidence_count}</strong></div>
      <div class="metric"><span>Out of scope</span><strong>${summary.out_of_scope_count}</strong></div>
      <div class="metric"><span>Fallidas</span><strong>${summary.failed_count}</strong></div>
    `;

    if (!records.length) {
      tbody.innerHTML = `<tr><td colspan="7">No hay consultas registradas todavía.</td></tr>`;
      return;
    }

    tbody.innerHTML = records
      .map(
        (item) => `
        <tr>
          <td>${item.id}</td>
          <td>${new Date(item.created_at).toLocaleString()}</td>
          <td>${escapeHtml(item.transcript || item.user_query || "-")}</td>
          <td>${formatStatusLabel(item)}</td>
          <td>${item.latency_total_ms} ms</td>
          <td>${item.top_score == null ? "-" : item.top_score}</td>
          <td><button class="secondary" data-action="view-audit" data-id="${item.id}">Ver</button></td>
        </tr>
      `
      )
      .join("");
  } catch (error) {
    summaryEl.innerHTML = `<div class="metric"><span>Error</span><strong>${escapeHtml(error.message)}</strong></div>`;
    tbody.innerHTML = `<tr><td colspan="7">No se pudo cargar el historial.</td></tr>`;
  }
}

async function handleAuditActions(event) {
  const button = event.target.closest("button[data-action='view-audit']");
  if (!button) return;
  await loadAuditDetail(button.dataset.id);
}

async function loadAuditDetail(recordId) {
  const detailBox = document.getElementById("audit-detail-box");
  detailBox.innerHTML = `<p class="status-line">Cargando detalle...</p>`;

  try {
    const response = await apiFetch(`/auditoria/registros/${recordId}`);
    const record = await response.json();
    if (!response.ok) throw new Error(record.detail || "No se pudo cargar el detalle.");

    const sources = record.metadata?.sources || [];
    const documentsUsed = record.metadata?.documents_used || [];

    detailBox.innerHTML = `
      <p class="status-line"><strong>Consulta:</strong> ${escapeHtml(record.transcript || record.user_query || "-")}</p>
      <p class="status-line"><strong>Estado:</strong> ${escapeHtml(formatStatusLabel(record))}</p>
      <p class="status-line"><strong>Respuesta:</strong> ${escapeHtml(record.response_text || "Sin respuesta registrada.")}</p>
      <p class="status-line"><strong>Documentos utilizados:</strong> ${documentsUsed.length ? documentsUsed.map(escapeHtml).join(", ") : "Sin documentos registrados."}</p>
      <p class="footer-note"><strong>Fragmentos recuperados:</strong></p>
      ${
        sources.length
          ? sources
              .map(
                (source) => `
                  <div class="status-box" style="margin-top:8px;">
                    <p class="status-line"><strong>${escapeHtml(source.document)}</strong> · score ${escapeHtml(source.similarity_percentage)}% · páginas ${escapeHtml(source.page_start ?? "-")}-${escapeHtml(source.page_end ?? "-")}</p>
                    <p class="footer-note">${escapeHtml(source.section_title || "Sin sección")}</p>
                    <p class="footer-note">${escapeHtml(source.content)}</p>
                  </div>
                `
              )
              .join("")
          : `<p class="footer-note">No hay fragmentos registrados para esta interacción.</p>`
      }
    `;
  } catch (error) {
    detailBox.innerHTML = `<p class="status-line">${escapeHtml(error.message)}</p>`;
  }
}

render();
