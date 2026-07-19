requireLogin();

const translations = {
    ar: {
        dashboard: "لوحة التحكم",
        title: "شهاداتي وإنجازاتي 🎓",
        subtitle: "هنا تجد جميع الشهادات التي حصلت عليها بعد إتمام كورساتك بنجاح.",
        empty: "لا توجد شهادات حالياً. استمر في الدراسة للحصول على شهادتك الأولى!",
        download: "تحميل الشهادة",
        lang: "EN / AR"
    },
    en: {
        dashboard: "Dashboard",
        title: "My Certificates & Achievements 🎓",
        subtitle: "Here you can find all your certificates.",
        empty: "No certificates yet.",
        download: "Download Certificate",
        lang: "AR / EN"
    }
};

function applyLanguage(lang){

    document.documentElement.lang = lang;
    document.documentElement.dir = lang==="ar"?"rtl":"ltr";

    const t = translations[lang];

    langToggle.innerText = t.lang;

    document.querySelector("h1").innerText = t.title;
    document.querySelector("main p").innerText = t.subtitle;

    emptyMsg.innerText = t.empty;

    document.querySelector("nav a").innerText = t.dashboard;

    localStorage.setItem("userLang",lang);

    renderCertificates();

}

let certificates=[];

async function loadCertificates(){

    try{

        const res = await API.getCertificates();

        certificates = res.data || [];

        renderCertificates();

    }catch(e){

        console.error(e);

    }

    const res = await API.getCertificates();
    

console.log(res.data);

certificates = res.data || [];

console.log(certificates);

}

function renderCertificates(){

    certificatesGrid.innerHTML="";

    const t = translations[document.documentElement.lang];

    if(certificates.length===0){

        emptyMsg.classList.remove("hidden");
        return;

    }

    emptyMsg.classList.add("hidden");

    certificates.forEach(cert=>{

        certificatesGrid.innerHTML+=`

<div class="glass-card p-6 rounded-3xl border border-slate-800">

<div class="text-teal-400 text-5xl mb-5">
📄
</div>

<h3 class="font-bold text-xl mb-2">

${cert.course?.title || "-"}
</h3>

<p class="text-zinc-400 text-sm mb-6">

${new Date(cert.issuedAt).toLocaleDateString()}

</p>

<button
onclick="downloadCertificate('${cert.certificateCode}')"
class="block w-full text-center bg-teal-500 hover:bg-teal-600 text-slate-950 font-bold py-3 rounded-xl">
${t.download}
</button>

</div>

`;

    });

}

langToggle.onclick=()=>{

    applyLanguage(

        document.documentElement.lang==="ar"

        ?"en"

        :"ar"

    );

};



window.addEventListener("load",()=>{

    applyLanguage(

        localStorage.getItem("userLang")||"ar"

    );

    loadCertificates();

});

async function downloadCertificate(code) {
    const response = await fetch(`${API_BASE}/api/certificates/${code}/download`, {
        headers: {
            Authorization: `Bearer ${getToken()}`
        }
    });

    if (!response.ok) {
        alert(await response.text());
        return;
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = `${code}.pdf`;
    a.click();

    URL.revokeObjectURL(url);
}