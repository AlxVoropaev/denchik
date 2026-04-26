import { chromium } from "playwright";

const BASE = process.env.BASE ?? "http://host.docker.internal:5173";
const email = `bot${Date.now()}@t.com`;
const log = (...a) => console.log("[smoke]", ...a);

const browser = await chromium.launch();
const ctx = await browser.newContext();
const page = await ctx.newPage();

page.on("console", (m) => console.log(`[browser:${m.type()}]`, m.text()));
page.on("pageerror", (e) => console.log("[browser:pageerror]", e.message));
page.on("requestfailed", (r) =>
  console.log("[browser:reqfailed]", r.method(), r.url(), r.failure()?.errorText),
);

log("goto", BASE);
await page.goto(BASE, { waitUntil: "networkidle" });

log("on", page.url());
await page.screenshot({ path: "/work/01-login.png" });

if (page.url().endsWith("/login")) {
  log("registering", email);
  await page.getByRole("button", { name: /register/i }).click().catch(() => {});
  await page.getByPlaceholder(/email/i).fill(email);
  await page.getByPlaceholder(/display name/i).fill("Bot").catch(() => {});
  await page.getByPlaceholder(/password/i).fill("pw123456");
  await page.getByRole("button", { name: /create|register|sign up/i }).click();
  await page.waitForURL((u) => !u.pathname.endsWith("/login"), { timeout: 5000 }).catch(() => {});
}

log("after auth url=", page.url());
await page.screenshot({ path: "/work/02-after-auth.png" });

const wsName = "BotWS-" + Date.now();
const wsInput = page.getByPlaceholder(/workspace name/i);
if (await wsInput.isVisible().catch(() => false)) {
  log("creating workspace", wsName);
  await wsInput.fill(wsName);
  await page.getByRole("button", { name: /create/i }).click();
  await page.waitForURL(/\/w\/\d+/, { timeout: 5000 }).catch(() => {});
}
log("after ws url=", page.url());
await page.screenshot({ path: "/work/03-after-ws.png" });

const groupInput = page.getByPlaceholder("+ New group");
log("group input visible:", await groupInput.isVisible().catch(() => false));
await groupInput.fill("BotGroup");
await page.getByRole("button", { name: /^add$/i }).first().click();
await page.waitForTimeout(500);
await page.screenshot({ path: "/work/04-after-group.png" });

const epicInput = page.getByPlaceholder("+ New epic");
log("epic input visible:", await epicInput.isVisible().catch(() => false));
if (await epicInput.isVisible().catch(() => false)) {
  await epicInput.fill("BotEpic");
  await page.getByRole("button", { name: /^add$/i }).nth(1).click();
  await page.waitForTimeout(500);
}
await page.screenshot({ path: "/work/05-after-epic.png" });

const taskInput = page.getByPlaceholder(/add task/i);
log("task input visible:", await taskInput.isVisible().catch(() => false));
if (await taskInput.isVisible().catch(() => false)) {
  await taskInput.first().click();
  await page.keyboard.type("First task");
  await page.keyboard.press("Enter");
  await page.waitForTimeout(500);
}
await page.screenshot({ path: "/work/06-after-task.png" });

const cards = await page.getByText("First task").count();
log("cards with title 'First task':", cards);

await browser.close();
log("done");
