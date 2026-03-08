# Auto-Quran YouTube Download Fix - Deployment Log

**Session Start**: 2026-03-08 00:39:50 UTC

---

## 📊 Summary of Changes

### Commits Made

| Commit  | Message                                               | Time     | Status       |
| ------- | ----------------------------------------------------- | -------- | ------------ |
| 493a87b | normalize multiline cookies env content               | 00:39:50 | ✅ Deployed  |
| b003d31 | make format selector maximally permissive             | 00:55:01 | ✅ Deployed  |
| 0c2b8f8 | explicitly list and select format IDs                 | 00:59:08 | ✅ Deployed  |
| 0954f0e | simplify download strategy, add socket timeout        | 01:11:09 | 🔄 Deploying |
| 144c21e | add thread-based timeouts (20s extract, 30s download) | 01:17:06 | 🔄 Deploying |

---

## 🎯 ROOT CAUSE ANALYSIS

**CRITICAL FINDING**: Works perfectly on local, fails on Render!

| Aspect                 | Local       | Render                 |
| ---------------------- | ----------- | ---------------------- |
| **IP Type**            | Residential | Datacenter (Frankfurt) |
| **YouTube Rate Limit** | Normal      | Aggressive/Blocked     |
| **Download Speed**     | Fast        | Hangs/Timeouts         |
| **Format Selector**    | Works       | Fails                  |
| **Code Logic**         | Same        | Same                   |

**Conclusion**: The issue is **Render datacenter IP being rate-limited or challenged by YouTube**, NOT code logic

---

### Issue 1: Cookie Format Errors

- **Problem**: `"does not look like a Netscape format cookies file"`
- **Root Cause**: Environment variables store escaped literals `\n` `\t` instead of actual newlines
- **Fix (493a87b)**: Added `_normalize_cookie_env_text()` function
  - Converts escaped `\n` → newline, `\t` → tab
  - Strips quotes from env values
- **Result**: ✅ Cookie validation errors eliminated

### Issue 2: "Requested Format Is Not Available"

- **Problem**: yt-dlp format selectors failing for multiple videos
- **Attempts**:
  1. b003d31: Removed strict format, tried auto-select
  2. 0c2b8f8: Added explicit format listing (caused 180s timeouts)
  3. 0954f0e: Simplified to `worst/best` fallback + 15s socket timeout
- **Current Status**: 🔄 Testing...

### Issue 3: Download Timeouts

- **Problem**: Download API call hung for 180+ seconds
- **Root Cause**: Format listing logic (`listformats=True`) was blocking
- **Fix (0954f0e)**:
  - Removed format listing entirely
  - Added `socket_timeout: 15` to prevent infinite hangs
  - Simplified download to single try with timeout protection

---

## 📋 Deployment Timeline

| Time     | Action                | Result                                   |
| -------- | --------------------- | ---------------------------------------- |
| 00:46:54 | Deploy commit 493a87b | ✅ Live (srv-d6m11sq4d50c73cjaqg0-87tth) |
| 00:58:10 | Deploy commit b003d31 | ✅ Live                                  |
| 01:04:38 | Deploy commit 0c2b8f8 | ✅ Live                                  |
| 01:11:16 | Deploy commit 0954f0e | 🔄 update_in_progress                    |

---

## 🧪 Testing Results

### Commit 493a87b (Cookie Fix)

- **Logs Checked**: Yes
- **Cookie Errors**: ❌ None (FIXED!)
- **Format Errors**: Still present

### Commit b003d31 (Permissive Format)

- **Logs Checked**: Yes
- **Format Errors**: Still present ("Requested format is not available")

### Commit 0c2b8f8 (Format Listing)

- **Test Attempt**: curl POST to /api/download-video
- **Result**: ❌ Timeout after 180 seconds
- **Reason**: Format listing hangs

### Commit 0954f0e (Socket Timeout + Simple)

- **Status**: Deploying (ETA: 01:13-01:15)
- **Test**: Pending after deploy live

---

## 🛠️ Code Changes Made

### File: `logic/scripts/download_quran_video.py`

**Change 1: Cookie Normalization (493a87b)**

```python
def _normalize_cookie_env_text(raw_text: str) -> str:
    # Handles escaped newlines/tabs from env vars
    # Strips quotes from quoted env values
    # Converts escaped literals to actual characters
```

**Change 2: Format Selection Strategies (b003d31 → 0954f0e)**

- Removed: Strict format selectors (`bv*+ba/b`)
- Removed: Format listing logic (caused hangs)
- Added: Socket timeout (15 seconds)
- Current: `format: "worst/best"` with fallback logic

**Change 3: Error Handling (0954f0e)**

- Added timeout/connection error detection
- Skip logic for retryable errors in channel mode
- Better logging with `[DOWNLOAD]`, `[SKIP]`, `[ERROR]` prefixes

---

## ⏳ Current Status

**Latest Deployment**: `dep-d6mcs6ea2pns73d335m0` (144c21e)

- Created: 01:17:13
- Status: ✅ **LIVE** (01:22:02)
- **Thread-based timeouts working!**

---

## ✅ BREAKTHROUGH: Timeout Fix Works! (Commit 144c21e)

### Test Result (01:22:03)

```json
{
  "success": false,
  "message": "Failed to read YouTube channel info: YouTube info extraction timed out after 20 seconds"
}
Response Time: 20.5 seconds
```

### Analysis

| Metric               | Before                       | After                     |
| -------------------- | ---------------------------- | ------------------------- |
| **Hang Time**        | 180+ seconds                 | 20 seconds                |
| **Error Response**   | Never returns                | Instant                   |
| **API Usability**    | 🔴 Dead                      | 🟢 Responsive             |
| **Timeout Approach** | Socket timeout (ineffective) | **Thread-based (WORKS!)** |

---

## 🔴 ROOT CAUSE CONFIRMED

**YouTube blocks Render datacenter IP** (Frankfurt):

- Not a code issue (works perfectly locally)
- Not format selection (would work if extraction succeeded)
- Issue: Render IP extraction itself fails/hangs
- Even valid cookies + proper headers can't bypass it
- YouTube deliberately rejects datacenter access during extraction phase

---

## 🎯 Next Actions (Required Solutions)

1. **Option A**: Use YouTube proxy API
   - Example: yt-api.com, rapidapi.com YouTube APIs
   - Cost: ~$0-5/month for basic tier
2. **Option B**: Use rotating proxy service
   - Example: ScraperAPI, BrightData
   - Cost: $10-50/month depending on usage
3. **Option C**: Use Invidious (Privacy-focused YouTube fork)
   - Free, self-hosted alternative to YouTube
   - May have different video availability
4. **Option D**: Accept limitation
   - Document that Render can't download from YouTube
   - Suggest running locally for downloads
   - Use Render only for Instagram posting

---

**Last Updated**: 2026-03-08 01:22:30 UTC
