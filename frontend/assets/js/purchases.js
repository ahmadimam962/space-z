let purchasesData = [];

async function loadPurchaseHistory() {
    try {
        const data = await API.getPurchases();

        if (data.success) {
            purchasesData = data.data || [];
            renderPurchases();
        }

    } catch (err) {
        console.error("Error loading purchase history:", err);
    }
}

function renderPurchases() {
    const list = document.getElementById("purchaseHistoryList");
    if (!list) return;

    const lang = document.documentElement.lang || "ar";

    if (purchasesData.length === 0) {
        list.innerHTML = `
            <div class="text-center py-8">
                <p class="text-zinc-500 text-sm">
                    ${lang === "ar" ? "لا توجد طلبات شراء حالياً" : "No purchase history available"}
                </p>
            </div>
        `;
        return;
    }

    list.innerHTML = purchasesData.slice(0, 5).map(p => {
        const date = new Date(p.createdAt).toLocaleDateString(lang === "ar" ? "ar-SA" : "en-US");

        const statusText = lang === "ar"
            ? (p.status === "approved" ? "مقبول" : "قيد الانتظار")
            : p.status;

        return `
            <div class="border border-slate-800 rounded-xl p-4 hover:border-teal-500 transition">
                <div class="flex justify-between gap-3 items-start">
                    <div>
                        <h3 class="font-bold">${p.course?.title || ""}</h3>
                        <p class="text-xs text-zinc-500 mt-1">${date}</p>
                    </div>
                    <span class="text-sm font-bold ${p.status === "approved" ? "text-teal-400" : "text-yellow-400"}">
                        ${statusText}
                    </span>
                </div>
            </div>
        `;
    }).join("");
}