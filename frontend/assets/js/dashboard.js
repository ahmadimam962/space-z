async function loadDashboardProfile() {
    try {
        const result = await API.getProfile();

        if (result.success && result.data) {
            const firstName =
                result.data.firstName ||
                result.data.first_name ||
                result.data.name ||
                "...";

            const userNameEl = document.getElementById("userName");

            if (userNameEl) {
                userNameEl.innerText = firstName;
            }
        }

    } catch (err) {
        console.error("Error loading profile:", err);

        if (err.message.includes("401") || err.message.includes("Unauthorized")) {
            logout();
        }
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    requireLogin();

    const savedLang = localStorage.getItem("userLang") || "ar";

    initLanguageToggle();

    await loadDashboardProfile();

    applyLanguage(savedLang);

    await loadNotifications();
    await loadPurchaseHistory();
});