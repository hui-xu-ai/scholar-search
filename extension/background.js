/* scholar-search bridge — service worker.
 *
 * Relays actions from the native host to the active tab. It knows no site
 * structure: the kernel and the channel manifest decide which hosts and DOM
 * selectors are legitimate.
 */

const HOST_NAME = "com.scholar.search";
const PROTOCOL_VERSION = 1;

let port = null;

function connect() {
  if (port) return;
  try {
    const channel = chrome.runtime.connectNative(HOST_NAME);
    port = channel;
    channel.onMessage.addListener((message) => onHostMessage(message, channel));
    channel.onDisconnect.addListener(() => {
      if (port === channel) port = null;
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

async function pageMeta(tabId) {
  try {
    const result = await chrome.tabs.sendMessage(tabId, { type: "meta" });
    return (result && result.data) || {};
  } catch (error) {
    return {};
  }
}

async function onHostMessage(message, channel) {
  if (!message) return;

  if (message.type === "hello") {
    channel.postMessage({
      type: "hello_ack",
      id: message.id,
      protocol: PROTOCOL_VERSION,
    });
    return;
  }
  if (message.type !== "action") return;

  const { id, action, params } = message;
  const reply = (payload) => channel.postMessage({ type: "action_result", id, ...payload });

  try {
    const tab = await activeTab();
    if (!tab || !tab.id) throw new Error("no_active_tab");

    if (action === "goto") {
      const url = new URL(params.url);
      if (url.protocol !== "https:") throw new Error("policy.url_scheme");
      await chrome.tabs.update(tab.id, { url: params.url });
      await waitComplete(tab.id);

      const updated = await chrome.tabs.get(tab.id);
      const meta = await pageMeta(tab.id);
      const status = Number(meta.status || 0);
      if (status >= 400) throw new Error(`HTTP ${status}`);
      return reply({
        ok: true,
        data: {
          ...meta,
          url: updated.url || params.url,
          title: updated.title || "",
          status: status || undefined,
        },
      });
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
connect();
