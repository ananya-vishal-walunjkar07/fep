// ============================================================
// CareerAI API Helper
// All backend calls go through these functions.
// ============================================================

const API_BASE = window.CAREERAI_API_BASE || 
    (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" 
        ? "http://127.0.0.1:8000" 
        : window.location.origin);

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

    const res = await fetch(API_BASE + path, { ...options, headers });

    if (res.status === 401) {
        clearToken();
        window.location.href = "login.html";
        throw new Error("Session expired. Please log in again.");
    }

    return res;
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
