requireLogin();

const profileTranslations = {
    ar: {
        langBtn: "English",
        navDashboard: "لوحة التحكم",
        titleProfile: "الملف الشخصي",
        accInfo: "معلومات الحساب",
        labelName: "الاسم:",
        labelEmail: "الإيميل:",
        labelPhone: "الهاتف:",
        labelRole: "الصلاحية:",
        changePassTitle: "تغيير كلمة المرور",
        curPassPH: "كلمة المرور الحالية",
        newPassPH: "كلمة المرور الجديدة",
        changePassBtn: "تغيير كلمة المرور",
        logoutBtn: "تسجيل الخروج",
        fillPass: "أدخل كلمة المرور الحالية والجديدة",
        passDone: "تم تغيير كلمة المرور بنجاح",
        serverFail: "فشل الاتصال بالسيرفر"
    },
    en: {
        langBtn: "عربي",
        navDashboard: "Dashboard",
        titleProfile: "Profile",
        accInfo: "Account Information",
        labelName: "Name:",
        labelEmail: "Email:",
        labelPhone: "Phone:",
        labelRole: "Role:",
        changePassTitle: "Change Password",
        curPassPH: "Current Password",
        newPassPH: "New Password",
        changePassBtn: "Change Password",
        logoutBtn: "Logout",
        fillPass: "Enter current and new password",
        passDone: "Password changed successfully",
        serverFail: "Server connection failed"
    }
};

function getProfileLang() {
    return document.documentElement.lang || "ar";
}

function applyProfileLanguage(lang) {
    const t = profileTranslations[lang];

    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";

    langBtn.innerText = t.langBtn;
    navDashboard.innerText = t.navDashboard;
    titleProfile.innerText = t.titleProfile;
    accInfo.innerText = t.accInfo;
    labelName.innerText = t.labelName;
    labelEmail.innerText = t.labelEmail;
    labelPhone.innerText = t.labelPhone;
    labelRole.innerText = t.labelRole;
    changePassTitle.innerText = t.changePassTitle;
    currentPassword.placeholder = t.curPassPH;
    newPassword.placeholder = t.newPassPH;
    changePassBtn.innerText = t.changePassBtn;
    logoutBtn.innerText = t.logoutBtn;

    localStorage.setItem("userLang", lang);
}

async function loadProfile() {
    try {
        const data = await API.getProfile();

        if (!data.success || !data.data) {
            logout();
            return;
        }

        const u = data.data;

        fullName.innerText = `${u.firstName || u.first_name || ""} ${u.lastName || u.last_name || ""}`.trim() || "-";
        email.innerText = u.email || "-";
        phoneNumber.innerText = u.phoneNumber || u.phone_number || "-";
        role.innerText = u.role || "-";

    } catch (e) {
        console.error(e);
        logout();
    }
}

async function changePassword() {
    const lang = getProfileLang();
    const t = profileTranslations[lang];

    const cur = currentPassword.value.trim();
    const next = newPassword.value.trim();

    passwordMessage.className = "text-sm text-red-400";

    if (!cur || !next) {
        passwordMessage.innerText = t.fillPass;
        return;
    }

    try {
        await API.changePassword(cur, next);

        passwordMessage.className = "text-sm text-green-400";
        passwordMessage.innerText = t.passDone;

        currentPassword.value = "";
        newPassword.value = "";

    } catch (e) {
        console.error(e);
        passwordMessage.className = "text-sm text-red-400";
        passwordMessage.innerText = mapErrorMessage(e.message);
    }
}

function logoutDevice() {
    logout();
}

langBtn.onclick = () => {
    const newLang = getProfileLang() === "ar" ? "en" : "ar";
    applyProfileLanguage(newLang);
};

window.addEventListener("load", async () => {
    applyProfileLanguage(localStorage.getItem("userLang") || "ar");
    await loadProfile();
});