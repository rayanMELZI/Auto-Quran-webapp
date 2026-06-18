# Backend Integration — Auto Quran Dashboard

This maps every UI control to a backend operation. In the reference `auto-quran.js`, each action is **simulated** with `setTimeout`. Replace each simulation with a real call to your existing pipeline backend. Endpoint paths below are a **suggested contract** — rename to match the routes you already have; what matters is the request/response *shape* and the status model.

> Conventions: all responses JSON unless noted. Long-running steps should return quickly and report progress/completion via the **status** and **log** channels (polling or SSE). Every state change the backend makes must be reflected in the UI via `setStatus(key, 'pending'|'running'|'done')` and `log(message, level)`.

---

## 0. Status & logs (the backbone)

### Pipeline status
`GET /api/pipeline/status` →
```json
{
  "image":   "pending|running|done",
  "video":   "pending|running|done",
  "overlay": "pending|running|done",
  "final":   "pending|running|done",
  "share":   "pending|running|done",
  "running": false,
  "final_file": "final.mp4"        // present when final is done
}
```
Frontend: on load and every ~2s while `running` (or via SSE), call this and apply `setStatus(key, value)` for each key, set `#downloadFinal.disabled = status.final !== 'done'`. This replaces the prototype's local `state` object as the source of truth. (Maps to the old "Pipeline Status: Image/Video/Overlay/Final ready/not ready" panel.)

### Run log stream
Prefer **SSE**: `GET /api/logs/stream` emitting lines:
```json
{ "ts": "2026-06-13T05:48:02Z", "level": "info|ok|warn|error", "message": "Downloading Quran video…" }
```
Frontend: for each event call `log(message, level)`. Fallback: `GET /api/logs?since=<cursor>` polled while running. The log modal (`#logConsole`) renders whatever `log()` receives — no other change needed. Keep `#logClear` as a client-only clear (or `DELETE /api/logs` if you want server truncation).

---

## 1. Background Image  (`#step-image`)
- **Fetch from Unsplash** (`#unsplashBtn`): `POST /api/steps/image/fetch` `{ query?: "nature" }` → `{ ok, file, thumbUrl, width, height }`.
  - On click: `setStatus('image','running')`; on success show `thumbUrl` in `#imgThumb`, set `#imgName`, add `.filled` to `#imgDrop`, `setStatus('image','done')`.
- **Upload custom** (`#imgInput` change): `POST /api/steps/image/upload` (multipart `file`) → `{ ok, file, thumbUrl }`. Same UI flow. (Prototype reads the file locally with `FileReader` for instant preview — keep that for UX, but the upload must reach the server.)
- **Remove** (`#imgClear`): `POST /api/steps/image/clear` → `setStatus('image','pending')`.
- **Save as default / Reset** (`[data-savedefault="image"]` / `[data-reset="image"]`): `POST /api/defaults/image` / `POST /api/defaults/image/reset`. (Old "Save As Default Image" / "Reset To Default".)

## 2. Quran Video  (`#step-video`)
- **Download Video** (`#videoBtn`): `POST /api/steps/video/download`
  ```json
  { "videoUrl": "...", "channelUrl": "...", "keyword": "سورة" }
  ```
  → `{ ok, file, duration, resolution }`. Flow: `setStatus('video','running')` → on success `setStatus('video','done')`.
  - Validation: at least one of `videoUrl` / `channelUrl` required. `keyword` is used only with `channelUrl` (pick the latest matching upload). Mirrors the original "Optional Video URL / Optional Channel URL / Keyword".
- **Save as default / Reset** (group `video`): persist `{ videoUrl, channelUrl, keyword }` via `POST /api/defaults/video` (+ `/reset`).

## 3. Text Overlay  (`#step-overlay`)
- **Extract Text** (`#overlayBtn`): `POST /api/steps/overlay/extract` → `{ ok, segments: [...] }`.
  - Gate: requires `video === 'done'` (frontend already blocks otherwise with a WARN log + toast).

## 4. Final Video  (`#step-final`)
- **Create Final Video** (`#finalBtn`): `POST /api/steps/final/create` → `{ ok, file: "final.mp4" }`.
  - Gate: requires `image`, `video`, `overlay` all `done`.
  - On success: `setStatus('final','done')`, enable `#downloadFinal`.
- **Download** (`#downloadFinal`): `GET /api/final/download` → streams the mp4 (set `Content-Disposition`). Frontend can just `window.location = '/api/final/download'`.

## 5. Share  (Instagram — this is the 5th pipeline node, no separate card)
- **Share on Instagram** (`#shareBtn` in the Instagram block, and `#shareTop` in the app bar): `POST /api/instagram/share`
  ```json
  { "caption": "<#caption value>" }
  ```
  → `{ ok, postId, permalink }`. Flow: `setStatus('share','running')` → on success `setStatus('share','done')`.
  - Gate: requires `final === 'done'`.
  - This is the same Instagram account linked for the user's Quran page. (Maps to the original green "Share on Instagram" button.)

---

## Run Full Pipeline  (`#runFull`)
Two valid implementations — pick what fits your backend:

**A. Server-orchestrated (recommended):** `POST /api/pipeline/run` `{ autopost: <#autopost.checked> }` → `{ ok, runId }`. The server runs image→video→overlay→final (then share if `autopost`), emitting status + log events. The frontend just disables the button, subscribes to status/logs, and re-enables when `status.running` goes false.

**B. Client-orchestrated:** the frontend calls each step endpoint in sequence (as the prototype's `runFull` does), then `POST /api/instagram/share` if `#autopost` is checked. Simpler backend, but the client must stay open.

The **Auto-post** toggle (`#autopost`) only controls whether step 5 (share) runs at the end of a full run. (Original: "Auto post to Instagram after full pipeline".)

## Stop all running processes  (`#stopAll`)
`POST /api/pipeline/stop` → kills any running ffmpeg/download/post jobs. Frontend sets `aborted`, resets any `running` node to `pending`, logs WARN. (New control, from your advanced-tools spec.)

## Reset downloaded videos list  (`#resetVideos`)
`POST /api/videos/reset` → clears the server's record of already-downloaded videos (so the channel fetcher will re-pull). Frontend resets the video step to `pending` and clears the URL fields. (New control, from your advanced-tools spec.)

## Clear all  (`#clearAll`)
Pipeline reset. `POST /api/pipeline/clear` → backend discards the current run's artifacts (image/video/overlay/final) and returns all-pending status. Frontend resets all 5 nodes + image preview. **Distinct from the log's Clear button**, which only empties the log view.

---

## Caption tools (Instagram block)
- **Caption** (`#caption`): default Arabic text is pre-filled. Sent with every share.
- **Regenerate** (`#regenCaption`): either keep client-side templates (as the prototype does) **or** `POST /api/instagram/caption/regenerate` → `{ caption }` if you generate server-side. (New placement; the action existed before.)
- **Save as default / Reset** (group `caption`): `POST /api/defaults/caption` (+ `/reset`). (Original "Save As Default Caption" / "Reset To Default".)

## Automated Scheduling (cronjob)
- **Save Schedule** (`#saveSchedule`): `POST /api/schedule`
  ```json
  { "enabled": <#schedEnable.checked>, "everyHours": <#every>, "startTime": "05:48" }
  ```
  → `{ ok, active, nextRun: "2026-06-13 05:48", jobCount }`. Frontend shows status (`#schedState`) and `#nextRun`.
- **Load on init:** `GET /api/schedule` → populate `#schedEnable`, `#every`, `#startTime`, and the status box.
- Backend creates/updates the cron entry that triggers `POST /api/pipeline/run { autopost:true }` at the interval. (Maps to the original "Enable Cronjob / Run every (hours) / Start time / Status: Active (N jobs) / Next run".)

---

## Defaults endpoint (consolidated)
`GET /api/defaults` → `{ image: {...}, video: { videoUrl, channelUrl, keyword }, caption: { text } }`, applied on load. `POST /api/defaults/<group>` saves; `POST /api/defaults/<group>/reset` restores factory values. Replaces the prototype's `localStorage` defaults (`aq_def_*`).

---

## Wiring checklist (where to edit `auto-quran.js`)
Each prototype handler to convert from simulated → real:
- `#unsplashBtn` click → image/fetch
- `#imgInput` change → image/upload
- `#imgClear` → image/clear
- `#videoBtn` → video/download
- `#overlayBtn` → overlay/extract
- `#finalBtn` → final/create  •  `#downloadFinal` → final/download
- `#shareBtn` / `#shareTop` → instagram/share
- `#runFull` → pipeline/run (or client sequence)
- `#stopAll` → pipeline/stop  •  `#resetVideos` → videos/reset  •  `#clearAll` → pipeline/clear
- `#saveSchedule` → schedule (POST)  •  init → schedule (GET)
- `[data-savedefault]` / `[data-reset]` → defaults
- add a status poller / SSE subscriber calling `setStatus` + `log`

Keep the UI helpers (`setStatus`, `log`, `toast`, `busyBtn`, the modal, i18n) exactly as-is — they're the contract the backend feeds. Replace only the bodies that currently `setTimeout`.
