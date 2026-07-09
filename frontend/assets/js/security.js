(function () {
    "use strict";

    const BLOCK_MESSAGE = `
        <div style="
            min-height:100vh;
            display:flex;
            align-items:center;
            justify-content:center;
            background:#060911;
            color:#14b8a6;
            font-family:Tajawal, Arial, sans-serif;
            font-size:24px;
            text-align:center;
            padding:30px;
            line-height:2;
        ">
            تم إيقاف عرض المحتوى لأسباب أمنية<br>
            الرجاء إغلاق أدوات المطور وإعادة تحميل الصفحة
        </div>
    `;

    let blocked = false;

    function blockPage() {
        if (blocked) return;
        blocked = true;
        document.body.innerHTML = BLOCK_MESSAGE;
    }

    // منع كليك يمين
    document.addEventListener("contextmenu", function (e) {
        e.preventDefault();
        return false;
    });

    // منع نسخ / قص / سحب / تحديد
    ["copy", "cut", "paste", "selectstart", "dragstart"].forEach(eventName => {
        document.addEventListener(eventName, function (e) {
            e.preventDefault();
            return false;
        });
    });

    // منع اختصارات الفحص والحفظ والطباعة
    document.addEventListener("keydown", function (e) {
        const key = e.key.toLowerCase();

        const blockedKeys =
            e.key === "F12" ||
            (e.ctrlKey && e.shiftKey && ["i", "j", "c", "k"].includes(key)) ||
            (e.ctrlKey && ["u", "s", "p"].includes(key)) ||
            (e.metaKey && e.altKey && ["i", "j", "c"].includes(key));

        if (blockedKeys) {
            e.preventDefault();
            e.stopPropagation();
            return false;
        }
    });

    // محاولة تعطيل Print Screen
    document.addEventListener("keyup", function (e) {
        if (e.key === "PrintScreen") {
            try {
                navigator.clipboard.writeText("");
            } catch (_) {}

            alert("Screen capture is not allowed.");
        }
    });

    // كشف DevTools من فرق أبعاد النافذة
    setInterval(() => {
        const widthDiff = window.outerWidth - window.innerWidth;
        const heightDiff = window.outerHeight - window.innerHeight;

        if (widthDiff > 180 || heightDiff > 180) {
            blockPage();
        }
    }, 1000);

    // كشف DevTools بطريقة debugger
    setInterval(() => {
        const start = performance.now();
        debugger;
        const end = performance.now();

        if (end - start > 100) {
            blockPage();
        }
    }, 1500);

    // منع فتح الصفحة داخل iframe خارجي
    if (window.top !== window.self) {
        window.top.location = window.self.location;
    }

})();