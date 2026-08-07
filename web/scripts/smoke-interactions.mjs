/**
 * Browser interaction smoke via Edge CDP (no project deps).
 * Asserts blank ordinary startup, then enters values explicitly for interactions.
 */
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
const DASH = "\u2014";

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

const userData = join(process.env.TEMP || "/tmp", `ggl-smoke-${Date.now()}`);
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

async function evaluate(expression, sessionId) {
  const result = await cdp(
    "Runtime.evaluate",
    { expression, returnByValue: true },
    sessionId,
  );
  if (result.exceptionDetails) {
    throw new Error(JSON.stringify(result.exceptionDetails));
  }
  return result.result.value;
}

const { targetId } = await cdp("Target.createTarget", { url: "about:blank" });
const { sessionId } = await cdp("Target.attachToTarget", {
  targetId,
  flatten: true,
});
await cdp(
  "Emulation.setDeviceMetricsOverride",
  { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false },
  sessionId,
);
await cdp("Page.enable", {}, sessionId);
await cdp("Runtime.enable", {}, sessionId);
await cdp("Page.navigate", { url: `http://127.0.0.1:${port}/` }, sessionId);

for (let i = 0; i < 50; i++) {
  const ready = await evaluate(
    '!!(document.getElementById("slot-helmet") && document.getElementById("jewel-1") && document.getElementById("result-flame-link"))',
    sessionId,
  );
  if (ready) break;
  await sleep(200);
}

const report = {};

report.blankStartup = await evaluate(
  `({
    life: document.getElementById("maximum-life").value,
    lr: document.getElementById("light-radius").value,
    other: document.getElementById("other-link").value,
    level: document.getElementById("flame-link-level").value,
    gg: document.getElementById("golden-glory").checked,
    powerful: document.getElementById("powerful-bond").checked,
    inspiring: document.getElementById("inspiring-bond").checked,
    gear: document.getElementById("gear-fire-res").value,
    aura: document.getElementById("aura-fire-res").value,
    reduced: document.getElementById("enmity-reduced").value,
    maxFr: document.getElementById("maximum-fire-res").value,
    enmity: document.getElementById("enmity-equipped").checked,
    flame: document.getElementById("result-flame-link").textContent.trim(),
    net: document.getElementById("result-net-effect").textContent.trim(),
    mult: document.getElementById("result-multiplier").textContent.trim(),
    enmityResult: document.getElementById("result-enmity").textContent.trim(),
    flameError: document.getElementById("flame-error").textContent.trim(),
    total: document.getElementById("breakdown-total").textContent.trim(),
    jewels: document.querySelectorAll("#jewel-rows .field-row").length,
    helmet: document.getElementById("slot-helmet").value,
    overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1
  })`,
  sessionId,
);

report.populateSample = await evaluate(POPULATE_SAMPLE_EXPRESSION, sessionId);

report.switchBreakdown = await evaluate(
  `(document.getElementById("tab-breakdown").click(), {
    active: document.getElementById("view-breakdown").classList.contains("is-active"),
    total: document.getElementById("breakdown-total").textContent
  })`,
  sessionId,
);

report.addManyJewels = await evaluate(
  `(() => {
    for (let i = 0; i < 12; i++) document.getElementById("btn-add-jewel").click();
    return {
      jewels: document.querySelectorAll("#jewel-rows .field-row").length,
      removable: document.querySelectorAll(".btn-remove-jewel").length,
      addDisabled: document.getElementById("btn-add-jewel").disabled
    };
  })()`,
  sessionId,
);

report.removeDynamicJewel = await evaluate(
  `(document.querySelector(".btn-remove-jewel").click(), {
    jewels: document.querySelectorAll("#jewel-rows .field-row").length,
    removable: document.querySelectorAll(".btn-remove-jewel").length
  })`,
  sessionId,
);

report.changeHelmetApply = await evaluate(
  `(() => {
    document.getElementById("btn-reset-breakdown").click();
    const helmet = document.getElementById("slot-helmet");
    helmet.value = "99";
    helmet.dispatchEvent(new Event("input", { bubbles: true }));
    const total = document.getElementById("breakdown-total").textContent;
    document.getElementById("btn-apply-total").click();
    return {
      total,
      calculatorActive: document.getElementById("view-calculator").classList.contains("is-active"),
      lr: document.getElementById("light-radius").value
    };
  })()`,
  sessionId,
);

report.resetCalculator = await evaluate(
  `(document.getElementById("btn-reset-calculator").click(), {
    lr: document.getElementById("light-radius").value,
    life: document.getElementById("maximum-life").value,
    flame: document.getElementById("result-flame-link").textContent,
    flameError: document.getElementById("flame-error").textContent
  })`,
  sessionId,
);

report.resetBreakdown = await evaluate(
  `(() => {
    document.getElementById("tab-breakdown").click();
    document.getElementById("btn-reset-breakdown").click();
    return {
      total: document.getElementById("breakdown-total").textContent,
      jewels: document.querySelectorAll("#jewel-rows .field-row").length,
      helmet: document.getElementById("slot-helmet").value
    };
  })()`,
  sessionId,
);

report.validationMessage = await evaluate(
  `(() => {
    document.getElementById("tab-calculator").click();
    const life = document.getElementById("maximum-life");
    life.value = "5000";
    life.dispatchEvent(new Event("input", { bubbles: true }));
    const lr = document.getElementById("light-radius");
    lr.value = "40";
    lr.dispatchEvent(new Event("input", { bubbles: true }));
    const other = document.getElementById("other-link");
    other.value = "0";
    other.dispatchEvent(new Event("input", { bubbles: true }));
    const level = document.getElementById("flame-link-level");
    level.value = "abc";
    level.dispatchEvent(new Event("input", { bubbles: true }));
    return {
      flameError: document.getElementById("flame-error").textContent,
      flame: document.getElementById("result-flame-link").textContent
    };
  })()`,
  sessionId,
);

console.log(JSON.stringify(report, null, 2));

const blank = report.blankStartup;
const ok =
  blank?.life === "" &&
  blank?.lr === "" &&
  blank?.other === "" &&
  blank?.level === "" &&
  blank?.gg === false &&
  blank?.powerful === false &&
  blank?.inspiring === false &&
  blank?.gear === "" &&
  blank?.enmity === false &&
  blank?.flame === DASH &&
  blank?.net === DASH &&
  blank?.mult === DASH &&
  blank?.enmityResult === DASH &&
  blank?.flameError === "Enter Maximum Life" &&
  blank?.total === "0%" &&
  blank?.jewels === 3 &&
  blank?.helmet === "0" &&
  blank?.overflowX === false &&
  report.populateSample?.flame === "3878-4423" &&
  report.addManyJewels?.jewels === 15 &&
  report.addManyJewels?.removable === 12 &&
  report.addManyJewels?.addDisabled === false &&
  report.removeDynamicJewel?.jewels === 14 &&
  report.changeHelmetApply?.calculatorActive === true &&
  report.changeHelmetApply?.lr === "99" &&
  report.resetCalculator?.life === "" &&
  report.resetBreakdown?.total === "0%" &&
  report.resetBreakdown?.jewels === 3 &&
  report.validationMessage?.flameError;

if (!ok) {
  console.error("SMOKE FAILED");
  process.exitCode = 1;
} else {
  console.log("SMOKE PASSED");
}

await cdp("Target.closeTarget", { targetId });
ws.close();
edgeProc.kill();
server.close();
