import { spawn } from 'node:child_process';
import { writeFile } from 'node:fs/promises';

const baseUrl = 'http://127.0.0.1:4173/settings';
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const chrome = spawn(
  'google-chrome',
  [
    '--headless=new',
    '--no-sandbox',
    '--disable-gpu',
    '--remote-debugging-port=9222',
    '--remote-allow-origins=*',
    '--user-data-dir=/tmp/zer582-settings-chrome',
    '--lang=zh-CN',
    'about:blank',
  ],
  { stdio: 'ignore' },
);

async function getTarget() {
  for (let attempt = 0; attempt < 50; attempt += 1) {
    try {
      const response = await fetch('http://127.0.0.1:9222/json/list');
      const targets = await response.json();
      const page = targets.find((target) => target.type === 'page');
      if (page?.webSocketDebuggerUrl) return page;
    } catch {
      // Chrome is still starting.
    }
    await sleep(200);
  }
  throw new Error('Chrome DevTools target did not become ready');
}

function connect(url) {
  return new Promise((resolve, reject) => {
    const socket = new WebSocket(url);
    socket.addEventListener('open', () => resolve(socket), { once: true });
    socket.addEventListener('error', reject, { once: true });
  });
}

const target = await getTarget();
const socket = await connect(target.webSocketDebuggerUrl);
let nextId = 0;
const pending = new Map();

socket.addEventListener('message', (event) => {
  const message = JSON.parse(event.data);
  if (!message.id) return;
  const task = pending.get(message.id);
  if (!task) return;
  pending.delete(message.id);
  if (message.error) task.reject(new Error(JSON.stringify(message.error)));
  else task.resolve(message.result);
});

function send(method, params = {}) {
  const id = ++nextId;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    socket.send(JSON.stringify({ id, method, params }));
  });
}

async function evaluate(expression) {
  const result = await send('Runtime.evaluate', {
    expression,
    returnByValue: true,
    awaitPromise: true,
  });
  return result?.result?.value;
}

async function waitFor(expression, label) {
  for (let attempt = 0; attempt < 50; attempt += 1) {
    if (await evaluate(expression)) return;
    await sleep(200);
  }
  throw new Error('Timed out waiting for ' + label);
}

async function navigate(width, height, mobile) {
  await send('Emulation.setDeviceMetricsOverride', {
    width,
    height,
    deviceScaleFactor: 1,
    mobile,
  });
  await send('Page.navigate', { url: baseUrl });
  await waitFor(
    "document.readyState === 'complete' && document.querySelectorAll('[role=\"tab\"]').length >= 5",
    'settings tabs',
  );
  await waitFor(
    "Array.from(document.querySelectorAll('input')).some((input) => input.value === '30')",
    'settings fixture data',
  );
  await evaluate('window.scrollTo(0, 0); true');
  await sleep(500);
}

async function clickText(selector, text) {
  const expression =
    "(() => { const nodes = Array.from(document.querySelectorAll(" +
    JSON.stringify(selector) +
    ")); const node = nodes.find((item) => (item.textContent || '').includes(" +
    JSON.stringify(text) +
    ")); if (!node) return false; node.click(); return true; })()";
  if (!(await evaluate(expression))) {
    throw new Error('Unable to click ' + text);
  }
  await sleep(700);
}

async function capture(fileName) {
  await evaluate('window.scrollTo(0, 0); true');
  await sleep(300);
  const result = await send('Page.captureScreenshot', {
    format: 'png',
    fromSurface: true,
    captureBeyondViewport: false,
  });
  await writeFile(fileName, Buffer.from(result.data, 'base64'));
}

try {
  await send('Page.enable');
  await send('Runtime.enable');

  await navigate(1440, 1200, false);
  await clickText('[role="tab"]', '通知');
  await clickText('.ant-tabs-tabpane-active button', '测试已保存配置');
  await waitFor(
    "document.body.innerText.includes('上游 HTTP') && document.body.innerText.includes('48 ms')",
    'webhook diagnostics',
  );
  await capture('settings-webhook.png');

  await clickText('[role="tab"]', '验证码 AI');
  await clickText('.ant-tabs-tabpane-active button', '测试 AI');
  await waitFor(
    "document.body.innerText.includes('连通性：正常') && document.body.innerText.includes('契约：失败')",
    'AI diagnostics',
  );
  await capture('settings-ai.png');

  await clickText('[role="tab"]', '外部 API / 池');
  await waitFor(
    "document.body.innerText.includes('Automation') && document.body.innerText.includes('Reporting')",
    'API key table',
  );
  await capture('settings-api-keys.png');

  await navigate(390, 844, true);
  await clickText('[role="tab"]', '外部 API / 池');
  await waitFor(
    "document.body.innerText.includes('Automation')",
    'mobile API key table',
  );
  await capture('settings-api-keys-mobile.png');
} finally {
  try {
    await send('Browser.close');
  } catch {
    chrome.kill('SIGTERM');
  }
  socket.close();
}
