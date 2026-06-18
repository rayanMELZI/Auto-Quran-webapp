/* Auto Quran — dashboard logic (wired to the Flask pipeline backend).
 *
 * The visual shell, status model, log console, toasts, i18n and scheduling UI
 * are preserved from the design handoff. Every action that previously simulated
 * work with setTimeout now calls the real backend (see BACKEND-INTEGRATION.md).
 */
(function () {
  "use strict";
  var qs = function (s, r) { return (r || document).querySelector(s); };
  var qsa = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  /* ---------------- backend API helpers ---------------- */
  var API_BASE = (window.API_CONFIG && window.API_CONFIG.baseURL) || "/api";

  function apiUrl(path) { return API_BASE + path; }

  // JSON request helper. Resolves with parsed body (even on !ok) so callers can
  // read {success,message}; rejects only on network/parse failure.
  function api(path, opts) {
    opts = opts || {};
    var cfg = { method: opts.method || "GET", headers: {} };
    if (opts.body !== undefined) {
      cfg.headers["Content-Type"] = "application/json";
      cfg.body = JSON.stringify(opts.body);
    }
    return fetch(apiUrl(path), cfg).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (data) {
        data = data || {};
        if (data.success === undefined) data.success = res.ok;
        data._status = res.status;
        return data;
      });
    });
  }

  // preview URL with a cache-buster so refreshed media actually reloads
  function previewUrl(kind) { return apiUrl("/preview/" + kind) + "?t=" + Date.now(); }

  /* NODES = all overview nodes; PROC = the four runnable processing steps; "share" completes via Instagram. */
  var NODES = ["image", "video", "overlay", "final", "share"];
  var PROC = ["image", "video", "overlay", "final"];
  var state = { image: "pending", video: "pending", overlay: "pending", final: "pending", share: "pending" };
  var running = false, aborted = false;
  var lastImagePath = null;       // server path of the current background image
  var lastVideoTitle = null;

  // backend progress step status -> UI node status
  function mapBackendStatus(s) {
    if (s === "processing") return "running";
    if (s === "completed" || s === "skipped") return "done";
    return "pending"; // pending | error | unknown
  }

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
    footnote:     { en: "Connected to the Auto Quran pipeline backend.", ar: "متصل بخادم معالجة أوتو قرآن." }
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
      var stt = state[key];
      qs(".ps-label", card).textContent = stt === "running" ? t("stRunning") : stt === "done" ? t("stDone") : t("stPending");
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

  /* ---------------- status ---------------- */
  function setStatus(key, stt) {
    state[key] = stt;
    var card = qs("#step-" + key);
    if (card) {
      var pill = qs(".pill", card);
      pill.setAttribute("data-status", stt);
      qs(".ps-label", pill).textContent = stt === "running" ? t("stRunning") : stt === "done" ? t("stDone") : t("stPending");
      card.classList.toggle("done", stt === "done");
    }
    var node = qs('.node[data-node="' + key + '"]');
    if (node) {
      node.classList.remove("running", "done");
      if (stt === "running") node.classList.add("running");
      if (stt === "done") { node.classList.add("done"); markNodeCheck(node); }
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
  function showImage(thumbCss, name) {
    qs("#imgThumb").style.backgroundImage = thumbCss;
    qs("#imgName").textContent = name;
    qs("#imgDrop").classList.add("filled");
  }
  function clearImagePreview() {
    qs("#imgDrop").classList.remove("filled");
    qs("#imgThumb").style.backgroundImage = "";
    qs("#imgInput").value = "";
  }

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
  function noop() {}

  /* ---------------- progress poller (full pipeline + final render) ----------------
   * Reflects GET /api/progress onto the nodes + streams overall_message into the log.
   * Resolves once the backend marks the run inactive.
   */
  var pollTimer = null, lastOverallMsg = "";
  function stopPoll() { if (pollTimer) { clearTimeout(pollTimer); pollTimer = null; } }
  function pollProgress(onDone) {
    api("/progress").then(function (p) {
      var steps = p.steps || {};
      (p.step_order || Object.keys(steps)).forEach(function (key) {
        var uiKey = (key === "post") ? "share" : key;
        if (NODES.indexOf(uiKey) === -1) return;
        var d = steps[key] || {};
        var mapped = mapBackendStatus(d.status);
        if (mapped !== state[uiKey]) setStatus(uiKey, mapped);
        if (uiKey === "final" && d.status === "completed") qs("#downloadFinal").disabled = false;
      });
      if (p.overall_message && p.overall_message !== lastOverallMsg) {
        lastOverallMsg = p.overall_message;
        log(p.overall_message, "info");
      }
      if (p.active) {
        pollTimer = setTimeout(function () { pollProgress(onDone); }, 1000);
      } else {
        stopPoll();
        if (onDone) onDone(p);
      }
    }, function () {
      // transient network error — keep trying while we believe a run is active
      pollTimer = setTimeout(function () { pollProgress(onDone); }, 1500);
    });
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
    // instant local preview…
    var rd = new FileReader();
    rd.onload = function () { qs("#imgThumb").style.backgroundImage = "url(" + rd.result + ")"; };
    rd.readAsDataURL(f);
    qs("#imgName").textContent = f.name;
    imgDrop.classList.add("filled");
    setStatus("image", "running");
    log("Uploading custom image: " + f.name, "info");
    // …and the real upload to the backend
    var fd = new FormData();
    fd.append("image", f);
    fetch(apiUrl("/upload-image"), { method: "POST", body: fd })
      .then(function (r) { return r.json().catch(function () { return {}; }); })
      .then(function (data) {
        if (data && data.success) {
          lastImagePath = data.path || null;
          setStatus("image", "done");
          log("Custom image uploaded: " + f.name, "ok");
          toast(msg("Image uploaded", "تم رفع الصورة"), "ok");
        } else {
          setStatus("image", "pending");
          clearImagePreview();
          log("Image upload failed: " + ((data && data.message) || "unknown error"), "error");
          toast(msg("Upload failed", "فشل الرفع"), "warn");
        }
      }, function (e) {
        setStatus("image", "pending"); clearImagePreview();
        log("Image upload error: " + e, "error");
      });
  });
  qs("#imgClear").addEventListener("click", function (e) {
    e.stopPropagation();
    clearImagePreview();
    lastImagePath = null;
    setStatus("image", "pending");
    log("Background image cleared", "warn");
  });
  qs("#unsplashBtn").addEventListener("click", function () {
    var btn = this;
    setStatus("image", "running");
    log("Fetching nature image from Unsplash…", "info");
    busyBtn(btn, true);
    api("/download-image", { method: "POST", body: { query: "nature landscape" } })
      .then(function (data) {
        busyBtn(btn, false);
        if (data.success) {
          lastImagePath = data.path || null;
          showImage("url(" + previewUrl("image") + ")", "unsplash-nature.jpg");
          setStatus("image", "done");
          log(data.message || "Background image ready", "ok");
          toast(msg("Fetched a nature image", "تم جلب صورة طبيعة"), "ok");
        } else {
          setStatus("image", "pending");
          log("Image fetch failed: " + (data.message || "unknown error"), "error");
          toast(msg("Couldn't fetch image", "تعذّر جلب الصورة"), "warn");
        }
      }, function (e) {
        busyBtn(btn, false); setStatus("image", "pending");
        log("Image fetch error: " + e, "error");
        toast(msg("Network error", "خطأ في الشبكة"), "warn");
      });
  });

  /* ---------------- individual steps ---------------- */
  qs("#videoBtn").addEventListener("click", function () {
    var btn = this;
    var videoUrl = qs("#videoUrl").value.trim();
    var channelUrl = qs("#channelUrl").value.trim();
    var keyword = qs("#keyword").value.trim() || "سورة";
    setStatus("video", "running");
    log("Downloading Quran video…" + (videoUrl || channelUrl ? " (" + (videoUrl || channelUrl) + ")" : ""), "info");
    busyBtn(btn, true);
    api("/download-video", { method: "POST", body: { video_url: videoUrl || null, channel_url: channelUrl || undefined, keyword: keyword } })
      .then(function (data) {
        busyBtn(btn, false);
        if (data.success) {
          lastVideoTitle = data.title || null;
          setStatus("video", "done");
          log(data.message || "Video downloaded", "ok");
          toast(msg("Video downloaded", "تم تنزيل الفيديو"), "ok");
        } else {
          setStatus("video", "pending");
          var lvl = data.duplicate ? "warn" : "error";
          log("Video download failed: " + (data.message || "unknown error"), lvl);
          toast(data.duplicate ? msg("Already downloaded", "تم تنزيله مسبقًا") : msg("Download failed", "فشل التنزيل"), data.duplicate ? "info" : "warn");
        }
      }, function (e) {
        busyBtn(btn, false); setStatus("video", "pending");
        log("Video download error: " + e, "error");
        toast(msg("Network error", "خطأ في الشبكة"), "warn");
      });
  });
  qs("#overlayBtn").addEventListener("click", function () {
    var btn = this;
    if (state.video !== "done") { log("Overlay blocked — video not downloaded", "warn"); toast(msg("Download the video first", "نزّل الفيديو أولًا"), "info"); return; }
    setStatus("overlay", "running");
    log("Extracting verse text overlay…", "info");
    busyBtn(btn, true);
    api("/extract-text", { method: "POST", body: {} })
      .then(function (data) {
        busyBtn(btn, false);
        if (data.success) {
          setStatus("overlay", "done");
          log(data.message || "Text overlay extracted", "ok");
          toast(msg("Text overlay extracted", "تم استخراج النص"), "ok");
        } else {
          setStatus("overlay", "pending");
          log("Overlay extraction failed: " + (data.message || "unknown error"), "error");
          toast(msg("Extraction failed", "فشل الاستخراج"), "warn");
        }
      }, function (e) {
        busyBtn(btn, false); setStatus("overlay", "pending");
        log("Overlay extraction error: " + e, "error");
      });
  });
  qs("#finalBtn").addEventListener("click", function () {
    var btn = this;
    var missing = ["image", "video"].filter(function (k) { return state[k] !== "done"; });
    if (missing.length) { log("Final blocked — missing: " + missing.join(", "), "warn"); toast(msg("Complete the image & video first", "أكمل الصورة والفيديو أولًا"), "info"); return; }
    setStatus("final", "running");
    log("Composing final video…", "info");
    busyBtn(btn, true);
    lastOverallMsg = "";
    pollProgress(null); // stream encoding % into the log while the request runs
    api("/create-final-video", { method: "POST", body: {} })
      .then(function (data) {
        busyBtn(btn, false);
        stopPoll();
        if (data.success) {
          setStatus("final", "done");
          qs("#downloadFinal").disabled = false;
          log(data.message || "Final video rendered", "ok");
          toast(msg("Final video created", "تم إنشاء الفيديو النهائي"), "ok");
        } else {
          setStatus("final", "pending");
          log("Final video failed: " + (data.message || "unknown error"), "error");
          toast(msg("Render failed", "فشل التركيب"), "warn");
        }
      }, function (e) {
        busyBtn(btn, false); stopPoll(); setStatus("final", "pending");
        log("Final video error: " + e, "error");
      });
  });
  qs("#downloadFinal").addEventListener("click", function () {
    log("Opening final video…", "info");
    window.open(apiUrl("/preview/final"), "_blank");
  });

  /* ---------------- run full pipeline ---------------- */
  function runFull(btn) {
    if (running) { toast(msg("Pipeline already running", "المسار قيد التشغيل"), "info"); return; }
    running = true; aborted = false;
    busyBtn(btn, true);
    lastOverallMsg = "";
    log("──────── Pipeline run started ────────", "info");
    var autopost = qs("#autopost").checked;
    api("/run-full-pipeline", {
      method: "POST",
      body: {
        skip_text_overlay: false,
        auto_post: autopost,
        caption: qs("#caption").value,
        channel_url: qs("#channelUrl").value.trim() || undefined,
        keyword: qs("#keyword").value.trim() || "سورة",
        video_url: qs("#videoUrl").value.trim() || null
      }
    }).then(function (data) {
      if (!data.success) {
        running = false; busyBtn(btn, false);
        log("Could not start pipeline: " + (data.message || "unknown error"), "error");
        toast(msg("Couldn't start pipeline", "تعذّر بدء المسار"), "warn");
        return;
      }
      log(data.message || "Pipeline started", "info");
      pollProgress(function (p) {
        running = false; busyBtn(btn, false);
        var ok = p && p.overall_percent === 100;
        if (aborted) { log("Pipeline stopped by user", "warn"); }
        else if (ok) { log("Pipeline complete ✓", "ok"); toast(msg("Pipeline complete", "اكتمل المسار"), "ok"); }
        else { log(p && p.overall_message ? p.overall_message : "Pipeline ended", "warn"); toast(msg("Pipeline ended", "انتهى المسار"), "info"); }
      });
    }, function (e) {
      running = false; busyBtn(btn, false);
      log("Pipeline start error: " + e, "error");
      toast(msg("Network error", "خطأ في الشبكة"), "warn");
    });
  }
  qs("#runFull").addEventListener("click", function () { runFull(this); });

  /* ---------------- clear all ---------------- */
  qs("#clearAll").addEventListener("click", function () {
    if (running) { toast(msg("Stop the pipeline first", "أوقف المسار أولًا"), "info"); return; }
    api("/reset", { method: "POST", body: {} }).then(noop, noop);
    NODES.forEach(function (k) { setStatus(k, "pending"); });
    clearImagePreview();
    lastImagePath = null;
    qs("#downloadFinal").disabled = true;
    log("Pipeline cleared — all steps reset", "warn");
    toast(msg("Pipeline cleared", "تم مسح المسار"), "info");
  });

  /* ---------------- save / reset defaults ---------------- */
  // maps a UI group to the backend settings keys it owns
  function saveDefaults(grp) {
    if (grp === "video") {
      return api("/settings", { method: "POST", body: {
        default_channel_url: qs("#channelUrl").value.trim(),
        default_keyword: qs("#keyword").value.trim() || "سورة"
      }});
    }
    if (grp === "caption") {
      return api("/settings", { method: "POST", body: { default_caption: qs("#caption").value }});
    }
    if (grp === "image") {
      return api("/settings", { method: "POST", body: { default_image_path: lastImagePath }});
    }
    return Promise.resolve({ success: true });
  }
  qsa("[data-savedefault]").forEach(function (b) {
    b.addEventListener("click", function () {
      var grp = b.getAttribute("data-savedefault");
      if (grp === "image" && !lastImagePath) { toast(msg("Set an image first", "اختر صورة أولًا"), "info"); return; }
      saveDefaults(grp).then(function (data) {
        if (data.success) { log("Saved defaults for: " + grp, "ok"); toast(msg("Saved as default", "تم الحفظ كافتراضي"), "ok"); }
        else { log("Save default failed for " + grp + ": " + (data.message || ""), "error"); toast(msg("Save failed", "فشل الحفظ"), "warn"); }
      }, function (e) { log("Save default error: " + e, "error"); });
    });
  });
  // factory defaults restored client-side; backend keys reset via /settings/reset-default
  var RESET_KEYS = { video: ["default_channel_url", "default_keyword"], caption: ["default_caption"], image: ["default_image_path"] };
  qsa("[data-reset]").forEach(function (b) {
    b.addEventListener("click", function () {
      var grp = b.getAttribute("data-reset");
      (RESET_KEYS[grp] || []).forEach(function (key) { api("/settings/reset-default", { method: "POST", body: { key: key } }).then(noop, noop); });
      if (grp === "video") { qs("#videoUrl").value = ""; qs("#channelUrl").value = ""; qs("#keyword").value = "سورة"; }
      if (grp === "caption") qs("#caption").value = "⚠️ لا تنسوا اخواننا المستضعفين بالدعاء رحمكم الله ⚠️\n#لاتنسى_ذكر_الله #اكتب_شي_تؤجر_عليه";
      if (grp === "image") { clearImagePreview(); lastImagePath = null; setStatus("image", "pending"); }
      log("Reset " + grp + " to default", "info");
      toast(msg("Reset to default", "تمت إعادة التعيين"), "info");
    });
  });

  /* ---------------- instagram ---------------- */
  // share is the 5th pipeline step; completes the "share" node
  function shareAsync(btn) {
    setStatus("share", "running");
    log("Publishing reel to Instagram…", "info");
    busyBtn(btn, true);
    return api("/post-to-instagram", { method: "POST", body: { caption: qs("#caption").value } })
      .then(function (data) {
        busyBtn(btn, false);
        if (data.success) {
          setStatus("share", "done");
          log(data.message || "Shared on Instagram", "ok");
          toast(msg("Shared on Instagram", "تمت المشاركة على إنستغرام"), "ok");
        } else {
          setStatus("share", "pending");
          log("Instagram share failed: " + (data.message || "unknown error"), "error");
          toast(msg("Share failed", "فشلت المشاركة"), "warn");
        }
      }, function (e) {
        busyBtn(btn, false); setStatus("share", "pending");
        log("Instagram share error: " + e, "error");
        toast(msg("Network error", "خطأ في الشبكة"), "warn");
      });
  }
  function shareFlow(btn) {
    if (state.final !== "done") { log("Share blocked — final video not ready", "warn"); toast(msg("Create the final video first", "أنشئ الفيديو النهائي أولًا"), "info"); return; }
    shareAsync(btn);
  }
  qs("#shareBtn").addEventListener("click", function () { shareFlow(this); });
  qs("#shareTop").addEventListener("click", function () { shareFlow(this); });
  qs("#regenCaption").addEventListener("click", function () {
    // client-side caption templates (backend has no generation endpoint)
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
    api("/reset-downloaded-videos", { method: "POST", body: {} }).then(function (data) {
      if (data.success) { log(data.message || "Downloaded videos list reset", "warn"); toast(msg("Videos list reset", "تمت إعادة تعيين القائمة"), "info"); }
      else { log("Reset videos failed: " + (data.message || ""), "error"); toast(msg("Reset failed", "فشلت العملية"), "warn"); }
    }, function (e) { log("Reset videos error: " + e, "error"); });
    setStatus("video", "pending");
    qs("#videoUrl").value = ""; qs("#channelUrl").value = "";
  });
  qs("#stopAll").addEventListener("click", function () {
    aborted = true;
    log("Stopping all running processes…", "warn");
    toast(msg("Stopping all processes…", "جارٍ إيقاف العمليات…"), "warn");
    api("/stop-all", { method: "POST", body: {} }).then(function (data) {
      stopPoll();
      NODES.forEach(function (k) { if (state[k] === "running") setStatus(k, "pending"); });
      running = false;
      log(data.message || "Stop signal sent", "warn");
    }, function (e) { log("Stop error: " + e, "error"); });
  });

  /* ---------------- run log clear ---------------- */
  qs("#logClear").addEventListener("click", function () {
    qs("#logConsole").innerHTML = ""; logN = 0; qs("#logCount").textContent = "0 lines";
    log("Log cleared", "info");
  });

  /* ---------------- scheduling ---------------- */
  var schedSaved = false;
  function renderSchedStatus(serverNextRun) {
    var on = qs("#schedEnable").checked;
    var every = parseInt(qs("#every").value, 10) || 24;
    var stamp = serverNextRun;
    if (!stamp) {
      var startV = qs("#startTime").value || "05:48";
      var parts = startV.split(":");
      var next = new Date();
      next.setHours(parseInt(parts[0], 10), parseInt(parts[1], 10), 0, 0);
      if (next <= new Date()) next.setDate(next.getDate() + 1);
      stamp = next.getFullYear() + "-" + pad(next.getMonth() + 1) + "-" + pad(next.getDate()) + " " + pad(next.getHours()) + ":" + pad(next.getMinutes());
    }
    qs("#schedState").textContent = on ? msg("Active · every " + every + "h", "نشِط · كل " + every + " ساعة") : msg("Disabled", "معطّل");
    qs("#nextRun").textContent = on ? stamp : "—";
    qs("#schedStatus").style.display = "block";
  }
  qs("#saveSchedule").addEventListener("click", function () {
    var on = qs("#schedEnable").checked;
    var every = parseInt(qs("#every").value, 10) || 24;
    var startTime = qs("#startTime").value || "05:48";
    api("/cronjob/configure", { method: "POST", body: { enabled: on, interval_hours: every, time: startTime } })
      .then(function (data) {
        if (!data.success) { log("Schedule save failed: " + (data.message || ""), "error"); toast(msg("Save failed", "فشل الحفظ"), "warn"); return; }
        schedSaved = true;
        // pull the authoritative next-run time from the backend
        api("/cronjob/status").then(function (s) {
          var nr = (s && s.next_run && s.next_run !== "None") ? s.next_run : null;
          renderSchedStatus(nr);
          log("Schedule saved — " + (on ? "active, next " + qs("#nextRun").textContent : "disabled"), "ok");
          toast(msg("Schedule saved", "تم حفظ الجدولة"), "ok");
        }, function () { renderSchedStatus(); });
      }, function (e) { log("Schedule save error: " + e, "error"); });
  });
  qs("#schedEnable").addEventListener("change", function () { if (schedSaved) renderSchedStatus(); });

  /* ---------------- language ---------------- */
  qs("#langBtn").addEventListener("click", function () {
    lang = lang === "en" ? "ar" : "en";
    try { localStorage.setItem("aq_lang", lang); } catch (e) {}
    applyLang();
  });

  /* ---------------- initial load (backend is source of truth) ---------------- */
  function loadState() {
    api("/state").then(function (s) {
      if (s.has_image) { showImage("linear-gradient(135deg,#2a5b7a,#1c7e6f 60%,#caa877)", "background.jpg"); setStatus("image", "done"); }
      if (s.has_video) { lastVideoTitle = s.video_title || null; setStatus("video", "done"); }
      if (s.has_overlay) setStatus("overlay", "done");
      if (s.has_final) { setStatus("final", "done"); qs("#downloadFinal").disabled = false; }
    }, noop);
  }
  function loadSettings() {
    api("/settings").then(function (r) {
      var s = (r && r.settings) || {};
      if (s.default_channel_url) qs("#channelUrl").value = s.default_channel_url;
      if (s.default_keyword) qs("#keyword").value = s.default_keyword;
      if (s.default_caption) qs("#caption").value = s.default_caption;
    }, noop);
  }
  function loadSchedule() {
    api("/cronjob/status").then(function (s) {
      if (!s || !s.success) return;
      qs("#schedEnable").checked = !!s.enabled;
      if (s.interval_hours) qs("#every").value = s.interval_hours;
      if (s.time) qs("#startTime").value = s.time;
      if (s.enabled || (s.next_run && s.next_run !== "None")) {
        schedSaved = true;
        renderSchedStatus((s.next_run && s.next_run !== "None") ? s.next_run : null);
      }
    }, noop);
  }
  // If a run is already in progress on the server (e.g. a cronjob run), attach to it.
  function attachIfRunning() {
    api("/progress").then(function (p) {
      if (p && p.active) {
        running = true;
        busyBtn(qs("#runFull"), true);
        log("Attached to a running pipeline…", "info");
        pollProgress(function (pp) {
          running = false; busyBtn(qs("#runFull"), false);
          if (pp && pp.overall_percent === 100) { log("Pipeline complete ✓", "ok"); }
        });
      }
    }, noop);
  }

  /* ---------------- init ---------------- */
  var styleEl = document.createElement("style");
  styleEl.textContent = "@keyframes spin{to{transform:rotate(360deg)}}";
  document.head.appendChild(styleEl);

  cacheNodeIcons();
  applyLang();
  updateOverview();
  loadSettings();
  loadState();
  loadSchedule();
  attachIfRunning();
  log("System ready — Auto Quran dashboard connected", "ok");
})();
