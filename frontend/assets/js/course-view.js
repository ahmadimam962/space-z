requireLogin();

const params = new URLSearchParams(location.search);
const courseId = params.get("id");

if (!courseId) {
    location.href = "my-courses.html";
}

const dict = {
    ar: {
        selectLesson: "اختر درس للبدء",
        noLessons: "لا يوجد دروس",
        loading: "جاري تحميل الدرس...",
        noVideo: "لا يوجد رابط فيديو لهذا الدرس",
        noAccess: "لا يمكنك مشاهدة هذا الدرس",
        noText: "لا يوجد نص",
        empty: "اختر درس من القائمة",
        noContent: "لا يوجد محتوى داخل هذا الكورس حالياً"
    },
    en: {
        selectLesson: "Select lesson",
        noLessons: "No lessons",
        loading: "Loading...",
        noVideo: "No video",
        noAccess: "Access denied",
        noText: "No content",
        empty: "Select lesson",
        noContent: "No course content"
    }
};

function emptyBox(text){

    return `
<div class="h-64 border border-slate-800 rounded-2xl flex items-center justify-center text-zinc-500">
${text}
</div>`;

}

async function loadCourse(){

    try{

        const data=await API.getCourseContent(courseId);

        courseTitle.innerText=data.course.title;
        courseDescription.innerText=data.course.description||"";

        renderSections(data.sections||[]);

    }catch(e){

        alert(mapErrorMessage(e.message));

        location.href="my-courses.html";

    }

}

function renderSections(sections){

    const lang=document.documentElement.lang||"ar";

    const t=dict[lang];

    sectionsList.innerHTML="";

    if(sections.length===0){

        sectionsList.innerHTML=`
<p class="text-zinc-500 text-sm">
${t.noContent}
</p>`;

        return;

    }

    sections.forEach(section=>{

        const wrapper=document.createElement("div");

        wrapper.innerHTML=`
<div class="border border-slate-800 rounded-2xl p-4">

<h3 class="font-bold text-teal-400 mb-3">

${section.title}

</h3>

<div class="space-y-2">

${
section.lessons.length
?
section.lessons.map(lesson=>`

<div class="flex items-center gap-3">

<input
type="checkbox"
class="w-5 h-5 accent-teal-500"

${localStorage.getItem("lesson_"+lesson.id)?"checked":""}

onchange="toggleLesson(this,${lesson.id})">

<button
onclick='openLesson(${JSON.stringify(lesson)})'

class="flex-1 text-right bg-slate-950/70 hover:bg-teal-500/10 border border-slate-800 hover:border-teal-500 rounded-xl px-4 py-3 transition">

<div class="font-bold">
${lesson.title}
</div>

<div class="text-xs text-zinc-500">
${lesson.lessonType}
</div>

</button>

</div>

`).join("")
:
`<p class="text-zinc-500">${t.noLessons}</p>`
}

</div>

</div>`;

        sectionsList.appendChild(wrapper);

    });

}

async function openLesson(lesson){

    const lang=document.documentElement.lang||"ar";

    const t=dict[lang];

    lessonTitle.innerText=lesson.title;
    lessonDescription.innerText=lesson.description||"";

    lessonContent.innerHTML=emptyBox(t.loading);

    try{

        const data=await API.watchLesson(lesson.id);

        const l=data.lesson;

if (l.lessonType === "video") {

    if (!l.videoUrl) {
        lessonContent.innerHTML = emptyBox(t.noVideo);
        return;
    }

lessonContent.innerHTML = `
<div class="aspect-video bg-black rounded-2xl overflow-hidden border border-slate-800">
    <div id="youtubePlayer"></div>
</div>
`;

createYoutubePlayer("FUKmyRLOlAA", lesson.id); // حط ID الفيديو اللي بدك إياه

    return;
}


        if(l.lessonType==="pdf"){

            lessonContent.innerHTML=`
<iframe
src="${l.pdfUrl}"
class="w-full h-[650px] rounded-2xl border border-slate-800">
</iframe>`;

            return;

        }

        lessonContent.innerHTML=`
<div class="bg-slate-950/70 border border-slate-800 rounded-2xl p-5 leading-8 whitespace-pre-line">

${l.contentText||t.noText}

</div>`;

    }catch(e){

        lessonContent.innerHTML=emptyBox(mapErrorMessage(e.message));

    }

}

async function toggleLesson(box, id) {
    console.log("toggleLesson fired:", id, box.checked);

    if (box.checked) {
        localStorage.setItem("lesson_" + id, "true");
    } else {
        localStorage.removeItem("lesson_" + id);
    }

    try {
        const res = await API.updateLessonProgress(id, box.checked);
        console.log("Progress saved:", res);
    } catch (e) {
        console.error("Progress save failed:", e);
        alert("فشل حفظ التقدم: " + e.message);
    }
}

function applyLanguage(lang){

    document.documentElement.lang=lang;
    document.documentElement.dir=lang==="ar"?"rtl":"ltr";

    localStorage.setItem("userLang",lang);

    document.querySelectorAll("[data-en]").forEach(el=>{

        el.innerText=el.dataset[lang];

    });

}

langToggle.onclick=()=>{

    applyLanguage(
        document.documentElement.lang==="ar"?"en":"ar"
    );

};

window.addEventListener("load",()=>{

    applyLanguage(localStorage.getItem("userLang")||"ar");

    loadCourse();

});

function setupBunnyProgressTracking(lessonId) {
    const iframe = document.getElementById("bunnyPlayer");

    if (!iframe || typeof playerjs === "undefined") {
        console.warn("Bunny Player.js not loaded");
        return;
    }

    const player = new playerjs.Player(iframe);

    let duration = 0;
    let completed = false;

    player.on("ready", () => {
        player.getDuration(value => {
            duration = Number(value) || 0;
        });
    });

    player.on("timeupdate", data => {
        if (completed || !duration) return;

        const currentTime = Number(data.seconds || 0);
        const percent = (currentTime / duration) * 100;

        if (percent >= 90) {
            completed = true;
            markLessonCompleted(lessonId);
        }
    });
}

async function markLessonCompleted(lessonId) {
    localStorage.setItem("lesson_" + lessonId, true);

    const checkbox = [...document.querySelectorAll("input[type='checkbox']")]
        .find(input => input.getAttribute("onchange")?.includes(String(lessonId)));

    if (checkbox) {
        checkbox.checked = true;
    }

    try {
        await API.updateLessonProgress(lessonId, true);
        console.log("Lesson completed after 90% watch");
    } catch (e) {
        console.error("Failed to update lesson progress:", e);
    }
}

let ytPlayer;
let ytInterval;
let lessonCompleted = false;

function createYoutubePlayer(videoId, lessonId) {

    ytPlayer = new YT.Player("youtubePlayer", {
        videoId: videoId,
        events: {
            onReady: () => {

                ytInterval = setInterval(async () => {

                    if (lessonCompleted) return;

                    const duration = ytPlayer.getDuration();

                    if (!duration) return;

                    const current = ytPlayer.getCurrentTime();

                    const percent = (current / duration) * 100;

                    console.log(percent.toFixed(1) + "%");

                    if (percent >= 90) {

                        lessonCompleted = true;

                        clearInterval(ytInterval);

                        await markLessonCompleted(lessonId);

                    }

                }, 1000);

            }
        }
    });

}




// منع السحب والتحديد
document.addEventListener("selectstart", e => e.preventDefault());
document.addEventListener("dragstart", e => e.preventDefault());

// إخفاء المحتوى إذا المستخدم خرج من التبويب
document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
        lessonContent.style.filter = "blur(20px)";
        lessonContent.style.opacity = "0.2";
    } else {
        lessonContent.style.filter = "none";
        lessonContent.style.opacity = "1";
    }
});

// منع Picture-in-Picture للفيديو العادي
document.addEventListener("enterpictureinpicture", e => {
    e.preventDefault();
});

protectContentBlur();

document.addEventListener("keyup", function (e) {
    if (e.key === "PrintScreen") {
        navigator.clipboard.writeText("");
        document.body.style.filter = "blur(30px)";

        setTimeout(() => {
            document.body.style.filter = "none";
        }, 1500);

        alert("Screen capture is not allowed.");
    }
});

document.addEventListener("contextmenu", e => e.preventDefault());
document.addEventListener("copy", e => e.preventDefault());
document.addEventListener("cut", e => e.preventDefault());
document.addEventListener("selectstart", e => e.preventDefault());
document.addEventListener("dragstart", e => e.preventDefault());




// منع القائمة اليمنى

// منع اختصارات أدوات المطور
document.addEventListener("keydown", function (e) {

    const key = e.key.toLowerCase();

    if (
        e.key === "F12" ||
        (e.ctrlKey && e.shiftKey && (key === "i" || key === "j" || key === "c")) ||
        (e.ctrlKey && key === "u")
    ) {
        e.preventDefault();
        e.stopPropagation();
        return false;
    }
});

setInterval(() => {

    if (
        window.outerWidth - window.innerWidth > 180 ||
        window.outerHeight - window.innerHeight > 180
    ) {

        document.body.innerHTML = `
            <div style="
                height:100vh;
                display:flex;
                justify-content:center;
                align-items:center;
                background:#060911;
                color:white;
                font-size:28px;
                font-family:Tajawal;
            ">
                تم إيقاف تشغيل الصفحة لأسباب أمنية
            </div>
        `;

    }

}, 1000);

