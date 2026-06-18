# Auto Quran — Dashboard Redesign Handoff

## Goal
Replace the **existing Auto Quran frontend** (the purple/AI-template "Auto Quran Video Creator" page) with this redesigned, on-brand dashboard, and wire every control to the **existing backend pipeline**. This package contains the reference implementation (HTML + JS) and two docs:

- **README.md** (this file) — design system, layout, components, state, behaviors.
- **BACKEND-INTEGRATION.md** — every UI action mapped to a backend endpoint, with request/response contracts, the status model, log streaming, and scheduling. **Read this to wire the backend.**

## What this screen is
A control dashboard for an automated Quran-video pipeline. The user produces a vertical Quran reel through 5 sequential stages and can post it to Instagram automatically or on a schedule. The product is part of the larger **Wisdom From Quran** project; this dashboard shares its visual language (deep navy + gold + cyan, glassmorphism, El Messiri / Tajawal type).

The five pipeline stages:
1. **Background Image** — upload a custom image or fetch a nature image (Unsplash).
2. **Quran Video** — download a source clip by video URL, or from a channel URL + keyword.
3. **Text Overlay** — extract the verse text to overlay on the clip.
4. **Final Video** — compose image + clip + text into the final reel (downloadable).
5. **Share** — publish the reel to Instagram (manual button, or automatic when Auto-post is on / via Run Full Pipeline).

---

## Treat these files as a REFERENCE
The HTML/CSS/JS here is a **working prototype that defines the target look and behavior** — it is not meant to ship as-is. Rebuild it inside the existing codebase using that project's framework, components, and conventions. The JS (`auto-quran.js`) currently **simulates** all backend work with `setTimeout`; your job is to swap each simulated action for a real backend call (see BACKEND-INTEGRATION.md). The design tokens, layout, status model, log console, and i18n approach should be reproduced faithfully.

**Performance note:** the background is a deliberately lightweight **CSS aurora** (two slow GPU-cheap drifting blurred blobs over layered radial gradients) — *not* a WebGL shader. This is intentional: it's a working tool, so keep the background cheap. Respect `prefers-reduced-motion` (blobs freeze).

---

## Design system

### Colors (CSS variables)
| Token | Value | Use |
|---|---|---|
| `--navy-950` | `#04101f` | page base |
| `--navy-900` | `#06182b` | deep surfaces |
| `--cyan` | `#69c0e6` | primary accent, running state, info |
| `--cyan-deep` | `#2f7fb0` | accent gradient end |
| `--gold` | `#dcc29c` | brand accent, done/ready state |
| `--gold-soft` | `#ecd9bb` | gold highlights, active rings |
| `--green` | `#5fcaa0` | Instagram / success actions |
| `--text` | `#eef4fa` | primary text |
| `--muted` | `#bccbdc` | secondary text |
| `--faint` | `#8ea4ba` | tertiary text, log timestamps |
| `--glass` | `rgba(11,24,41,0.55)` | glass panels |
| `--glass-2` | `rgba(13,28,48,0.70)` | denser glass (toasts, modal) |
| `--hair` | `rgba(150,185,215,0.16)` | hairline borders |
| `--hair-gold` | `rgba(220,194,156,0.30)` | gold hairline borders |

Log levels: INFO → cyan, OK → green, WARN → `#e8c07a`, ERROR → `#f0a3a3`.

### Typography (Google Fonts)
- **El Messiri** (600/700) — all headings, step numbers, counts.
- **Tajawal** (300–700) — body, labels, buttons, inputs (works for Arabic + Latin).
- Monospace stack (`ui-monospace, SFMono-Regular, Menlo, Consolas`) — the run-log console only.

### Shape / effects
- Radii: `--r-lg:22px` (cards), `--r-md:15px`, `--r-sm:11px` (fields), pills `999px`.
- Glass: `backdrop-filter: blur(20px) saturate(1.25)` + hairline border + soft drop shadow + inset top highlight.
- Buttons: pill-shaped. Variants: `.btn-gold` (primary), `.btn-green` (Instagram), `.btn-cyan` (step actions), `.btn-ghost` (secondary), `.btn-text` (utility/inline). `.btn-sm`, `.btn-block` modifiers. Disabled = 40% opacity, no shadow.
- Custom `.switch` toggle (cyan-gradient when on).

---

## Layout

```
┌───────────────────────────────────────────────────────────────┐
│ APP BAR (sticky glass): [emblem] Auto Quran   [lang][Run Full Pipeline][Share to Instagram]
├───────────────────────────────────────────────────────────────┤
│ OVERVIEW (glass): Pipeline    [Clear all]  N of 5 ready         │
│   ● Background ── ● Video ── ● Overlay ── ● Final ── ● Share    │
│   [progress bar]                                                │
├──────────────────────────────────┬────────────────────────────┤
│ MAIN (1.55fr)                     │ RAIL (1fr)                  │
│  Step 1 · Background Image        │  Automation                 │
│  Step 2 · Quran Video             │   (Auto-post + Scheduling)  │
│  Step 3 · Text Overlay            │  Post to Instagram          │
│  Step 4 · Final Video             │  Advanced tools             │
│  (Step 5 "Share" lives in nav +   │                             │
│   the Instagram block, not a card)│                             │
└──────────────────────────────────┴────────────────────────────┘
Run-log MODAL (opened by "View run log"; closable via ✕ / Esc / backdrop)
```
- Grid collapses to a single column ≤980px. App-bar actions wrap on narrow screens.
- The emblem is an inline SVG (8-point gold star + cyan core) — the shared Wisdom From Quran mark.

### Components & element IDs (the JS hooks)
- **App bar:** `#langBtn`, `#runFull`, `#shareTop`.
- **Overview:** nodes `.node[data-node="image|video|overlay|final|share"]`, `#readyCount`, `#progFill`, `#clearAll`.
- **Step 1 (image):** `#step-image`, dropzone `#imgDrop` + hidden `#imgInput`, preview `#imgThumb`/`#imgName`/`#imgClear`, `#unsplashBtn`, defaults `[data-savedefault="image"]` / `[data-reset="image"]`.
- **Step 2 (video):** `#step-video`, `#videoUrl`, `#channelUrl`, `#keyword`, `#videoBtn`, defaults `video`.
- **Step 3 (overlay):** `#step-overlay`, `#overlayBtn`.
- **Step 4 (final):** `#step-final`, `#finalBtn`, `#downloadFinal` (disabled until final ready).
- **Automation:** `#autopost`, `#schedEnable`, `#every`, `#startTime`, `#saveSchedule`, status `#schedStatus`/`#schedState`/`#nextRun`.
- **Instagram:** `#caption`, `#regenCaption`, `#shareBtn`, defaults `caption`.
- **Advanced tools:** `#viewLog`, `#resetVideos`, `#stopAll`.
- **Log modal:** `#logModal`, console `#logConsole`, `#logCount`, `#logClear`, `#logClose`.
- Each step card has a status pill `.pill[data-status]` with `.ps-label`.

---

## Status model (drives the overview + pills)
Each of the 5 nodes is in one of three states:
- `pending` — neutral/faint dot, pill "Pending".
- `running` — cyan pulsing dot, pill "Running".
- `done` — gold dot + checkmark, pill "Ready", connector fills gold.

`setStatus(key, state)` updates: the step-card pill (if a card exists — `share` has no card), the overview node, the progress bar (`doneCount / 5`), and the ready count. `updateOverview()` recomputes from `state`.

The frontend keeps a local `state` object; the **backend is the source of truth** — poll `GET /pipeline/status` (or subscribe) and reflect it via `setStatus`. See BACKEND-INTEGRATION.md.

---

## Behaviors
- **Run Full Pipeline** (`#runFull`): runs steps 1→4 in order, then — only if Auto-post is on — runs step 5 (share). Shows spinners, logs each stage, toasts on completion. Disabled re-entry while running.
- **Individual step buttons** run a single stage; gated sensibly (overlay needs video; final needs 1–3; share needs final).
- **Share** (`#shareTop` and `#shareBtn`): posts the current `#caption` to Instagram; marks the **Share** node done. Requires final ready.
- **Stop all running processes** (`#stopAll`): aborts an in-flight run, resets any `running` step to `pending`, logs a WARN.
- **Clear all** (`#clearAll`): resets all 5 nodes to pending (and the image preview). This is the *pipeline* reset — distinct from the log's Clear.
- **Run log:** an in-memory, timestamped, color-coded console. It is **only** shown in a modal opened by **View run log** (`#viewLog`); closes via ✕ / `Esc` / backdrop click. Logs accumulate even while the modal is closed. `#logClear` empties it.
- **Save as default / Reset:** per group (image, video fields, caption) — persist defaults and restore on load.
- **Scheduling:** Enable + every-hours + start-time → Save computes & shows the next run time and an Active/Disabled status.
- **Language:** `#langBtn` swaps all `[data-i18n]` copy between English and Arabic (text only — layout direction stays LTR, matching the home page). Persisted.

### Persistence (prototype uses localStorage — replace with backend)
`aq_lang`, `aq_def_video`, `aq_def_caption`, `aq_sched`. In production these defaults + schedule should live in the backend (see integration doc); keep only `aq_lang` client-side if desired.

---

## i18n
All visible chrome carries `data-i18n="key"`; the `I18N` dictionary in `auto-quran.js` holds `{en, ar}` per key. **Run-log lines stay English** (technical logs). If the codebase already has an i18n system, port the strings into it instead of the inline dictionary. Default language is currently **English** — confirm with the product owner whether to default to Arabic.

## Files
- `Auto Quran - Dashboard.html` — full reference (markup + all CSS).
- `auto-quran.js` — all behavior; the functions to rewire are flagged in **BACKEND-INTEGRATION.md**.
