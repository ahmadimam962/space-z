let notificationsData = [];

function toggleNotifications() {
    const drawer = document.getElementById("notifDrawer");
    drawer.classList.toggle("right-0");
    drawer.classList.toggle("right-[-400px]");
}

function showTab(tab) {
    const notifList = document.getElementById("notificationsList");
    const purchList = document.getElementById("purchaseHistoryList");
    const tabNotif = document.getElementById("tabNotif");
    const tabPurch = document.getElementById("tabPurch");

    if (tab === "notifications") {
        notifList.classList.remove("hidden");
        purchList.classList.add("hidden");
        tabNotif.className = "pb-2 text-teal-400 border-b-2 border-teal-400 font-bold text-sm";
        tabPurch.className = "pb-2 text-zinc-500 hover:text-white font-bold text-sm";
    } else {
        notifList.classList.add("hidden");
        purchList.classList.remove("hidden");
        tabPurch.className = "pb-2 text-teal-400 border-b-2 border-teal-400 font-bold text-sm";
        tabNotif.className = "pb-2 text-zinc-500 hover:text-white font-bold text-sm";
    }
}

function translateNotification(text) {
    if (!text) return "";

    if (text.includes("تمت إضافة كورس")) {
        return "A course has been added to your account";
    }

    if (text.includes("قام الأدمن بإضافة كورس")) {
        const courseNumber = text.match(/\d+/);
        return `The admin added Course ${courseNumber ? courseNumber[0] : ""} to your account.`;
    }

    return text;
}

async function loadNotifications() {
    try {
        const data = await API.getNotifications();

        if (!data.success) return;

        notificationsData = data.data || [];

        const badge = document.getElementById("unreadBadge");

        if (badge) {
            if (data.unreadCount > 0) {
                badge.classList.remove("hidden");
            } else {
                badge.classList.add("hidden");
            }
        }

        renderNotifications();

    } catch (err) {
        console.error("Error loading notifications:", err);
    }
}

function renderNotifications() {
    const list = document.getElementById("notificationsList");
    if (!list) return;

    const lang = document.documentElement.lang || "ar";

    if (notificationsData.length === 0) {
        list.innerHTML = `
            <div class="text-center py-8">
                <p class="text-zinc-500 text-sm">
                    ${lang === "ar" ? "لا توجد إشعارات جديدة" : "No new notifications"}
                </p>
            </div>
        `;
        return;
    }

    list.innerHTML = "";

    notificationsData.slice(0, 5).forEach(n => {
        const date = new Date(n.createdAt).toLocaleDateString(lang === "ar" ? "ar-SA" : "en-US");
        const title = lang === "ar" ? n.title : translateNotification(n.title);
        const message = lang === "ar" ? n.message : translateNotification(n.message);

        list.innerHTML += `
            <div onclick="markNotificationRead(${n.id})" 
                 class="group relative bg-slate-800/30 border border-slate-700/50 rounded-2xl p-5 hover:border-teal-500/60 hover:bg-slate-800/60 transition-all duration-300 cursor-pointer shadow-xl hover:shadow-teal-900/10">
                
                <div class="flex justify-between items-start gap-4">
                    <h3 class="font-bold text-teal-100 group-hover:text-teal-400 transition">${title}</h3>
                    ${!n.isRead ? `<span class="flex-shrink-0 w-2.5 h-2.5 bg-teal-400 rounded-full animate-pulse shadow-[0_0_10px_rgba(45,212,191,0.8)]"></span>` : ""}
                </div>

                <p class="text-zinc-400 text-sm mt-2 leading-relaxed">${message}</p>

            </div>
        `;
    });
}

async function markNotificationRead(id) {
    try {
        await API.readNotification(id);
        await loadNotifications();
    } catch (err) {
        console.error("Error marking notification read:", err);
    }
}

async function markAllNotificationsRead() {
    try {
        await API.readAllNotifications();
        await loadNotifications();
    } catch (err) {
        console.error("Error marking all notifications read:", err);
    }
}