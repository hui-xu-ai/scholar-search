/* scholar-search bridge — service worker.
 *
 * Relays actions from the native host to one bound tab. The extension only
 * accepts hosts inside its configured scope (the selected channel); the kernel
 * and native host enforce the same list independently.
 */

const HOST_NAME = "com.scholar.search";
const PROTOCOL_VERSION = 1;
const DEFAULT_DOMAINS = ["kns.cnki.net", "www.cnki.net"];

let port = null;
let boundTabId = null;

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

function allowedHost(hostname, domains) {
  const host = String(hostname || "").toLowerCase();
  return domains.some((domain) => {
    const value = String(domain).toLowerCase();
    return host === value || host.endsWith(`.${value}`);
  });
}

function domainsFor(message) {
  const supplied = message && Array.isArray(message.domains) ? message.domains : [];
  return supplied.length ? supplied : DEFAULT_DOMAINS;
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
  const domains = domainsFor(message);
  const reply = (payload) => channel.postMessage({ type: "action_result", id, ...payload });

  try {
    if (action === "goto") {
      const url = new URL(params.url);
      if (url.protocol !== "https:" || !allowedHost(url.hostname, domains)) {
        throw new Error("policy.domain");
      }
      const tab = await activeTab();
      if (!tab || !tab.id) throw new Error("no_active_tab");
      await chrome.tabs.update(tab.id, { url: params.url });
      await waitComplete(tab.id);

      const updated = await chrome.tabs.get(tab.id);
      if (!allowedHost(new URL(updated.url || params.url).hostname, domains)) {
        throw new Error("policy.domain");
      }
      boundTabId = updated.id;
      const meta = await pageMeta(updated.id);
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

    const tabId = boundTabId !== null ? boundTabId : (await activeTab())?.id;
    if (!tabId) throw new Error("no_active_tab");
    if (boundTabId !== null) {
      const current = await chrome.tabs.get(tabId).catch(() => null);
      if (!current || !allowedHost(new URL(current.url).hostname, domains)) {
        throw new Error("policy.tab_scope");
      }
    }

    const result = await chrome.tabs.sendMessage(tabId, {
      type: "dom_action",
      action,
      params,
    });
    if (!result) throw new Error("dom_failed");
    return reply({ ok: Boolean(result.ok), error: result.error, data: result.data || {} });
  } catch (error) {
    return reply({ ok: false, error: String((error && error.message) || error) });
  }
}

chrome.runtime.onInstalled.addListener(connect);
chrome.runtime.onStartup.addListener(connect);
connect();
