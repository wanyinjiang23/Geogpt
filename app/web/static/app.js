const $ = id => document.getElementById(id);
let sessionId = sessionStorage.getItem('geogpt-session');
let busy = false, ready = false, submitting = false, polling = false;
let transcript = '';

async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { 'Content-Type': 'application/json' } });
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(typeof data.detail === 'string' ? data.detail : '请求格式不正确，请检查输入。');
    error.status = response.status;
    throw error;
  }
  return data;
}
function showError(message = '') { $('error').textContent = message; $('error').hidden = !message; }
function controls() {
  $('send').disabled = !ready || busy || submitting || !$('input').value.trim();
  $('stop').disabled = !busy || submitting;
  $('new').disabled = busy || submitting;
  $('input').disabled = busy || submitting;
  document.querySelectorAll('[data-prompt]').forEach(button => { button.disabled = busy || submitting; });
}
function render(data) {
  busy = data.run?.status === 'running';
  const next = JSON.stringify(data.messages);
  if (next !== transcript && data.messages.length) {
    const nearBottom = $('messages').scrollHeight - $('messages').scrollTop - $('messages').clientHeight < 100;
    $('messages').replaceChildren();
    for (const message of data.messages) {
      const row = document.createElement('article');
      row.className = `message ${message.role} ${message.status || ''}`;
      const label = document.createElement('div'); label.className = 'role';
      label.textContent = message.role === 'user' ? '你' : 'GeoGPT';
      const bubble = document.createElement('div'); bubble.className = 'bubble';
      bubble.textContent = message.content;
      row.append(label, bubble); $('messages').append(row);
    }
    if (nearBottom || busy) $('messages').scrollTop = $('messages').scrollHeight;
  }
  transcript = next;
  $('progress').hidden = !data.run;
  $('steps').textContent = (data.run?.events || []).join('\n\n') || (busy ? '正在启动 GISAgent…' : '暂无执行步骤');
  if (ready) {
    $('status').textContent = busy ? '正在处理 · 可暂停 / 停止本次任务' : '后端已连接 · 可以开始对话';
    $('dot').className = `dot ${busy ? 'busy' : 'ready'}`;
  }
  controls();
}
async function newSession() {
  const data = await api('/api/sessions', { method: 'POST' });
  sessionId = data.session_id;
  sessionStorage.setItem('geogpt-session', sessionId);
}
async function refresh() {
  const data = await api(`/api/sessions/${sessionId}`);
  render(data);
}
async function checkHealth() {
  const health = await api('/api/health'); ready = health.ready;
  if (!ready) {
    $('status').textContent = '服务已连接 · 后端配置待完成';
    const issues = [];
    if (!health.configured) issues.push('请在项目 .env 中填写 GEOGPT_API_KEY');
    if (health.missing_dependencies.length) issues.push(`缺少依赖：${health.missing_dependencies.join('、')}，请安装 requirements-web.txt`);
    showError(issues.join('；'));
  }
  controls();
}
$('composer').addEventListener('submit', async event => {
  event.preventDefault();
  const message = $('input').value.trim();
  if (!message || busy || submitting || !ready) return;
  submitting = true; controls(); showError();
  try {
    await api(`/api/sessions/${sessionId}/messages`, { method: 'POST', body: JSON.stringify({ message }) });
    $('input').value = ''; await refresh();
  } catch (error) { showError(error.message); }
  finally { submitting = false; controls(); }
});
$('input').addEventListener('input', controls);
$('input').addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault(); $('composer').requestSubmit();
  }
});
$('stop').addEventListener('click', async () => {
  submitting = true; controls();
  try { await api(`/api/sessions/${sessionId}/stop`, { method: 'POST' }); await refresh(); }
  catch (error) { showError(error.message); }
  finally { submitting = false; controls(); $('input').focus(); }
});
$('new').addEventListener('click', async () => {
  submitting = true; controls();
  try { await newSession(); location.reload(); }
  catch (error) { showError(error.message); submitting = false; controls(); }
});
document.querySelectorAll('[data-prompt]').forEach(button => button.addEventListener('click', () => {
  $('input').value = button.dataset.prompt; controls(); $('input').focus();
}));
(async () => {
  try {
    await checkHealth();
    if (!sessionId) await newSession();
    try { await refresh(); }
    catch (error) {
      if (error.status !== 404) throw error;
      await newSession(); await refresh();
    }
  } catch (error) { showError(error.message); }
  setInterval(async () => {
    if (polling || submitting || !sessionId) return;
    polling = true;
    try { await refresh(); }
    catch (error) {
      if (error.status === 404) { busy = false; ready = false; controls(); }
      showError(error.message);
    }
    finally { polling = false; }
  }, 700);
})();
