// ============================================
// دوال مساعدة (Utility Functions)
// ============================================

function getLang() {
    return localStorage.getItem('userLang') || 'ar';
}

function getDeviceFingerprint() {
    // بصمة الجهاز البسيطة
    const fingerprint = navigator.userAgent + navigator.language + screen.colorDepth;
    let hash = 0;
    for (let i = 0; i < fingerprint.length; i++) {
        const char = fingerprint.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
    }
    return Math.abs(hash).toString(16);
}

function mapErrorMessage(message) {
    const lang = getLang();
    const errorMessages = {
        'Invalid credentials': lang === 'ar' ? 'البريد أو كلمة المرور غير صحيحة' : 'Invalid email or password',
        'Email already registered': lang === 'ar' ? 'البريد الإلكتروني مسجل مسبقاً' : 'Email already registered',
        'Phone number already registered': lang === 'ar' ? 'رقم الهاتف مسجل مسبقاً' : 'Phone number already registered',
        'Invalid OTP': lang === 'ar' ? 'رمز التحقق غير صحيح' : 'Invalid verification code',
        'OTP expired': lang === 'ar' ? 'انتهت صلاحية رمز التحقق' : 'Verification code expired',
        'User is banned': lang === 'ar' ? 'الحساب محظور، يرجى التواصل مع الدعم' : 'Account is banned',
        'Failed to fetch': lang === 'ar' ? 'فشل الاتصال بالسيرفر' : 'Failed to connect to server'
    };
    return errorMessages[message] || message;
}

function showMessage(elementId, message, type = 'error') {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerText = message;
        element.className = `mt-4 text-sm ${type === 'error' ? 'text-red-400' : 'text-teal-400'}`;
        setTimeout(() => {
            element.innerText = '';
        }, 5000);
    }
}

const translations = {
    ar: {
        title: "بوابة Space Z التعليمية",
        langBtn: "English",
        welcome: "بوابة Space Z التعليمية",
        subtitle: "أهلاً بك مجدداً، سجّل دخولك لتكمل رحلتك",
        labelUser: "البريد الإلكتروني أو الهاتف",
        labelPass: "كلمة المرور",
        loginBtn: "تسجيل الدخول",
        checking: "جاري التحقق...",
        or: "أو يمكنك الدخول عبر",
        noAccount: "ليس لديك حساب بعد؟",
        registerLink: "إنشاء حساب جديد",
        googleLang: "ar_EG",
        googleFail: "فشل تسجيل الدخول بواسطة جوجل",
        serverFail: "فشل الاتصال بالسيرفر",
        forgotBtn: "نسيت كلمة المرور؟",
        forgotTitle: "استعادة كلمة المرور",
        forgotDesc: "أدخل بريدك الإلكتروني لإرسال رمز التحقق",
        sendResetOtp: "إرسال رمز التحقق",
        resetPassword: "تغيير كلمة المرور"
    },
    en: {
        title: "Space Z Education Portal",
        langBtn: "عربي",
        welcome: "Space Z Education Portal",
        subtitle: "Welcome back, log in to continue your journey",
        labelUser: "Email or Phone Number",
        labelPass: "Password",
        loginBtn: "Login",
        checking: "Checking...",
        or: "Or log in with",
        noAccount: "Don't have an account yet?",
        registerLink: "Create a new account",
        googleLang: "en_US",
        googleFail: "Google login failed",
        serverFail: "Failed to connect to server",
        forgotBtn: "Forgot password?",
        forgotTitle: "Reset Password",
        forgotDesc: "Enter your email to receive a verification code",
        sendResetOtp: "Send verification code",
        resetPassword: "Change password"
    }
};

function showLoginMessage(message, type = "error") {
    showMessage("loginMessage", message, type);
}

function renderGoogleButton(lang) {
    const googleBtn = document.getElementById("googleLoginBtn");

    if (googleBtn && window.google) {
        googleBtn.innerHTML = "";

        google.accounts.id.renderButton(googleBtn, {
            theme: "outline",
            size: "large",
            width: 320,
            text: "continue_with",
            locale: lang
        });
    }
}

function updateUI(lang) {
    const trans = translations[lang];

    document.documentElement.setAttribute("lang", lang);
    document.documentElement.setAttribute("dir", lang === "ar" ? "rtl" : "ltr");
    document.title = trans.title;

    document.getElementById("langBtn").innerText = trans.langBtn;
    document.querySelector("main h1").innerText = trans.welcome;
    document.querySelector("main p").innerText = trans.subtitle;

    const labels = document.querySelectorAll("form label");
    labels[0].innerText = trans.labelUser;
    labels[1].innerText = trans.labelPass;

    document.querySelector("form button span").innerText = trans.loginBtn;
    document.getElementById("orText").innerText = trans.or;
    document.getElementById("noAccountText").innerText = trans.noAccount;
    document.getElementById("registerLink").innerText = trans.registerLink;
    document.getElementById("forgotPasswordBtn").innerText = trans.forgotBtn;

    document.querySelector("#forgotModal h2").innerText = trans.forgotTitle;
    document.getElementById("forgotDesc").innerText = trans.forgotDesc;
    document.querySelector("#sendResetOtpBtn span").innerText = trans.sendResetOtp;
    document.querySelector("#resetPasswordBtn span").innerText = trans.resetPassword;

    const idInput = document.getElementById("identifier");
    const formElement = document.getElementById("loginForm");
    const btnArrow = document.getElementById("btnArrow");

    if (lang === "en") {
        idInput.classList.remove("text-right");
        idInput.classList.add("text-left");
        formElement.classList.remove("text-right");
        formElement.classList.add("text-left");
        btnArrow.classList.remove("rotate-180");
    } else {
        idInput.classList.remove("text-left");
        idInput.classList.add("text-right");
        formElement.classList.remove("text-left");
        formElement.classList.add("text-right");
        btnArrow.classList.add("rotate-180");
    }

    renderGoogleButton(trans.googleLang);
}

function openPhoneModal() {
    document.getElementById("phoneModal").classList.remove("hidden");
    document.getElementById("phoneModal").classList.add("flex");
}

function closePhoneModal() {
    document.getElementById("phoneModal").classList.add("hidden");
    document.getElementById("phoneModal").classList.remove("flex");
}

function openForgotModal() {
    document.getElementById("forgotModal").classList.remove("hidden");
    document.getElementById("forgotModal").classList.add("flex");
    document.getElementById("forgotStepEmail").classList.remove("hidden");
    document.getElementById("forgotStepReset").classList.add("hidden");
    document.getElementById("forgotMessage").innerText = "";
}

function closeForgotModal() {
    document.getElementById("forgotModal").classList.add("hidden");
    document.getElementById("forgotModal").classList.remove("flex");
}

async function handleCredentialResponse(response) {
    const googleToken = response.credential;
    const deviceId = getDeviceFingerprint();

    try {
        const data = await API.googleLogin(googleToken, deviceId);

        saveSession(data, deviceId);

        if (data.requiresPhoneNumber) {
            openPhoneModal();
        } else {
            redirectByRole();
        }

    } catch (error) {
        console.error(error);
        showLoginMessage(mapErrorMessage(error.message || translations[lang].googleFail), "error");
    }
}

window.addEventListener("load", () => {
        const savedLang = localStorage.getItem("userLang") || "ar";

    document.getElementById("langBtn").addEventListener("click", () => {
        const newLang = getLang() === "ar" ? "en" : "ar";
        localStorage.setItem("userLang", newLang);
        updateUI(newLang);
    });

    document.getElementById("loginForm").addEventListener("submit", async (e) => {
        e.preventDefault();

        const lang = getLang();
        const identifier = document.getElementById("identifier").value.trim();
        const password = document.getElementById("password").value;
        const deviceId = getDeviceFingerprint();

        const loginBtn = document.querySelector("form button");
        const originalBtnText = loginBtn.innerHTML;

        loginBtn.disabled = true;
        loginBtn.innerHTML = `<span>${translations[lang].checking}</span>`;

        try {
            const data = await API.login(identifier, password, deviceId);
            saveSessionAndRedirect(data, deviceId);
        } catch (error) {
            console.error(error);
            showLoginMessage(mapErrorMessage(error.message), "error");
        } finally {
            loginBtn.disabled = false;
            loginBtn.innerHTML = originalBtnText;
        }
    });

    document.getElementById("savePhoneBtn").addEventListener("click", async () => {
        const phone = document.getElementById("completePhoneInput").value.trim();
        const msg = document.getElementById("phoneMessage");

        if (!phone) {
            msg.innerText = getLang() === "ar" ? "أدخل رقم الهاتف" : "Enter phone number";
            msg.className = "mt-4 text-sm text-red-400";
            return;
        }

        try {
            await API.completePhone(phone);

            const user = getUser();
            user.phoneNumber = phone;
            localStorage.setItem("user", JSON.stringify(user));

            redirectByRole();
        } catch (error) {
            console.error(error);
            msg.innerText = mapErrorMessage(error.message);
            msg.className = "mt-4 text-sm text-red-400";
        }
    });

    document.getElementById("forgotPasswordBtn").addEventListener("click", () => {
        const identifierValue = document.getElementById("identifier").value.trim();

        if (identifierValue.includes("@")) {
            document.getElementById("forgotEmailInput").value = identifierValue;
        }

        openForgotModal();
    });

    document.getElementById("sendResetOtpBtn").addEventListener("click", async () => {
        const email = document.getElementById("forgotEmailInput").value.trim();
        const msg = document.getElementById("forgotMessage");
        const btn = document.getElementById("sendResetOtpBtn");
        const originalText = btn.innerHTML;

        if (!email) {
            msg.innerText = "أدخل البريد الإلكتروني";
            msg.className = "mt-4 text-sm text-red-400";
            return;
        }

        btn.disabled = true;
        btn.innerHTML = "جاري الإرسال...";

        try {
            await API.forgotPassword(email);

            msg.innerText = "تم إرسال رمز التحقق إلى بريدك";
            msg.className = "mt-4 text-sm text-teal-400";

            document.getElementById("forgotStepEmail").classList.add("hidden");
            document.getElementById("forgotStepReset").classList.remove("hidden");

        } catch (error) {
            console.error(error);
            msg.innerText = mapErrorMessage(error.message);
            msg.className = "mt-4 text-sm text-red-400";
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    });

    document.getElementById("resetPasswordBtn").addEventListener("click", async () => {
        const email = document.getElementById("forgotEmailInput").value.trim();
        const otp = document.getElementById("resetOtpInput").value.trim();
        const newPassword = document.getElementById("newPasswordInput").value;
        const msg = document.getElementById("forgotMessage");
        const btn = document.getElementById("resetPasswordBtn");
        const originalText = btn.innerHTML;

        if (!otp || !newPassword) {
            msg.innerText = "أدخل الرمز وكلمة المرور الجديدة";
            msg.className = "mt-4 text-sm text-red-400";
            return;
        }

        btn.disabled = true;
        btn.innerHTML = "جاري التغيير...";

        try {
            await API.resetPassword(email, otp, newPassword);

            msg.innerText = "تم تغيير كلمة المرور بنجاح، يمكنك تسجيل الدخول الآن";
            msg.className = "mt-4 text-sm text-teal-400";

            setTimeout(() => {
                closeForgotModal();
            }, 1500);

        } catch (error) {
            console.error(error);
            msg.innerText = mapErrorMessage(error.message);
            msg.className = "mt-4 text-sm text-red-400";
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    });

    document.getElementById("phoneModal").addEventListener("click", (e) => {
        if (e.target.id === "phoneModal") {
            closePhoneModal();
        }
    });

    document.querySelector("#phoneModal .modal-close-btn").addEventListener("click", () => {
        closePhoneModal();
    });

    document.getElementById("closeForgotModalBtn").addEventListener("click", () => {
        closeForgotModal();
    });

    document.getElementById("forgotModal").addEventListener("click", (e) => {
        if (e.target.id === "forgotModal") {
            closeForgotModal();
        }
    });

    window.handleCredentialResponse = handleCredentialResponse;

    if (window.google) {
        google.accounts.id.initialize({
            client_id: "872959715248-i7d0r6f7luj8vuraut76um6oaahgtj02.apps.googleusercontent.com",
            callback: handleCredentialResponse,
            use_fedcm: false
        });
    }

    updateUI(savedLang);
});