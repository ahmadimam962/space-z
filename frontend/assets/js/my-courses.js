requireLogin();

const translations = {
    ar: {
        langBtn: "English",
        navSub: "My Courses",
        dashboard: "لوحة التحكم",
        title: "كورساتي",
        empty: "لا تملك أي كورسات حالياً",
        desc: "لا يوجد وصف",
        btn: "دخول الكورس",
        completed: "مكتمل"
    },
    en: {
        langBtn: "عربي",
        navSub: "My Courses",
        dashboard: "Dashboard",
        title: "My Courses",
        empty: "You don't have any courses yet",
        desc: "No description",
        btn: "Enter Course",
        completed: "completed"
    }
};

let myCourses = [];

function applyLanguage(lang) {

    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";

    const t = translations[lang];

    langBtn.innerText = t.langBtn;
    navSub.innerText = t.navSub;
    dashboardLink.innerText = t.dashboard;
    pageTitle.innerText = t.title;
    emptyMessage.innerText = t.empty;

    localStorage.setItem("userLang", lang);

    renderCourses();


}

async function loadMyCourses() {

    try {

        const res = await API.getMyCourses();

        if (!res.success) {
            return;
        }

        myCourses = res.data || [];

        console.log("MY COURSES RESPONSE:", myCourses);

        renderCourses();

    } catch (e) {

        console.error(e);

    }

}

function renderCourses() {

    const lang = document.documentElement.lang || "ar";
    const t = translations[lang];

    coursesGrid.innerHTML = "";

    if (myCourses.length === 0) {

        emptyMessage.classList.remove("hidden");
        return;

    }

    emptyMessage.classList.add("hidden");

    myCourses.forEach(item => {

        const course = item.course;

        const progress = Number(
    item.progress_percentage ??
    item.progressPercentage ??
    item.completionPercentage ??
    item.completion_percentage ??
    item.progress ??
    course.progress_percentage ??
    course.progressPercentage ??
    course.completionPercentage ??
    course.completion_percentage ??
    course.progress ??
    0
);



        const card = document.createElement("div");

        card.className = "glass rounded-3xl overflow-hidden hover:border-teal-500 transition";

        card.innerHTML = `
<div class="h-44 bg-slate-950 flex items-center justify-center">

${course.thumbnailUrl
? `<img src="${course.thumbnailUrl}" class="w-full h-full object-cover">`
: `<span class="text-teal-400 text-4xl font-bold">SPACE Z</span>`}

</div>

<div class="p-5">

<h2 class="text-xl font-bold mb-2">
${course.title}
</h2>

<p class="text-zinc-400 text-sm mb-4 min-h-[45px]">
${course.description || t.desc}
</p>

<div class="w-full bg-slate-700 rounded-full h-2.5 mb-2">
<div class="bg-teal-500 h-2.5 rounded-full transition-all duration-500"
style="width:${progress}%">
</div>
</div>

<div class="text-xs text-zinc-400 mb-4">
${progress}% ${t.completed}
</div>

<button
onclick="openCourse(${course.id})"
class="w-full bg-teal-500 hover:bg-teal-600 text-slate-950 font-bold py-3 rounded-xl">

${t.btn}

</button>

</div>
`;

        coursesGrid.appendChild(card);

    });

}

function openCourse(courseId) {
    window.location.href = `course-view.html?id=${courseId}`;
}


langBtn.onclick = () => {

    applyLanguage(
        document.documentElement.lang === "ar" ? "en" : "ar"
    );

};

window.addEventListener("load", async () => {

    applyLanguage(
        localStorage.getItem("userLang") || "ar"
    );

    await loadMyCourses();

});