function getToken() {
    return localStorage.getItem("token");
}

function getUser() {
    return JSON.parse(localStorage.getItem("user") || "{}");
}

function saveSession(data, deviceId = null) {
    localStorage.setItem("token", data.token);
    localStorage.setItem("user", JSON.stringify(data.user || {}));

    if (deviceId) {
        localStorage.setItem("deviceId", deviceId);
    }
}

function redirectByRole() {
    const user = getUser();

    if (user.role && user.role.toLowerCase() === "admin") {
        window.location.href = "admin-dashboard.html";
    } else {
        window.location.href = "dashboard.html";
    }
}

function saveSessionAndRedirect(data, deviceId = null) {
    saveSession(data, deviceId);
    redirectByRole();
}

function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    localStorage.removeItem("deviceId");
    window.location.href = "login.html";
}

function requireLogin() {
    if (!getToken()) {
        window.location.href = "login.html";
    }
}