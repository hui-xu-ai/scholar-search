/* scholar-search bridge — content script.
 *
 * Implements the nine generic verbs. No channel selectors are hard-coded: the
 * caller passes selectors in the action parameters.
 *
 * Every reply — success, failure or missing element — carries a risk snapshot,
 * and actions with side effects are refused while a captcha or login gate is
 * already visible.
 */

const MAX_HTML_BYTES = 1_000_000;

const CAPTCHA_SELECTORS = [
  "#tcaptcha_transform_dy",
  "[id*='captcha' i]",
  "[class*='captcha' i]",
];
const LOGIN_SELECTORS = [
  "#Ecp_top_login_realName",
  "#Ecp_top_login_oversea",
  "[id*='login-modal' i]",
  "[class*='login-modal' i]",
];

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isVisible(element) {
  if (!element) return false;
  try {
    const style = getComputedStyle(element);
    if (style && (style.display === "none" || style.visibility === "hidden")) return false;
    if (typeof element.getBoundingClientRect !== "function") return false;
    const rect = element.getBoundingClientRect();
    if (!rect || rect.width <= 0 || rect.height <= 0) return false;
    const top = typeof rect.top === "number" ? rect.top : 0;
    const bottom = typeof rect.bottom === "number" ? rect.bottom : top + rect.height;
    const viewport = (window && window.innerHeight) || Infinity;
    return bottom > 0 && top < viewport;
  } catch (error) {
    return false;
  }
}

function isPresent(element) {
  if (!element) return false;
  return isVisible(element) || typeof element.getBoundingClientRect !== "function";
}

function anyVisible(selectors) {
  for (const selector of selectors) {
    try {
      if (typeof document.querySelectorAll === "function") {
        for (const element of document.querySelectorAll(selector)) {
          if (isVisible(element)) return true;
        }
        continue;
      }
    } catch (error) {
      // Fall through to the single-element query below.
    }
    try {
      if (isVisible(document.querySelector(selector))) return true;
    } catch (error) {
      // A selector the page does not support is simply skipped.
    }
  }
  return false;
}

async function waitFor(selector, timeoutMs, state) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    let matched = false;
    try {
      matched = isPresent(document.querySelector(selector));
    } catch (error) {
      matched = false;
    }
    if (state === "hidden" ? !matched : matched) return true;
    await sleep(100);
  }
  return false;
}

function utf8Length(text, limit) {
  let bytes = 0;
  for (let index = 0; index < text.length; index += 1) {
    const code = text.codePointAt(index) || 0;
    if (code > 0xffff) index += 1;
    bytes += code <= 0x7f ? 1 : code <= 0x7ff ? 2 : code <= 0xffff ? 3 : 4;
    if (bytes > limit) return index + 1;
  }
  return text.length;
}

function riskSnapshot() {
  return {
    captcha_visible: anyVisible(CAPTCHA_SELECTORS),
    auth_required: anyVisible(LOGIN_SELECTORS),
    title: document.title,
    url: window && window.location ? String(window.location.href) : undefined,
    status: (function () {
      try {
        const entry = performance.getEntriesByType("navigation")[0];
        return entry && entry.responseStatus ? entry.responseStatus : undefined;
      } catch (error) {
        return undefined;
      }
    })(),
  };
}

function withRisk(result) {
  return { ...result, data: { ...(result.data || {}), ...riskSnapshot() } };
}

function riskPresent() {
  const snapshot = riskSnapshot();
  return snapshot.captcha_visible || snapshot.auth_required;
}

async function run(action, params) {
  let result;
  switch (action) {
    case "wait_for": {
      const state = params.state || "visible";
      const matched = await waitFor(params.selector, params.timeout_ms || 10000, state);
      result = { ok: matched, data: { matched }, error: matched ? undefined : "timeout" };
      break;
    }
    case "type": {
      if (riskPresent()) return withRisk({ ok: false, error: "risk.present" });
      const element = document.querySelector(params.selector);
      if (!element) {
        result = { ok: false, error: "not_found" };
        break;
      }
      if (params.clear !== false) element.value = "";
      element.value = params.text;
      element.dispatchEvent(new Event("input", { bubbles: true }));
      element.dispatchEvent(new Event("change", { bubbles: true }));
      result = { ok: true, data: {} };
      break;
    }
    case "click": {
      if (riskPresent()) return withRisk({ ok: false, error: "risk.present" });
      const element = document.querySelector(params.selector);
      if (!element) {
        result = { ok: false, error: "not_found" };
        break;
      }
      element.click();
      result = { ok: true, data: {} };
      break;
    }
    case "select": {
      if (riskPresent()) return withRisk({ ok: false, error: "risk.present" });
      const element = document.querySelector(params.selector);
      if (!element) {
        result = { ok: false, error: "not_found" };
        break;
      }
      element.value = params.value;
      element.dispatchEvent(new Event("change", { bubbles: true }));
      result = { ok: true, data: {} };
      break;
    }
    case "read_html": {
      const html = document.documentElement.outerHTML;
      const cut = utf8Length(html, MAX_HTML_BYTES);
      const truncated = cut < html.length;
      result = {
        ok: true,
        data: { html: truncated ? html.slice(0, cut) : html, truncated },
      };
      break;
    }
    case "read_text": {
      const element = document.querySelector(params.selector);
      if (!element) {
        result = { ok: false, error: "not_found" };
        break;
      }
      result = { ok: true, data: { text: (element.innerText || "").trim() } };
      break;
    }
    case "scroll": {
      window.scrollTo(0, params.to === "top" ? 0 : document.body.scrollHeight);
      result = { ok: true, data: {} };
      break;
    }
    case "sleep": {
      await sleep(Math.min(params.ms || 0, 3000));
      result = { ok: true, data: {} };
      break;
    }
    default:
      result = { ok: false, error: "policy.verb" };
  }
  return withRisk(result);
}

function meta() {
  return { ok: true, data: riskSnapshot() };
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message) return undefined;
  if (message.type === "meta") {
    sendResponse(meta());
    return undefined;
  }
  if (message.type !== "dom_action") return undefined;
  run(message.action, message.params || {})
    .then(sendResponse)
    .catch((error) => sendResponse({ ok: false, error: String(error), data: riskSnapshot() }));
  return true;
});
