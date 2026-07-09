function applyLanguage(lang) {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
    localStorage.setItem("userLang", lang);

    document.querySelectorAll("[data-en]").forEach(el => {
        if (el.tagName === "H1" && el.querySelector("#userName")) {
            const userName = document.getElementById("userName").innerText;
            const text = el.getAttribute(`data-${lang}`);
            el.innerHTML = `${text} <span id="userName" class="text-teal-400">${userName}</span> 👋`;
        } else {
            el.innerText = el.getAttribute(`data-${lang}`);
        }
    });

    if (typeof renderNotifications === "function") {
        renderNotifications();
    }

    if (typeof renderPurchases === "function") {
        renderPurchases();
    }
}

function initLanguageToggle() {
    const langToggle = document.getElementById("langToggle");
    if (!langToggle) return;

    langToggle.addEventListener("click", () => {
        const currentLang = document.documentElement.lang || "ar";
        const newLang = currentLang === "ar" ? "en" : "ar";
        applyLanguage(newLang);
    });
}