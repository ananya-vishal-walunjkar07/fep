// ============================================================
// CareerAI API Helper
// All backend calls go through these functions.
// ============================================================

function getApiBase() {
    // 1. Explicit window override
    if (window.CAREERAI_API_BASE) {
        return window.CAREERAI_API_BASE;
    }

    // 2. Query parameter override (e.g. ?api=local, ?api=render, or ?api=http://...)
    try {
        const urlParams = new URLSearchParams(window.location.search);
        const apiParam = urlParams.get("api") || urlParams.get("backend");
        if (apiParam) {
            if (apiParam === "local") return "http://127.0.0.1:8000";
            if (apiParam === "render" || apiParam === "production") return "https://career-ai-backend-a9ie.onrender.com";
            if (apiParam.startsWith("http://") || apiParam.startsWith("https://")) return apiParam;
        }
    } catch (_) {}

    // 3. Stored user preference
    try {
        const stored = localStorage.getItem("careerai_api_base");
        if (stored) return stored;
    } catch (_) {}

    // 4. Production Cloud Detection:
    // Only use Render if the page is explicitly served over HTTPS from a known cloud host
    const hostname = window.location.hostname || "";
    const protocol = window.location.protocol || "";

    const isProductionHost = protocol === "https:" && (
        hostname.endsWith(".onrender.com") ||
        hostname.endsWith(".vercel.app") ||
        hostname.endsWith(".netlify.app") ||
        hostname.endsWith(".github.io")
    );

    if (isProductionHost) {
        return "https://career-ai-backend-a9ie.onrender.com";
    }

    // Default to local backend for all local environments (localhost, 127.0.0.1, file:, 192.168.*, 10.*, 172.*, etc.)
    return "http://127.0.0.1:8000";
}

let API_BASE = getApiBase();

// ---- Token Storage ----
function getToken() {
    return localStorage.getItem("careerai_token");
}
function setToken(token) {
    localStorage.setItem("careerai_token", token);
}
function clearToken() {
    localStorage.removeItem("careerai_token");
    localStorage.removeItem("careerai_user");
    sessionStorage.removeItem("careerai_resume_id");
}

// ---- Auth Guard ---- 
// Call on every protected page's DOMContentLoaded
function requireAuth() {
    if (!getToken()) {
        window.location.href = "login.html";
        return false;
    }
    return true;
}

// ---- Base fetch wrapper ----
async function apiFetch(path, options = {}) {
    const token = getToken();
    const headers = {
        ...(options.headers || {}),
    };
    if (token) {
        headers["Authorization"] = "Bearer " + token;
    }
    if (!(options.body instanceof FormData)) {
        headers["Content-Type"] = "application/json";
    }

    try {
        const res = await fetch(API_BASE + path, { ...options, headers });

        if (res.status === 401) {
            clearToken();
            if (!window.location.pathname.endsWith("login.html") && !window.location.pathname.endsWith("signup.html")) {
                window.location.href = "login.html";
            }
            throw new Error("Invalid credentials or session expired.");
        }

        return res;
    } catch (err) {
        if (err.name === "TypeError" && (err.message.includes("fetch") || err.message.includes("NetworkError"))) {
            console.error(`CareerAI backend connection failed at ${API_BASE}${path}:`, err);

            // If Render backend failed and we are running in a browser that can reach localhost, try local fallback
            if (API_BASE.includes("onrender.com") && window.location.protocol !== "https:") {
                try {
                    console.warn("Render backend unreachable. Attempting fallback to local backend at http://127.0.0.1:8000...");
                    const fallbackRes = await fetch("http://127.0.0.1:8000" + path, { ...options, headers });
                    if (fallbackRes) {
                        API_BASE = "http://127.0.0.1:8000";
                        return fallbackRes;
                    }
                } catch (_) {}
            }

            if (API_BASE.includes("127.0.0.1") || API_BASE.includes("localhost")) {
                throw new Error(`Unable to connect to local backend at ${API_BASE}. Make sure the backend server is running (uvicorn main:app --port 8000).`);
            } else {
                throw new Error(`Unable to connect to production backend at ${API_BASE}. The service is currently inactive on Render (x-render-routing: no-server). Please resume or redeploy it in your Render dashboard.`);
            }
        }
        throw err;
    }
}

// ---- Auth ----
async function apiSignup(name, email, password) {
    const res = await apiFetch("/auth/signup", {
        method: "POST",
        body: JSON.stringify({ name, email, password, user_type: "student" }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Signup failed.");
    return data; // { id, email, name, user_type }
}

async function apiLogin(email, password) {
    const res = await apiFetch("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Login failed.");
    setToken(data.access_token);
    return data;
}

// ---- Users ----
async function apiGetMe() {
    const res = await apiFetch("/users/me");
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Could not load profile.");
    return data; // { id, email, name, user_type }
}

async function apiUpdateMe(name) {
    const res = await apiFetch("/users/me", {
        method: "PUT",
        body: JSON.stringify({ name }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Could not update profile.");
    return data;
}

// ---- Resumes ----
async function apiUploadResume(file) {
    // file = File object from <input type="file">
    const formData = new FormData();
    formData.append("file", file);
    const res = await apiFetch("/resumes/upload", {
        method: "POST",
        body: formData,
        headers: {}, // let browser set Content-Type for multipart
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Resume upload failed.");
    return data; // ResumeOut: { id, source, content_json, file_url, created_at }
}

async function apiGetResume() {
    const res = await apiFetch("/resumes/");
    if (res.status === 404) return null;
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Could not load resume.");
    return data; // ResumeOut
}

// ---- Reports (ATS) ----
async function apiGetReports(resumeId) {
    const res = await apiFetch(`/reports/resume/${resumeId}`);
    if (res.status === 404) return [];
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Could not load reports.");
    return data; // list[ReportOut]
}

async function apiGenerateAtsReport(resumeId, jobDescription = null) {
    const params = jobDescription
        ? `?job_description=${encodeURIComponent(jobDescription)}`
        : "";
    const res = await apiFetch(`/reports/generate/${resumeId}${params}`, {
        method: "POST",
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "ATS report generation failed.");
    return data; // ReportOut
}

// ---- Interview ----
async function apiStartInterview() {
    const res = await apiFetch("/interview/start", { method: "POST" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Could not start interview.");
    return data; // { success, question }
}

async function apiSubmitAnswer(answer) {
    const res = await apiFetch("/interview/answer", {
        method: "POST",
        body: JSON.stringify({ answer }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Could not submit answer.");
    return data; // { success, completed, next_question }
}

async function apiTranscribeSpeech(audioBlob) {
    // audioBlob = Blob from MediaRecorder (WAV)
    const res = await apiFetch("/speech/transcribe", {
        method: "POST",
        body: audioBlob,
        headers: { "Content-Type": "audio/wav" },
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Transcription failed.");
    return data; // { success, text }
}

// ---- Jobs ----
async function apiGetJobs() {
    const res = await apiFetch("/jobs");
    const data = await res.json();
    if (!res.ok) throw new Error("Could not load jobs.");
    return data.jobs; // array of job objects
}

// ---- Job Matching ----
async function apiMatchJob(jobTitle, jobDescription) {
    const res = await apiFetch("/applications/match", {
        method: "POST",
        body: JSON.stringify({
            job_title: jobTitle,
            company_name: "CareerAI Opportunity",
            job_description: jobDescription,
        }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Matching failed.");
    return data; // JobMatchOut
}

// ---- Applications ----
async function apiApplyJob(jobTitle, companyName, jobUrl) {
    const res = await apiFetch("/applications/apply", {
        method: "POST",
        body: JSON.stringify({
            job_title: jobTitle,
            company_name: companyName,
            job_url: jobUrl || "",
        }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Application failed.");
    return data;
}