/* scholar-search bridge — content script.
 *
 * Implements the nine generic verbs. No selectors are hard-coded here; they
 * always arrive in the action parameters.
 */

const MAX_HTML_CHARS = 1_500_000;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitFor(selector, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (document.querySelector(selector)) return true;
    await sleep(200);
  }
  return false;
}

async function run(action, params) {
  switch (action) {
    case "wait_for": {
      const matched = await waitFor(params.selector, params.timeout_ms || 10000);
      return { ok: matched, data: { matched }, error: matched ? undefined : "timeout" };
    }
    case "type": {
      const element = document.querySelector(params.selector);
      if (!element) return { ok: false, error: "not_found" };
      if (params.clear !== false) element.value = "";
      element.value = params.text;
      element.dispatchEvent(new Event("input", { bubbles: true }));
      return { ok: true, data: {} };
    }
    case "click": {
      const element = document.querySelector(params.selector);
      if (!element) return { ok: false, error: "not_found" };
      element.click();
      return { ok: true, data: {} };
    }
    case "select": {
      const element = document.querySelector(params.selector);
      if (!element) return { ok: false, error: "not_found" };
      element.value = params.value;
      element.dispatchEvent(new Event("change", { bubbles: true }));
      return { ok: true, data: {} };
    }
    case "read_html": {
      const html = document.documentElement.outerHTML;
      return { ok: true, data: { html: html.slice(0, MAX_HTML_CHARS) } };
    }
    case "read_text": {
      const element = document.querySelector(params.selector);
      if (!element) return { ok: false, error: "not_found" };
      return { ok: true, data: { text: (element.innerText || "").trim() } };
    }
    case "scroll": {
      window.scrollTo(0, params.to === "top" ? 0 : document.body.scrollHeight);
      return { ok: true, data: {} };
    }
    case "sleep": {
      await sleep(Math.min(params.ms || 0, 3000));
      return { ok: true, data: {} };
    }
    default:
      return { ok: false, error: "policy.verb" };
  }
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || message.type !== "dom_action") return undefined;
  run(message.action, message.params || {})
    .then(sendResponse)
    .catch((error) => sendResponse({ ok: false, error: String(error) }));
  return true;
});
