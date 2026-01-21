let apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Handle Render injecting the internal service name as the host
if (apiUrl === "daily-manager-backend") {
    apiUrl = "https://daily-manager-backend.onrender.com";
}

if (!apiUrl.startsWith("http")) {
    apiUrl = `https://${apiUrl}`;
}

export const API_BASE_URL = apiUrl;
