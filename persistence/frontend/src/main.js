import { Streamlit } from "streamlit-component-lib";
import { createClient } from "@supabase/supabase-js";

const allowedKeys = [
  "resume_text",
  "jd_text",
  "interview_history",
  "language",
  "supabase_session",
];
const oauthStorageKey = "hiresense-supabase-google-oauth";
let lastOperation = "";

function prefix(namespace) {
  return `hiresense:${encodeURIComponent(namespace || "local-user")}:`;
}

function storageName(namespace, key) {
  if (!allowedKeys.includes(key)) throw new Error("Unsupported storage key");
  return `${prefix(namespace)}${key}`;
}

function parseHistory(raw) {
  if (!raw) return [];
  try {
    const value = JSON.parse(raw);
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

function load(namespace) {
  return {
    status: "loaded",
    resume_text: localStorage.getItem(storageName(namespace, "resume_text")) || "",
    jd_text: localStorage.getItem(storageName(namespace, "jd_text")) || "",
    interview_history: parseHistory(
      localStorage.getItem(storageName(namespace, "interview_history")),
    ),
    language: localStorage.getItem(storageName(namespace, "language")) || "en",
  };
}

function loadAuth(namespace) {
  const raw = localStorage.getItem(
    storageName(namespace, "supabase_session"),
  );
  if (!raw) {
    return { status: "loaded", supabase_session: null };
  }
  try {
    const value = JSON.parse(raw);
    return {
      status: "loaded",
      supabase_session:
        value && typeof value === "object" && !Array.isArray(value)
          ? value
          : null,
    };
  } catch {
    return { status: "loaded", supabase_session: null };
  }
}

function save(namespace, key, value) {
  const serialized =
    typeof value === "string" ? value : JSON.stringify(value ?? "");
  localStorage.setItem(storageName(namespace, key), serialized);
}

function clear(namespace, key) {
  if (key === "ALL") {
    for (const item of allowedKeys) {
      localStorage.removeItem(storageName(namespace, item));
    }
    return;
  }
  localStorage.removeItem(storageName(namespace, key));
}

function clearGoogleOAuthArtifacts() {
  const keys = [];
  for (let index = 0; index < localStorage.length; index += 1) {
    const key = localStorage.key(index);
    if (key === oauthStorageKey || key?.startsWith(`${oauthStorageKey}-`)) {
      keys.push(key);
    }
  }
  for (const key of keys) localStorage.removeItem(key);
}

function oauthClient(args) {
  const url = String(args.supabase_url || "");
  const key = String(args.supabase_publishable_key || "");
  if (!url.startsWith("https://") || !key) {
    throw new Error("Google sign-in is not configured.");
  }
  return createClient(url, key, {
    auth: {
      autoRefreshToken: false,
      detectSessionInUrl: false,
      flowType: "pkce",
      persistSession: true,
      storageKey: oauthStorageKey,
    },
  });
}

function resolveRedirectUrl(override) {
  if (override) return String(override);
  try {
    const current = new URL(window.parent.location.href);
    current.search = "";
    current.hash = "";
    return current.toString();
  } catch {
    return "";
  }
}

function resetView() {
  document.body.replaceChildren();
  document.body.style.margin = "0";
  document.body.style.background = "transparent";
  document.body.style.fontFamily =
    'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
}

function googleButton(label, disabled = false) {
  const control = document.createElement("a");
  control.setAttribute("role", "button");
  control.setAttribute("aria-label", label);
  if (disabled) {
    control.setAttribute("aria-disabled", "true");
    control.style.pointerEvents = "none";
  } else {
    control.href = "#";
    // Streamlit custom components run in a sandboxed iframe that cannot
    // navigate the top-level page. A user-initiated new tab is permitted, so
    // the OAuth authorization page must open outside the component iframe.
    control.target = "_blank";
    control.rel = "noopener noreferrer";
  }
  control.style.alignItems = "center";
  control.style.background = disabled ? "#1b2030" : "#ffffff";
  control.style.border = disabled ? "1px solid #343a4d" : "1px solid #d6d9e0";
  control.style.borderRadius = "10px";
  control.style.boxSizing = "border-box";
  control.style.color = disabled ? "#98a0b3" : "#1f2430";
  control.style.cursor = disabled ? "wait" : "pointer";
  control.style.display = "flex";
  control.style.fontSize = "15px";
  control.style.fontWeight = "650";
  control.style.gap = "12px";
  control.style.height = "48px";
  control.style.justifyContent = "center";
  control.style.textDecoration = "none";
  control.style.width = "100%";

  const mark = document.createElement("span");
  mark.textContent = "G";
  mark.setAttribute("aria-hidden", "true");
  mark.style.color = disabled ? "#98a0b3" : "#4285f4";
  mark.style.fontSize = "20px";
  mark.style.fontWeight = "800";

  const text = document.createElement("span");
  text.textContent = label;
  control.append(mark, text);
  return control;
}

async function renderGoogleOAuthButton(args) {
  resetView();
  const control = googleButton("Preparing Google sign-in…", true);
  document.body.append(control);
  Streamlit.setFrameHeight(52);

  const redirectTo = resolveRedirectUrl(args.redirect_to);
  if (!redirectTo) {
    throw new Error("Set SUPABASE_OAUTH_REDIRECT_URL for Google sign-in.");
  }

  const client = oauthClient(args);
  const { data, error } = await client.auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo,
      skipBrowserRedirect: true,
      queryParams: { prompt: "select_account" },
    },
  });
  if (error || !data?.url) {
    throw new Error(error?.message || "Google sign-in could not start.");
  }

  const ready = googleButton("Continue with Google");
  ready.href = data.url;
  control.replaceWith(ready);
  Streamlit.setComponentValue({ status: "ready" });
}

async function exchangeGoogleOAuth(args) {
  resetView();
  Streamlit.setFrameHeight(0);
  const code = String(args.code || "");
  const flowId = String(args.flow_id || "");
  if (!code) throw new Error("The Google callback code is missing.");

  const client = oauthClient(args);
  const options = flowId ? { flowId } : undefined;
  const { data, error } = await client.auth.exchangeCodeForSession(
    code,
    options,
  );
  if (error || !data?.session || !data?.user) {
    clearGoogleOAuthArtifacts();
    throw new Error(error?.message || "Google sign-in could not be completed.");
  }

  const session = data.session;
  const user = data.user;
  localStorage.removeItem(oauthStorageKey);
  Streamlit.setComponentValue({
    status: "authenticated",
    session: {
      access_token: String(session.access_token || ""),
      refresh_token: String(session.refresh_token || ""),
      expires_at: Number(session.expires_at || 0),
      expires_in: Number(session.expires_in || 0),
      user: {
        id: String(user.id || ""),
        email: String(user.email || ""),
        app_metadata:
          user.app_metadata && typeof user.app_metadata === "object"
            ? user.app_metadata
            : {},
        user_metadata:
          user.user_metadata && typeof user.user_metadata === "object"
            ? user.user_metadata
            : {},
      },
    },
  });
}

async function handleRender(event) {
  const args = event.detail.args || {};
  const signature = JSON.stringify(args);
  if (signature === lastOperation) return;
  lastOperation = signature;

  try {
    if (args.operation === "load") {
      resetView();
      Streamlit.setComponentValue(load(args.namespace));
    } else if (args.operation === "load_auth") {
      resetView();
      Streamlit.setComponentValue(loadAuth(args.namespace));
    } else if (args.operation === "save") {
      resetView();
      save(args.namespace, args.storage_key, args.value);
    } else if (args.operation === "save_auth") {
      resetView();
      save(args.namespace, "supabase_session", args.value);
    } else if (args.operation === "clear") {
      resetView();
      clear(args.namespace, args.storage_key);
    } else if (args.operation === "clear_auth") {
      resetView();
      clear(args.namespace, "supabase_session");
    } else if (args.operation === "google_oauth_button") {
      await renderGoogleOAuthButton(args);
      return;
    } else if (args.operation === "exchange_google_oauth") {
      await exchangeGoogleOAuth(args);
      return;
    } else if (args.operation === "clear_google_oauth") {
      resetView();
      clearGoogleOAuthArtifacts();
    }
  } catch (error) {
    Streamlit.setComponentValue({
      status: "error",
      message: String(error?.message || error).slice(0, 300),
    });
  }
  Streamlit.setFrameHeight(0);
}

Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, (event) => {
  void handleRender(event);
});

Streamlit.setComponentReady();
Streamlit.setFrameHeight(0);
