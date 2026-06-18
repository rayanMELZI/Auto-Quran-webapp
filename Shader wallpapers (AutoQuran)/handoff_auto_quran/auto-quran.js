/* Auto Quran — dashboard logic.
 * Functional prototype shell: 5-step pipeline, real run-log console,
 * automation + scheduling, Instagram, i18n. No backend — actions simulate work.
 */
(function () {
  "use strict";
  var qs = function (s, r) { return (r || document).querySelector(s); };
  var qsa = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  // NODES = all overview nodes; PROC = the four runnable processing steps; "share" completes via Instagram.
  var NODES = ["image", "video", "overlay", "final", "share"];
  var PROC = ["image", "video", "overlay", "final"];
  var state = { image: "pending", video: "pending", overlay: "pending", final: "pending", share: "pending" };
  var DUR = { image: 900, video: 1200, overlay: 950, final: 1400 };
  var running = false, aborted = false;

  /* ---------------- i18n (UI chrome only; logs stay English) ---------------- */
  var I18N = {
    brandSub:     { en: "Automated Quran video pipeline", ar: "خط إنتاج فيديوهات القرآن الآلي" },
    runFull:      { en: "Run Full Pipeline", ar: "تشغيل المسار الكامل" },
    shareTop:     { en: "Share to Instagram", ar: "مشاركة على إنستغرام" },
    pipeline:     { en: "Pipeline", ar: "مسار الإنتاج" },
    clearAll:     { en: "Clear all", ar: "مسح الكل" },
    ofReady:      { en: "of 5 steps ready", ar: "من 5 خطوات جاهزة" },
    nImage:       { en: "Background", ar: "الخلفية" },
    nVideo:       { en: "Video", ar: "الفيديو" },
    nOverlay:     { en: "Overlay", ar: "النص" },
    nFinal:       { en: "Final", ar: "النهائي" },
    nShare:       { en: "Share", ar: "مشاركة" },
    s1Title:      { en: "Background Image", ar: "صورة الخلفية" },
    s1Sub:        { en: "Upload your own, or fetch a nature image", ar: "ارفع صورتك أو اجلب صورة طبيعة" },
    s1Drop:       { en: "Click to upload a custom image", ar: "انقر لرفع صورة مخصّصة" },
    s1DropHint:   { en: "or fetch one from Unsplash below", ar: "أو اجلب واحدة من Unsplash بالأسفل" },
    s1Fetch:      { en: "Fetch from Unsplash", ar: "جلب من Unsplash" },
    s2Title:      { en: "Quran Video", ar: "فيديو القرآن" },
    s2Sub:        { en: "Source clip by URL or from a channel", ar: "مصدر المقطع برابط أو من قناة" },
    s2VideoUrl:   { en: "Video URL (optional)", ar: "رابط الفيديو (اختياري)" },
    s2ChannelUrl: { en: "Channel URL (optional)", ar: "رابط القناة (اختياري)" },
    s2Keyword:    { en: "Keyword (used with channel)", ar: "كلمة مفتاحية (تُستخدم مع القناة)" },
    s2Download:   { en: "Download Video", ar: "تنزيل الفيديو" },
    s3Title:      { en: "Text Overlay", ar: "النص التراكبي" },
    s3Sub:        { en: "Extract the verse text to lay over the clip", ar: "استخراج نص الآية لعرضه فوق المقطع" },
    s3Extract:    { en: "Extract Text", ar: "استخراج النص" },
    s4Title:      { en: "Final Video", ar: "الفيديو النهائي" },
    s4Sub:        { en: "Compose image, clip & text into the reel", ar: "تركيب الصورة والمقطع والنص في الريل" },
    s4Create:     { en: "Create Final Video", ar: "إنشاء الفيديو النهائي" },
    automation:   { en: "Automation", ar: "الأتمتة" },
    autopost:     { en: "Auto-post to Instagram", ar: "النشر تلقائيًا على إنستغرام" },
    autopostSub:  { en: "after the full pipeline finishes", ar: "بعد انتهاء المسار الكامل" },
    schedSection: { en: "Scheduling", ar: "الجدولة" },
    schedEnable:  { en: "Enable schedule", ar: "تفعيل الجدولة" },
    schedSub:     { en: "run the pipeline at set intervals", ar: "تشغيل المسار على فترات محدّدة" },
    schedEvery:   { en: "Every (hours)", ar: "كل (ساعات)" },
    schedStart:   { en: "Start time", ar: "وقت البدء" },
    schedSave:    { en: "Save Schedule", ar: "حفظ الجدولة" },
    schedEveryHint:{ en: "24 = once daily", ar: "24 = مرة يوميًا" },
    status:       { en: "Status", ar: "الحالة" },
    nextRun:      { en: "Next run", ar: "التشغيل القادم" },
    igTitle:      { en: "Post to Instagram", ar: "النشر على إنستغرام" },
    igCaption:    { en: "Caption", ar: "التعليق" },
    regenCaption: { en: "Regenerate", ar: "إعادة توليد" },
    igShare:      { en: "Share on Instagram", ar: "مشاركة على إنستغرام" },
    advanced:     { en: "Advanced tools", ar: "أدوات متقدمة" },
    viewLog:      { en: "View run log", ar: "عرض سجل التشغيل" },
    resetVideos:  { en: "Reset downloaded videos list", ar: "إعادة تعيين قائمة الفيديوهات" },
    stopAll:      { en: "Stop all running processes", ar: "إيقاف كل العمليات الجارية" },
    runLog:       { en: "Run Log", ar: "سجل التشغيل" },
    logClear:     { en: "Clear", ar: "مسح" },
    saveDefault:  { en: "Save as default", ar: "حفظ كافتراضي" },
    reset:        { en: "Reset", ar: "إعادة تعيين" },
    download:     { en: "Download", ar: "تنزيل" },
    remove:       { en: "Remove", ar: "إزالة" },
    ready:        { en: "Ready", ar: "جاهز" },
    stPending:    { en: "Pending", ar: "قيد الانتظار" },
    stRunning:    { en: "Running", ar: "جارٍ التشغيل" },
    stDone:       { en: "Ready", ar: "جاهز" },
    footnote:     { en: "Functional interface shell — ready to connect to the pipeline backend.", ar: "واجهة وظيفية جاهزة للربط بخادم المعالجة." }
  };
  var lang = "en";
  try { lang = localStorage.getItem("aq_lang") || "en"; } catch (e) {}
  function t(key) { var o = I18N[key]; return o ? (o[lang] || o.en) : key; }
  function msg(en, ar) { return lang === "en" ? en : ar; }

  function applyLang() {
    qsa("[data-i18n]").forEach(function (el) {
      var k = el.getAttribute("data-i18n");
      if (I18N[k]) el.textContent = t(k);
    });
    qs("#langBtn").textContent = lang === "en" ? "العربية" : "English";
    document.documentElement.lang = lang;
    PROC.forEach(function (key) {
      var card = qs("#step-" + key);
      if (!card) return;
      var st = state[key];
      qs(".ps-label", card).textContent = st === "running" ? t("stRunning") : st === "done" ? t("stDone") : t("stPending");
    });
    if (schedSaved) renderSchedStatus();
  }

  /* ---------------- run log ---------------- */
  var logN = 0;
  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function log(message, level) {
    level = level || "info";
    var c = qs("#logConsole"), now = new Date();
    var ts = pad(now.getHours()) + ":" + pad(now.getMinutes()) + ":" + pad(now.getSeconds());
    var line = document.createElement("div");
    line.className = "logline " + level;
    var lt = document.createElement("span"); lt.className = "lt"; lt.textContent = ts;
    var lv = document.createElement("span"); lv.className = "lv"; lv.textContent = level.toUpperCase();
    var lm = document.createElement("span"); lm.className = "lm"; lm.textContent = message;
    line.appendChild(lt); line.appendChild(lv); line.appendChild(lm);
    c.appendChild(line); c.scrollTop = c.scrollHeight;
    logN++; qs("#logCount").textContent = logN + " lines";
  }
  var LOGMSG = {
    image:   { start: "Fetching background image…", done: "Background image ready (1080×1920)" },
    video:   { start: "Downloading Quran video…", done: "Video downloaded — 00:58, 1080p" },
    overlay: { start: "Extracting verse text overlay…", done: "Text overlay extracted (3 segments)" },
    final:   { start: "Composing final video…", done: "Final video rendered → final.mp4" }
  };

  /* ---------------- status ---------------- */
  function setStatus(key, st) {
    state[key] = st;
    var card = qs("#step-" + key);
    if (card) {
      var pill = qs(".pill", card);
      pill.setAttribute("data-status", st);
      qs(".ps-label", pill).textContent = st === "running" ? t("stRunning") : st === "done" ? t("stDone") : t("stPending");
      card.classList.toggle("done", st === "done");
    }
    var node = qs('.node[data-node="' + key + '"]');
    if (node) {
      node.classList.remove("running", "done");
      if (st === "running") node.classList.add("running");
      if (st === "done") { node.classList.add("done"); markNodeCheck(node); }
      else restoreNodeIcon(node, key);
    }
    updateOverview();
  }
  var NODE_ICONS = {};
  function cacheNodeIcons() { qsa(".node").forEach(function (n) { NODE_ICONS[n.getAttribute("data-node")] = qs(".dot", n).innerHTML; }); }
  function markNodeCheck(node) { qs(".dot", node).innerHTML = '<svg viewBox="0 0 24 24" fill="none"><path d="m5 13 4 4L19 7" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"></path></svg>'; }
  function restoreNodeIcon(node, key) { qs(".dot", node).innerHTML = NODE_ICONS[key]; }
  function updateOverview() {
    var done = NODES.filter(function (k) { return state[k] === "done"; }).length;
    qs("#readyCount").textContent = String(done);
    qs("#progFill").style.width = (done / NODES.length * 100) + "%";
  }

  /* ---------------- helpers ---------------- */
  function busyBtn(btn, on) {
    if (!btn) return;
    if (on) { btn._html = btn.innerHTML; btn.disabled = true;
      btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" style="animation:spin .8s linear infinite"><path d="M12 3a9 9 0 1 0 9 9" stroke="currentColor" stroke-width="2" stroke-linecap="round"></path></svg><span>' + (lang === "en" ? "Working…" : "جارٍ…") + "</span>"; }
    else { btn.disabled = false; if (btn._html) btn.innerHTML = btn._html; }
  }
  function setImgFetched(name) {
    qs("#imgThumb").style.backgroundImage = "linear-gradient(135deg,#2a5b7a,#1c7e6f 60%,#caa877)";
    qs("#imgName").textContent = name;
    qs("#imgDrop").classList.add("filled");
  }

  /* ---------------- simulate a step ---------------- */
  function runStep(key, btn) {
    return new Promise(function (resolve, reject) {
      setStatus(key, "running");
      log(LOGMSG[key].start, "info");
      busyBtn(btn, true);
      setTimeout(function () {
        busyBtn(btn, false);
        if (aborted) { reject("aborted"); return; }
        if (key === "image" && !qs("#imgDrop").classList.contains("filled")) setImgFetched("unsplash-nature-auto.jpg");
        setStatus(key, "done");
        log(LOGMSG[key].done, "ok");
        if (key === "final") qs("#downloadFinal").disabled = false;
        resolve();
      }, DUR[key]);
    });
  }
  function noop() {}

  /* ---------------- toasts ---------------- */
  function toast(message, kind) {
    var box = qs("#toasts"), el = document.createElement("div");
    el.className = "toast " + (kind || "");
    var ic = kind === "ok" ? '<path d="m5 13 4 4L19 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>'
      : kind === "info" ? '<circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.7"></circle><path d="M12 11v5m0-8h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"></path>'
      : kind === "warn" ? '<path d="M12 4 2 20h20z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"></path><path d="M12 10v4m0 3h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"></path>'
      : '<circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.7"></circle><path d="M12 8v5m0 3h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"></path>';
    el.innerHTML = '<span class="tic"><svg width="18" height="18" viewBox="0 0 24 24" fill="none">' + ic + "</svg></span><span>" + message + "</span>";
    box.appendChild(el);
    requestAnimationFrame(function () { el.classList.add("in"); });
    setTimeout(function () { el.classList.remove("in"); setTimeout(function () { el.remove(); }, 320); }, 2600);
  }

  /* ---------------- image step ---------------- */
  var imgDrop = qs("#imgDrop"), imgInput = qs("#imgInput");
  imgDrop.addEventListener("click", function (e) {
    if (e.target.closest("#imgClear")) return;
    if (!imgDrop.classList.contains("filled")) imgInput.click();
  });
  imgInput.addEventListener("change", function () {
    var f = imgInput.files && imgInput.files[0];
    if (!f) return;
    var rd = new FileReader();
    rd.onload = function () {
      qs("#imgThumb").style.backgroundImage = "url(" + rd.result + ")";
      qs("#imgName").textContent = f.name;
      imgDrop.classList.add("filled");
      setStatus("image", "done");
      log("Custom image uploaded: " + f.name, "ok");
      toast(msg("Image uploaded", "تم رفع الصورة"), "ok");
    };
    rd.readAsDataURL(f);
  });
  qs("#imgClear").addEventListener("click", function (e) {
    e.stopPropagation();
    imgDrop.classList.remove("filled");
    qs("#imgThumb").style.backgroundImage = "";
    imgInput.value = "";
    setStatus("image", "pending");
    log("Background image cleared", "warn");
  });
  qs("#unsplashBtn").addEventListener("click", function () {
    var btn = this;
    setStatus("image", "running");
    log("Fetching nature image from Unsplash…", "info");
    busyBtn(btn, true);
    setTimeout(function () {
      busyBtn(btn, false);
      setImgFetched("unsplash-nature-" + (1000 + Math.floor(Math.random() * 8999)) + ".jpg");
      setStatus("image", "done");
      log("Background image ready", "ok");
      toast(msg("Fetched a nature image", "تم جلب صورة طبيعة"), "ok");
    }, 1200);
  });

  /* ---------------- individual steps ---------------- */
  qs("#videoBtn").addEventListener("click", function () {
    var u = qs("#videoUrl").value || qs("#channelUrl").value;
    if (u) log("Source: " + u, "info");
    runStep("video", this).then(function () { toast(msg("Video downloaded", "تم تنزيل الفيديو"), "ok"); }, noop);
  });
  qs("#overlayBtn").addEventListener("click", function () {
    if (state.video !== "done") { log("Overlay blocked — video not downloaded", "warn"); toast(msg("Download the video first", "نزّل الفيديو أولًا"), "info"); return; }
    runStep("overlay", this).then(function () { toast(msg("Text overlay extracted", "تم استخراج النص"), "ok"); }, noop);
  });
  qs("#finalBtn").addEventListener("click", function () {
    var missing = ["image", "video", "overlay"].filter(function (k) { return state[k] !== "done"; });
    if (missing.length) { log("Final blocked — missing: " + missing.join(", "), "warn"); toast(msg("Complete steps 1–3 first", "أكمل الخطوات 1–3 أولًا"), "info"); return; }
    runStep("final", this).then(function () { toast(msg("Final video created", "تم إنشاء الفيديو النهائي"), "ok"); }, noop);
  });
  qs("#downloadFinal").addEventListener("click", function () {
    log("Downloading final.mp4…", "info");
    toast(msg("Downloading final.mp4…", "جارٍ تنزيل final.mp4…"), "info");
  });

  /* ---------------- run full pipeline ---------------- */
  function runFull(btn) {
    if (running) return;
    running = true; aborted = false;
    busyBtn(btn, true);
    log("──────── Pipeline run started ────────", "info");
    var chain = Promise.resolve();
    PROC.forEach(function (key) {
      chain = chain.then(function () {
        if (aborted) return Promise.reject("aborted");
        if (state[key] === "done") { log("Skipping " + key + " — already done", "info"); return; }
        return runStep(key, null);
      });
    });
    chain.then(function () {
      log("Pipeline complete ✓", "ok");
      toast(msg("Pipeline complete", "اكتمل المسار"), "ok");
      if (qs("#autopost").checked) {
        log("Auto-post enabled — publishing to Instagram…", "info");
        return shareAsync(null);
      }
    }, function (e) {
      if (e === "aborted") log("Pipeline stopped by user", "warn");
    }).then(function () { busyBtn(btn, false); running = false; }, function () { busyBtn(btn, false); running = false; });
  }
  qs("#runFull").addEventListener("click", function () { runFull(this); });

  /* ---------------- clear all ---------------- */
  qs("#clearAll").addEventListener("click", function () {
    if (running) { toast(msg("Stop the pipeline first", "أوقف المسار أولًا"), "info"); return; }
    NODES.forEach(function (k) { setStatus(k, "pending"); });
    imgDrop.classList.remove("filled");
    qs("#imgThumb").style.backgroundImage = "";
    imgInput.value = "";
    qs("#downloadFinal").disabled = true;
    log("Pipeline cleared — all steps reset", "warn");
    toast(msg("Pipeline cleared", "تم مسح المسار"), "info");
  });

  /* ---------------- save / reset defaults ---------------- */
  var FIELDS = { image: [], video: ["#videoUrl", "#channelUrl", "#keyword"], caption: ["#caption"] };
  qsa("[data-savedefault]").forEach(function (b) {
    b.addEventListener("click", function () {
      var grp = b.getAttribute("data-savedefault"), store = {};
      (FIELDS[grp] || []).forEach(function (sel) { store[sel] = qs(sel).value; });
      try { localStorage.setItem("aq_def_" + grp, JSON.stringify(store)); } catch (e) {}
      log("Saved defaults for: " + grp, "ok");
      toast(msg("Saved as default", "تم الحفظ كافتراضي"), "ok");
    });
  });
  qsa("[data-reset]").forEach(function (b) {
    b.addEventListener("click", function () {
      var grp = b.getAttribute("data-reset");
      if (grp === "video") { qs("#videoUrl").value = ""; qs("#channelUrl").value = ""; qs("#keyword").value = "سورة"; }
      if (grp === "caption") qs("#caption").value = "⚠️ لا تنسوا اخواننا المستضعفين بالدعاء رحمكم الله ⚠️\n#لاتنسى_ذكر_الله #اكتب_شي_تؤجر_عليه";
      if (grp === "image") qs("#imgClear").click();
      log("Reset " + grp + " to default", "info");
      toast(msg("Reset to default", "تمت إعادة التعيين"), "info");
    });
  });

  /* ---------------- instagram ---------------- */
  // share is the 5th pipeline step; completes the "share" node
  function shareAsync(btn) {
    return new Promise(function (resolve, reject) {
      setStatus("share", "running");
      log("Publishing reel to Instagram…", "info");
      busyBtn(btn, true);
      setTimeout(function () {
        busyBtn(btn, false);
        if (aborted) { setStatus("share", "pending"); reject("aborted"); return; }
        setStatus("share", "done");
        log("Shared on Instagram", "ok");
        toast(msg("Shared on Instagram", "تمت المشاركة على إنستغرام"), "ok");
        resolve();
      }, 1300);
    });
  }
  function shareFlow(btn) {
    if (state.final !== "done") { log("Share blocked — final video not ready", "warn"); toast(msg("Create the final video first", "أنشئ الفيديو النهائي أولًا"), "info"); return; }
    shareAsync(btn).then(noop, noop);
  }
  qs("#shareBtn").addEventListener("click", function () { shareFlow(this); });
  qs("#shareTop").addEventListener("click", function () { shareFlow(this); });
  qs("#regenCaption").addEventListener("click", function () {
    var caps = [
      "✨ تذكير: قال تعالى ﴿فَاذْكُرُونِي أَذْكُرْكُمْ﴾\n#قرآن #ذكر_الله",
      "🌙 لا تنسوا الصلاة على النبي ﷺ\n#السلام_عليكم #قرآن_كريم",
      "⚠️ ادعوا لإخوانكم بظهر الغيب\n#لا_تنسى_ذكر_الله"
    ];
    qs("#caption").value = caps[Math.floor(Math.random() * caps.length)];
    log("Caption regenerated", "ok");
    toast(msg("Caption regenerated", "تم توليد تعليق جديد"), "ok");
  });

  /* ---------------- advanced tools ---------------- */
  var logModal = qs("#logModal");
  function openLog() { log("Opened run log (" + logN + " lines)", "info"); logModal.classList.add("open"); var c = qs("#logConsole"); c.scrollTop = c.scrollHeight; }
  function closeLog() { logModal.classList.remove("open"); }
  qs("#viewLog").addEventListener("click", openLog);
  qs("#logClose").addEventListener("click", closeLog);
  logModal.addEventListener("click", function (e) { if (e.target === logModal) closeLog(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && logModal.classList.contains("open")) closeLog(); });
  qs("#resetVideos").addEventListener("click", function () {
    setStatus("video", "pending");
    qs("#videoUrl").value = ""; qs("#channelUrl").value = "";
    log("Downloaded videos list reset", "warn");
    toast(msg("Videos list reset", "تمت إعادة تعيين القائمة"), "info");
  });
  qs("#stopAll").addEventListener("click", function () {
    if (!running) { log("No processes are running", "info"); toast(msg("Nothing is running", "لا توجد عمليات جارية"), "info"); return; }
    aborted = true;
    NODES.forEach(function (k) { if (state[k] === "running") setStatus(k, "pending"); });
    log("Stopping all running processes…", "warn");
    toast(msg("Stopping all processes…", "جارٍ إيقاف العمليات…"), "warn");
  });

  /* ---------------- run log clear ---------------- */
  qs("#logClear").addEventListener("click", function () {
    qs("#logConsole").innerHTML = ""; logN = 0; qs("#logCount").textContent = "0 lines";
    log("Log cleared", "info");
  });

  /* ---------------- scheduling ---------------- */
  var schedSaved = false;
  function renderSchedStatus() {
    var on = qs("#schedEnable").checked;
    var every = parseInt(qs("#every").value, 10) || 24;
    var startV = qs("#startTime").value || "05:48";
    var parts = startV.split(":");
    var next = new Date();
    next.setHours(parseInt(parts[0], 10), parseInt(parts[1], 10), 0, 0);
    if (next <= new Date()) next.setDate(next.getDate() + 1);
    var stamp = next.getFullYear() + "-" + pad(next.getMonth() + 1) + "-" + pad(next.getDate()) + " " + pad(next.getHours()) + ":" + pad(next.getMinutes());
    qs("#schedState").textContent = on ? msg("Active · every " + every + "h", "نشِط · كل " + every + " ساعة") : msg("Disabled", "معطّل");
    qs("#nextRun").textContent = on ? stamp : "—";
    qs("#schedStatus").style.display = "block";
  }
  qs("#saveSchedule").addEventListener("click", function () {
    schedSaved = true; renderSchedStatus();
    var on = qs("#schedEnable").checked;
    try { localStorage.setItem("aq_sched", JSON.stringify({ on: on, every: qs("#every").value, start: qs("#startTime").value })); } catch (e) {}
    log("Schedule saved — " + (on ? "active, next " + qs("#nextRun").textContent : "disabled"), "ok");
    toast(msg("Schedule saved", "تم حفظ الجدولة"), "ok");
  });
  qs("#schedEnable").addEventListener("change", function () { if (schedSaved) renderSchedStatus(); });

  /* ---------------- language ---------------- */
  qs("#langBtn").addEventListener("click", function () {
    lang = lang === "en" ? "ar" : "en";
    try { localStorage.setItem("aq_lang", lang); } catch (e) {}
    applyLang();
  });

  /* ---------------- restore persisted ---------------- */
  function restore() {
    try {
      ["video", "caption"].forEach(function (grp) {
        var raw = localStorage.getItem("aq_def_" + grp);
        if (raw) { var o = JSON.parse(raw); Object.keys(o).forEach(function (sel) { if (qs(sel)) qs(sel).value = o[sel]; }); }
      });
      var sc = localStorage.getItem("aq_sched");
      if (sc) { var s = JSON.parse(sc); qs("#schedEnable").checked = !!s.on; qs("#every").value = s.every; qs("#startTime").value = s.start; schedSaved = true; renderSchedStatus(); }
    } catch (e) {}
  }

  /* ---------------- init ---------------- */
  var st = document.createElement("style");
  st.textContent = "@keyframes spin{to{transform:rotate(360deg)}}";
  document.head.appendChild(st);

  cacheNodeIcons();
  restore();
  applyLang();
  updateOverview();
  log("System ready — Auto Quran pipeline idle", "ok");
  log("Loaded saved defaults and schedule", "info");
})();
