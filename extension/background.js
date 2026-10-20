/* scholar-search bridge — service worker.
 *
 * Relays actions from the native host to the active tab. It knows no site
 * structure: every DOM decision arrives from the Python channel plugin.
 */

const HOST_NAME = "com.scholar.search";
const ALLOWED_HOST = /(^|\.)cnki\.net$/i;

let port = null;

function connect() {
  try {
    port = chrome.runtime.connectNative(HOST_NAME);
    port.onMessage.addListener(onHostMessage);
    port.onDisconnect.addListener(() => {
      port = null;
      setTimeout(connect, 3000);
    });
  } catch (error) {
    port = null;
    setTimeout(connect, 3000);
  }
}

async function activeTab() {
  const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  return tab;
}

function waitComplete(tabId, timeoutMs = 15000) {
  const deadline = Date.now() + timeoutMs;
  return new Promise((resolve, reject) => {
    const tick = async () => {
      try {
        const tab = await chrome.tabs.get(tabId);
        if (tab.status === "complete") return resolve();
      } catch (error) {
        return reject(error);
      }
      if (Date.now() > deadline) return reject(new Error("timeout.navigation"));
      setTimeout(tick, 250);
    };
    tick();
  });
}

async function onHostMessage(message) {
  if (!message || message.type !== "action") return;

  const { id, action, params } = message;
  const reply = (payload) =>
    port && port.postMessage({ type: "action_result", id, ...payload });

  try {
    const tab = await activeTab();
    if (!tab || !tab.id) throw new Error("no_active_tab");

    if (action === "goto") {
      const url = new URL(params.url);
      if (url.protocol !== "https:" || !ALLOWED_HOST.test(url.hostname)) {
        throw new Error("policy.domain");
      }
      await chrome.tabs.update(tab.id, { url: params.url });
      await waitComplete(tab.id);
      return reply({ ok: true, data: { url: params.url, title: tab.title || "" } });
    }

    const result = await chrome.tabs.sendMessage(tab.id, {
      type: "dom_action",
      action,
      params,
    });
    if (!result || !result.ok) throw new Error((result && result.error) || "dom_failed");
    return reply({ ok: true, data: result.data || {} });
  } catch (error) {
    return reply({ ok: false, error: String((error && error.message) || error) });
  }
}

chrome.runtime.onInstalled.addListener(connect);
chrome.runtime.onStartup.addListener(connect);
chrome.alarms.create("keepalive", { periodInMinutes: 1 });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "keepalive" && !port) connect();
});
connect();
