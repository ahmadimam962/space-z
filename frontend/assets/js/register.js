let currentEmail = "";
let resendTimer = null;
let resendSeconds = 40;

const registerTranslations = {
    ar: {
        title: "إنشاء حساب - Space Z",
        langBtn: "English",
        mainTitle: "انضم إلى بوابة Space Z",
        subTitle: "أنشئ حسابك الجديد لتكون جزءاً من رحلتنا",
        fName: "الاسم الأول",
        lName: "الاسم الأخير",
        email: "البريد الإلكتروني",
        phone: "رقم الهاتف",
        pass: "كلمة المرور",
        btn: "إنشاء الحساب ←",
        haveAcc: "لديك حساب بالفعل؟",
        logLink: "تسجيل الدخول",
        otpTitle: "تحقق من بريدك",
        otpDesc: "أدخل رمز التحقق المرسل إلى بريدك الإلكتروني",
        verifyBtn: "تأكيد الحساب",
        sending: "جاري إرسال رمز التحقق...",
        verifying: "جاري التحقق...",
        resendAfter: "إعادة الإرسال بعد",
        resend: "إعادة إرسال الرمز",
        accountDone: "تم تفعيل الحساب بنجاح",
        serverFail: "فشل الاتصال بالسيرفر",
        fillAll: "يرجى تعبئة جميع الحقول",
        otpRequired: "أدخل رمز التحقق"
    },
    en: {
        title: "Sign Up - Space Z",
        langBtn: "عربي",
        mainTitle: "Join Space Z Portal",
        subTitle: "Create your account to be part of our journey",
        fName: "First Name",
        lName: "Last Name",
        email: "Email",
        phone: "Phone Number",
        pass: "Password",
        btn: "Sign Up ←",
        haveAcc: "Already have an account?",
        logLink: "Log In",
        otpTitle: "Verify your email",
        otpDesc: "Enter the verification code sent to your email",
        verifyBtn: "Verify Account",
        sending: "Sending...",
        verifying: "Verifying...",
        resendAfter: "Resend after",
        resend: "Resend code",
        accountDone: "Account verified successfully",
        serverFail: "Failed to connect",
        fillAll: "Please fill all fields",
        otpRequired: "Enter verification code"
    }
};

function getRegisterLang() {
    return document.documentElement.getAttribute("lang") || "ar";
}

function applyRegisterLanguage(lang) {
    const t = registerTranslations[lang];

    document.documentElement.setAttribute("lang", lang);
    document.documentElement.setAttribute("dir", lang === "ar" ? "rtl" : "ltr");

    document.title = t.title;
    document.getElementById("langBtn").innerText = t.langBtn;
    document.getElementById("mainTitle").innerText = t.mainTitle;
    document.getElementById("subTitle").innerText = t.subTitle;

    document.getElementById("firstName").placeholder = t.fName;
    document.getElementById("lastName").placeholder = t.lName;
    document.getElementById("email").placeholder = t.email;
    document.getElementById("phoneNumber").placeholder = t.phone;
    document.getElementById("password").placeholder = t.pass;

    document.getElementById("submitBtn").innerText = t.btn;
    document.getElementById("haveAccount").innerText = t.haveAcc;
    document.getElementById("loginLink").innerText = t.logLink;

    document.getElementById("otpTitle").innerText = t.otpTitle;
    document.getElementById("otpDesc").innerText = t.otpDesc;
    document.getElementById("verifyOtpBtn").innerText = t.verifyBtn;

    localStorage.setItem("userLang", lang);
}

function showFormMessage(message, type = "error") {
    showMessage("formMessage", message, type);
}

function showOtpMessage(message, type = "error") {
    const msg = document.getElementById("otpMessage");
    msg.innerText = message;
    msg.className = type === "success"
        ? "mt-4 text-sm text-teal-400"
        : "mt-4 text-sm text-red-400";
}

function openOtpModal() {
    document.getElementById("otpModal").classList.remove("hidden");
    document.getElementById("otpModal").classList.add("flex");
}

function startResendTimer() {
    const btn = document.getElementById("resendOtpBtn");
    const lang = getRegisterLang();
    const t = registerTranslations[lang];

    resendSeconds = 40;
    btn.disabled = true;
    btn.classList.add("cursor-not-allowed", "text-zinc-400");
    btn.classList.remove("text-teal-400");

    btn.innerText = `${t.resendAfter} ${resendSeconds} ${lang === "ar" ? "ثانية" : "seconds"}`;

    clearInterval(resendTimer);

    resendTimer = setInterval(() => {
        resendSeconds--;

        btn.innerText = `${t.resendAfter} ${resendSeconds} ${lang === "ar" ? "ثانية" : "seconds"}`;

        if (resendSeconds <= 0) {
            clearInterval(resendTimer);
            btn.disabled = false;
            btn.innerText = t.resend;
            btn.classList.remove("cursor-not-allowed", "text-zinc-400");
            btn.classList.add("text-teal-400");
        }
    }, 1000);
}

document.addEventListener("DOMContentLoaded", () => {
    applyRegisterLanguage(localStorage.getItem("userLang") || "ar");

    document.getElementById("langBtn").addEventListener("click", () => {
        const newLang = getRegisterLang() === "ar" ? "en" : "ar";
        applyRegisterLanguage(newLang);
    });

    document.getElementById("signupForm").addEventListener("submit", async (e) => {
        e.preventDefault();

        const lang = getRegisterLang();
        const t = registerTranslations[lang];

        const firstName = document.getElementById("firstName").value.trim();
        const lastName = document.getElementById("lastName").value.trim();
        const email = document.getElementById("email").value.trim();
        const phoneNumber = document.getElementById("phoneNumber").value.trim();
        const password = document.getElementById("password").value;

        const btn = document.getElementById("submitBtn");
        const originalText = btn.innerText;

        if (!firstName || !lastName || !email || !phoneNumber || !password) {
            showFormMessage(t.fillAll, "error");
            return;
        }

        btn.disabled = true;
        btn.innerText = t.sending;

        try {
            await API.register({
                first_name: firstName,
                last_name: lastName,
                email: email,
                phone_number: phoneNumber,
                password: password
            });

            currentEmail = email;
            showFormMessage("", "success");
            openOtpModal();
            startResendTimer();

        } catch (error) {
            console.error(error);
            showFormMessage(mapErrorMessage(error.message), "error");
        } finally {
            btn.disabled = false;
            btn.innerText = originalText;
        }
    });

    document.getElementById("verifyOtpBtn").addEventListener("click", async () => {
        const lang = getRegisterLang();
        const t = registerTranslations[lang];

        const otp = document.getElementById("otpInput").value.trim();
        const btn = document.getElementById("verifyOtpBtn");
        const originalText = btn.innerText;

        if (!otp) {
            showOtpMessage(t.otpRequired, "error");
            return;
        }

        btn.disabled = true;
        btn.innerText = t.verifying;

        try {
            await API.verifyOtp(currentEmail, otp);

            showOtpMessage(t.accountDone, "success");

            setTimeout(() => {
                window.location.href = "login.html";
            }, 1200);

        } catch (error) {
            console.error(error);
            showOtpMessage(mapErrorMessage(error.message), "error");
        } finally {
            btn.disabled = false;
            btn.innerText = originalText;
        }
    });

    document.getElementById("resendOtpBtn").addEventListener("click", async () => {
        if (!currentEmail) return;

        try {
            await API.resendOtp(currentEmail);
            showOtpMessage(
                getRegisterLang() === "ar"
                    ? "تم إرسال رمز جديد"
                    : "New code sent",
                "success"
            );
            startResendTimer();
        } catch (error) {
            console.error(error);
            showOtpMessage(mapErrorMessage(error.message), "error");
        }
    });
});