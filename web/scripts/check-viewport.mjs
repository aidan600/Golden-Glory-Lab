import { spawn } from "node:child_process";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { setTimeout as sleep } from "node:timers/promises";
import { POPULATE_SAMPLE_EXPRESSION } from "./sample-data.mjs";

const siteDir = join(dirname(fileURLToPath(import.meta.url)), "../site");
const edge =
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";

function contentType(path) {
  if (path.endsWith(".html")) return "text/html";
  if (path.endsWith(".css")) return "text/css";
  if (path.endsWith(".mjs")) return "text/javascript";
  if (path.endsWith(".json")) return "application/json";
  if (path.endsWith(".png")) return "image/png";
  return "application/octet-stream";
}

const server = createServer(async (req, res) => {
  try {
    let urlPath = decodeURIComponent((req.url || "/").split("?")[0]);
    if (urlPath === "/") urlPath = "/index.html";
    const filePath = join(siteDir, urlPath.replace(/^\//, ""));
    const data = await readFile(filePath);
    res.writeHead(200, { "Content-Type": contentType(filePath) });
    res.end(data);
  } catch {
    res.writeHead(404);
    res.end();
  }
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const { port } = server.address();

const userData = join(process.env.TEMP || "/tmp", `ggl-check-${Date.now()}`);
const edgeProc = spawn(
  edge,
  [
    "--remote-debugging-port=0",
    `--user-data-dir=${userData}`,
    "--headless=new",
    "--disable-gpu",
    "about:blank",
  ],
  { stdio: ["ignore", "pipe", "pipe"] },
);

let debugUrl;
await new Promise((resolve, reject) => {
  const timer = setTimeout(() => reject(new Error("debug port timeout")), 15000);
  edgeProc.stderr.on("data", (buf) => {
    const match = buf.toString().match(/DevTools listening on (ws:\/\/\S+)/);
    if (match) {
      debugUrl = match[1];
      clearTimeout(timer);
      resolve();
    }
  });
});

const ws = new WebSocket(debugUrl);
await new Promise((resolve, reject) => {
  ws.addEventListener("open", resolve);
  ws.addEventListener("error", reject);
});

let nextId = 1;
const pending = new Map();
ws.addEventListener("message", (event) => {
  const data = JSON.parse(String(event.data));
  if (data.id != null && pending.has(data.id)) {
    const { resolve, reject, timer } = pending.get(data.id);
    clearTimeout(timer);
    pending.delete(data.id);
    if (data.error) reject(new Error(JSON.stringify(data.error)));
    else resolve(data.result);
  }
});

function cdp(method, params = {}, sessionId) {
  const id = nextId++;
  const msg = { id, method, params };
  if (sessionId) msg.sessionId = sessionId;
  ws.send(JSON.stringify(msg));
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(method)), 20000);
    pending.set(id, { resolve, reject, timer });
  });
}

async function inspect(view, width, height) {
  const { targetId } = await cdp("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await cdp("Target.attachToTarget", {
    targetId,
    flatten: true,
  });
  await cdp(
    "Emulation.setDeviceMetricsOverride",
    { width, height, deviceScaleFactor: 1, mobile: width < 800 },
    sessionId,
  );
  await cdp("Page.enable", {}, sessionId);
  await cdp("Runtime.enable", {}, sessionId);
  await cdp(
    "Page.navigate",
    { url: `http://127.0.0.1:${port}/?view=${view}` },
    sessionId,
  );
  for (let i = 0; i < 50; i++) {
    const ready = await cdp(
      "Runtime.evaluate",
      {
        expression:
          '!!(document.getElementById("slot-helmet") && document.getElementById("jewel-1") && document.getElementById("result-flame-link"))',
        returnByValue: true,
      },
      sessionId,
    );
    if (ready.result.value) break;
    await sleep(200);
  }

  const blank = await cdp(
    "Runtime.evaluate",
    {
      expression: `({
        life: document.getElementById("maximum-life").value,
        flame: document.getElementById("result-flame-link").textContent,
        total: document.getElementById("breakdown-total").textContent,
        jewels: document.querySelectorAll("#jewel-rows .field-row").length
      })`,
      returnByValue: true,
    },
    sessionId,
  );

  await cdp(
    "Runtime.evaluate",
    { expression: POPULATE_SAMPLE_EXPRESSION, returnByValue: true },
    sessionId,
  );

  const result = await cdp(
    "Runtime.evaluate",
    {
      expression: `({
        scrollH: document.documentElement.scrollHeight,
        clientH: document.documentElement.clientHeight,
        clientW: document.documentElement.clientWidth,
        scrollW: document.documentElement.scrollWidth,
        pre: document.getElementById("pre-enmity-display")?.textContent,
        final: document.getElementById("final-uncapped-display")?.textContent,
        over: document.getElementById("overcapped-display")?.textContent,
        flame: document.getElementById("result-flame-link")?.textContent,
        enmity: document.getElementById("result-enmity")?.textContent,
        total: document.getElementById("breakdown-total")?.textContent,
        overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
        bodyOverflowX: document.body.scrollWidth > document.documentElement.clientWidth + 1,
        tabs: (() => {
          const tabs = [...document.querySelectorAll(".tab")];
          return tabs.map((tab) => {
            const rect = tab.getBoundingClientRect();
            return {
              label: tab.textContent.replace(/\\s+/g, " ").trim(),
              width: Math.round(rect.width),
              height: Math.round(rect.height),
              overflow: tab.scrollWidth > tab.clientWidth + 1,
            };
          });
        })(),
        overInView: (() => {
          const el = document.getElementById("overcapped-display");
          if (!el) return false;
          const rect = el.getBoundingClientRect();
          return rect.top >= 0 && rect.bottom <= window.innerHeight;
        })(),
        applyInView: (() => {
          const el = document.getElementById("btn-apply-total");
          if (!el) return null;
          const rect = el.getBoundingClientRect();
          return rect.top >= 0 && rect.bottom <= window.innerHeight;
        })()
      })`,
      returnByValue: true,
    },
    sessionId,
  );
  console.log(
    `${view} ${width}x${height}`,
    JSON.stringify({ blank: blank.result.value, ...result.result.value }),
  );
  await cdp("Target.closeTarget", { targetId });
}

await inspect("calculator", 1280, 900);
await inspect("breakdown", 1280, 900);
await inspect("calculator", 390, 844);
await inspect("breakdown", 390, 844);
await inspect("calculator", 360, 800);
await inspect("breakdown", 360, 800);

ws.close();
edgeProc.kill();
server.close();
