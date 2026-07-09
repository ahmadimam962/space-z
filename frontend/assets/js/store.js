requireLogin();

let coursesList = [];
let selectedCourse = null;
let paymentMethods = [];
let selectedPaymentMethod = null;

const translations = {
    ar: {
        navTitle: "Store",
        navDashboard: "لوحة التحكم",
        navMyCourses: "كورساتي",
        navStore: "السوق",
        pageTitle: "متجر الكورسات",
        empty: "لا يوجد كورسات متاحة حالياً",
        modalTitle: "شراء الكورس",
        placeholder: "رقم التحويلة",
        submit: "إرسال الطلب",
        noDesc: "لا يوجد وصف",
        free: "مجاني",
        buy: "شراء",
        freeEnroll: "تسجيل مجاني"
    },
    en: {
        navTitle: "Store",
        navDashboard: "Dashboard",
        navMyCourses: "My Courses",
        navStore: "Store",
        pageTitle: "Course Store",
        empty: "No courses available currently",
        modalTitle: "Purchase Course",
        placeholder: "Transfer Number",
        submit: "Submit Request",
        noDesc: "No description",
        free: "Free",
        buy: "Buy",
        freeEnroll: "Free Enroll"
    }
};

function applyLanguage(lang){

    document.documentElement.lang = lang;
    document.documentElement.dir = lang==="ar"?"rtl":"ltr";

    const t = translations[lang];

    navTitle.innerText=t.navTitle;
    navDashboard.innerText=t.navDashboard;
    navMyCourses.innerText=t.navMyCourses;
    navStore.innerText=t.navStore;
    pageTitle.innerText=t.pageTitle;
    emptyMessage.innerText=t.empty;
    modalTitle.innerText=t.modalTitle;
    transferNumber.placeholder=t.placeholder;
    submitBtn.innerText=t.submit;

    localStorage.setItem("userLang",lang);

    renderCourses();
}

async function loadCourses(){

    try{

        const res = await API.getStoreCourses();

        if(!res.success){
            return;
        }

        coursesList=(res.data||[]).sort((a,b)=>a.isFeatured===b.isFeatured?0:a.isFeatured?-1:1);

        renderCourses();

    }catch(e){
        console.error(e);
    }

}

function renderCourses(){

    const lang=document.documentElement.lang||"ar";
    const t=translations[lang];

    coursesGrid.innerHTML="";

    if(coursesList.length===0){
        emptyMessage.classList.remove("hidden");
        return;
    }

    emptyMessage.classList.add("hidden");

    coursesList.forEach(course=>{

        const card=document.createElement("div");

        card.className="glass rounded-3xl overflow-hidden hover:border-teal-500 transition";

        card.innerHTML=`
<div class="h-44 bg-slate-950 flex items-center justify-center">

${course.thumbnailUrl?
`<img src="${course.thumbnailUrl}" class="w-full h-full object-cover">`
:
`<span class="text-teal-400 text-4xl font-bold">SPACE Z</span>`}

</div>

<div class="p-5">

<h2 class="text-xl font-bold mb-2">${course.title}</h2>

<p class="text-zinc-400 text-sm mb-4 min-h-[45px]">

${course.description||t.noDesc}

</p>

<div class="flex justify-between items-center">

<span class="text-teal-400 font-bold">

${course.isPaid?course.price+" JOD":t.free}

</span>

<button
onclick="${course.isPaid?`buyCourse(${course.id})`:`enrollFreeCourse(${course.id})`}"
class="bg-teal-500 hover:bg-teal-600 text-slate-950 font-bold px-4 py-2 rounded-xl">

${course.isPaid?t.buy:t.freeEnroll}

</button>

</div>

</div>`;

        coursesGrid.appendChild(card);

    });

}

async function enrollFreeCourse(courseId){

    try{

        await API.freeEnroll(courseId);

        alert("تم التسجيل بنجاح");

        location.href="my-courses.html";

    }catch(e){

        alert(mapErrorMessage(e.message));

    }

}

async function buyCourse(courseId){

    selectedCourse=courseId;

    purchaseModal.classList.remove("hidden");
    purchaseModal.classList.add("flex");

    await loadPaymentMethods();

}

function closePurchaseModal(){

    purchaseModal.classList.add("hidden");
    purchaseModal.classList.remove("flex");

}

async function loadPaymentMethods(){

    selectedPaymentMethod = null;
    paymentMethods = [];
    paymentMethodsContainer.innerHTML = "";
    purchaseMessage.innerText = "";

    try {
        const res = await API.getPaymentMethods();

        console.log("PAYMENT METHODS RESPONSE:", res);

        paymentMethods = res.data || res.paymentMethods || res.methods || [];

        if (!paymentMethods.length) {
            paymentMethodsContainer.innerHTML = `
                <div class="border border-red-500/40 bg-red-500/10 rounded-xl p-3 text-sm text-red-400">
                    لا توجد طرق دفع مضافة حالياً
                </div>
            `;
            return;
        }

        paymentMethods.forEach(method => {
            paymentMethodsContainer.innerHTML += `
                <label class="flex gap-3 items-center border border-slate-700 rounded-xl p-3 mb-3 cursor-pointer hover:border-teal-500 transition">
                    <input
                        type="radio"
                        name="payment"
                        value="${method.id}"
                        onchange="selectedPaymentMethod=${method.id}"
                    >

                    <div>
                        <div class="font-bold">
                            ${method.name || method.title || method.methodName || "Payment Method"}
                        </div>

                        <div class="text-sm text-zinc-400">
                            ${method.number || method.accountNumber || method.phoneNumber || method.details || ""}
                        </div>
                    </div>
                </label>
            `;
        });

    } catch(e) {
        console.error("Payment methods error:", e);

        paymentMethodsContainer.innerHTML = `
            <div class="border border-red-500/40 bg-red-500/10 rounded-xl p-3 text-sm text-red-400">
                فشل تحميل طرق الدفع
            </div>
        `;
    }
}

async function submitPurchase(){

    if(!selectedPaymentMethod){

        purchaseMessage.innerText="اختر وسيلة الدفع";

        return;

    }

    try{

        await API.submitPurchase(
    selectedCourse,
    transferNumber.value
);

        purchaseMessage.className="text-sm text-teal-400 mt-3";
        purchaseMessage.innerText="تم إرسال الطلب";

        setTimeout(()=>{

            closePurchaseModal();

        },1200);

    }catch(e){

        purchaseMessage.className="text-sm text-red-400 mt-3";
        purchaseMessage.innerText=mapErrorMessage(e.message);

    }

}

langToggle.onclick=()=>{

    applyLanguage(
        document.documentElement.lang==="ar"?"en":"ar"
    );

};

window.addEventListener("load",async()=>{

    applyLanguage(localStorage.getItem("userLang")||"ar");

    await loadCourses();

});