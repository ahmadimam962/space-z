function getLang() {
    return document.documentElement.getAttribute("lang") || "ar";
}

function getDeviceFingerprint() {
    const navigatorInfo =
        window.navigator.userAgent +
        window.navigator.language +
        window.screen.colorDepth +
        window.screen.width +
        window.screen.height;

    let hash = 0;

    for (let i = 0; i < navigatorInfo.length; i++) {
        hash = ((hash << 5) - hash) + navigatorInfo.charCodeAt(i);
        hash |= 0;
    }

    return "DEV-" + Math.abs(hash);
}

function mapErrorMessage(detail) {
    const lang = getLang();

    if (!detail) {
        return lang === "ar" ? "فشل الاتصال بالسيرفر" : "Server connection failed";
    }

    if (detail === "Invalid credentials") {
        return lang === "ar"
            ? "البريد أو كلمة المرور غير صحيحة"
            : "Email/phone or password is incorrect";
    }

    if (detail === "Account is banned") {
        return lang === "ar"
            ? "تم حظر هذا الحساب"
            : "This account is banned";
    }

    if (detail.includes("Device limit reached")) {
        return lang === "ar"
            ? "تم الوصول للحد الأقصى: الحساب يعمل على جهازين فقط"
            : "Device limit reached: this account can only be used on 2 devices";
    }

    if (detail === "Please login with Google") {
        return lang === "ar"
            ? "هذا الحساب مسجل بواسطة جوجل، استخدم زر جوجل للدخول"
            : "This account uses Google login. Please use Google sign-in.";
    }

    if (detail === "Phone already exists") {
        return lang === "ar"
            ? "رقم الهاتف مستخدم بالفعل"
            : "Phone number already exists";
    }

    return detail;
}

function showMessage(elementId, message, type = "error") {
    const msg = document.getElementById(elementId);

    if (!msg) return;

    msg.innerText = message;
    msg.classList.remove("hidden", "text-red-400", "text-teal-400", "text-zinc-400");

    if (type === "success") {
        msg.classList.add("text-teal-400");
    } else {
        msg.classList.add("text-red-400");
    }
}