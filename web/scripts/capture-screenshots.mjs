/**
 * One-off screenshot helper using system Edge + CDP (no project deps).
 * Populates approved synthetic sample data before capture — production startup is blank.
 * Usage: node web/scripts/capture-screenshots.mjs
 */

import { spawn } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import { createServer } from "node:http";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { setTimeout as sleep } from "node:timers/promises";
import { POPULATE_SAMPLE_EXPRESSION } from "./sample-data.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const siteDir = join(root, "site");
const outDir = join(root, "screenshots");
const edge =
  process.env.EDGE_PATH ||
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";

const shots = [
  {
    name: "desktop-calculator.png",
    width: 1280,
    height: 900,
    urlPath: "/?view=calculator",
    waitText: "3878",
  },
  {
    name: "desktop-breakdown.png",
    width: 1280,
    height: 900,
    urlPath: "/?view=breakdown",
    waitText: "254%",
  },
  {
    name: "mobile-calculator.png",
    width: 390,
    height: 844,
    urlPath: "/?view=calculator",
    waitText: "3878",
  },
  {
    name: "mobile-breakdown.png",
    width: 390,
    height: 844,
    urlPath: "/?view=breakdown",
    waitText: "254%",
  },
];

function contentType(path) {
  if (path.endsWith(".html")) return "text/html; charset=utf-8";
  if (path.endsWith(".css")) return "text/css; charset=utf-8";
  if (path.endsWith(".mjs") || path.endsWith(".js"))
    return "text/javascript; charset=utf-8";
  if (path.endsWith(".json")) return "application/json; charset=utf-8";
  if (path.endsWith(".png")) return "image/png";
  return "application/octet-stream";
}

async function startStaticServer() {
  const { readFile } = await import("node:fs/promises");
  const server = createServer(async (req, res) => {
    try {
      let urlPath = decodeURIComponent((req.url || "/").split("?")[0]);
      if (urlPath === "/") urlPath = "/index.html";
      const filePath = join(siteDir, urlPath.replace(/^\//, ""));
      if (!filePath.startsWith(siteDir)) {
        res.writeHead(403);
        res.end("Forbidden");
        return;
      }
      const data = await readFile(filePath);
      res.writeHead(200, { "Content-Type": contentType(filePath) });
      res.end(data);
    } catch {
      res.writeHead(404);
      res.end("Not found");
    }
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address();
  return { server, port };
}

async function cdp(ws, method, params = {}, sessionId) {
  const id = cdp.nextId++;
  const msg = { id, method, params };
  if (sessionId) msg.sessionId = sessionId;
  ws.send(JSON.stringify(msg));
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      cdp.pending.delete(id);
      reject(new Error(`CDP timeout: ${method}`));
    }, 30000);
    cdp.pending.set(id, { resolve, reject, timer });
  });
}
cdp.nextId = 1;
cdp.pending = new Map();

function attachWs(ws) {
  ws.addEventListener("message", (event) => {
    const data = JSON.parse(String(event.data));
    if (data.id != null && cdp.pending.has(data.id)) {
      const { resolve, reject, timer } = cdp.pending.get(data.id);
      clearTimeout(timer);
      cdp.pending.delete(data.id);
      if (data.error) reject(new Error(JSON.stringify(data.error)));
      else resolve(data.result);
    }
  });
}

async function waitForText(ws, sessionId, text, timeoutMs = 15000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const result = await cdp(
      ws,
      "Runtime.evaluate",
      {
        expression: `document.body && document.body.innerText.includes(${JSON.stringify(text)})`,
        returnByValue: true,
      },
      sessionId,
    );
    if (result.result?.value === true) return;
    await sleep(200);
  }
  throw new Error(`Timed out waiting for text: ${text}`);
}

async function waitReady(ws, sessionId) {
  const start = Date.now();
  while (Date.now() - start < 15000) {
    const result = await cdp(
      ws,
      "Runtime.evaluate",
      {
        expression:
          '!!(document.getElementById("slot-helmet") && document.getElementById("jewel-1") && document.getElementById("result-flame-link"))',
        returnByValue: true,
      },
      sessionId,
    );
    if (result.result?.value === true) return;
    await sleep(200);
  }
  throw new Error("Timed out waiting for calculator ready");
}

async function main() {
  await mkdir(outDir, { recursive: true });
  const { server, port } = await startStaticServer();
  const userData = join(process.env.TEMP || "/tmp", `ggl-cdp-${Date.now()}`);
  const edgeProc = spawn(
    edge,
    [
      `--remote-debugging-port=0`,
      `--user-data-dir=${userData}`,
      "--headless=new",
      "--disable-gpu",
      "--hide-scrollbars",
      "--no-first-run",
      "--no-default-browser-check",
      "about:blank",
    ],
    { stdio: ["ignore", "pipe", "pipe"] },
  );

  let debugUrl = null;
  const stderrChunks = [];
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("Edge debug port timeout")), 15000);
    edgeProc.stderr.on("data", (buf) => {
      const text = buf.toString();
      stderrChunks.push(text);
      const match = text.match(/DevTools listening on (ws:\/\/\S+)/);
      if (match) {
        debugUrl = match[1];
        clearTimeout(timer);
        resolve();
      }
    });
    edgeProc.on("error", reject);
    edgeProc.on("exit", (code) => {
      if (!debugUrl) {
        clearTimeout(timer);
        reject(new Error(`Edge exited early (${code}): ${stderrChunks.join("")}`));
      }
    });
  });

  const browserWs = new WebSocket(debugUrl);
  await new Promise((resolve, reject) => {
    browserWs.addEventListener("open", resolve);
    browserWs.addEventListener("error", reject);
  });
  attachWs(browserWs);

  try {
    for (const shot of shots) {
      const { targetId } = await cdp(browserWs, "Target.createTarget", {
        url: "about:blank",
      });
      const { sessionId } = await cdp(browserWs, "Target.attachToTarget", {
        targetId,
        flatten: true,
      });
      await cdp(
        browserWs,
        "Emulation.setDeviceMetricsOverride",
        {
          width: shot.width,
          height: shot.height,
          deviceScaleFactor: 1,
          mobile: shot.width < 800,
        },
        sessionId,
      );
      await cdp(browserWs, "Page.enable", {}, sessionId);
      await cdp(browserWs, "Runtime.enable", {}, sessionId);
      const url = `http://127.0.0.1:${port}${shot.urlPath}`;
      await cdp(browserWs, "Page.navigate", { url }, sessionId);
      await waitReady(browserWs, sessionId);
      await cdp(
        browserWs,
        "Runtime.evaluate",
        { expression: POPULATE_SAMPLE_EXPRESSION, returnByValue: true },
        sessionId,
      );
      await waitForText(browserWs, sessionId, shot.waitText);
      await sleep(300);
      const shotResult = await cdp(
        browserWs,
        "Page.captureScreenshot",
        { format: "png", fromSurface: true },
        sessionId,
      );
      const outPath = join(outDir, shot.name);
      await writeFile(outPath, Buffer.from(shotResult.data, "base64"));
      console.log(`Wrote ${outPath}`);
      await cdp(browserWs, "Target.closeTarget", { targetId });
    }
  } finally {
    browserWs.close();
    edgeProc.kill();
    server.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
