# Whisper Voice To Form - V5 Drive Workspace

V5 keeps the local Whisper, Gemini, PDF filling, legal drafting, matter profile, and Gmail draft features from V4, but reorganizes the app around a drive-first workspace.

The main workflow is now:

1. Choose a synced or local drive root.
2. Select a client or matter folder.
3. Review or save the matter profile.
4. Open documents from that matter folder.
5. Dictate notes, fill PDF forms, create legal work product, or draft email.
6. Export a filled PDF or update the original PDF after V5 creates a backup.

## Layout

The left side is a tabbed workspace:

- `File Hub`: drive type, drive root, matter folder picker, matter profile, and matter document list.
- `Dictation & Legal`: transcript box, grammar cleanup, legal tone rewrite, attorney notes, billing entries, timelines, client letters, and checklists.
- `Email Center`: editable To, CC, BCC, Subject, Body, Gmail OAuth connection, Gmail draft creation, and default email app fallback.
- `Form Fields`: PDF form field table, AI-filled values, Gemini field review, and template controls.

The right side is a persistent PDF viewport. It stays visible while you move across tabs, so the loaded PDF remains the center of the workspace.

## Drive Roots

V5 works with local folders. That means Computer Drive, Dropbox, OneDrive, Google Drive for Desktop, local folders, and network folders all work the same way as long as they appear as normal folders on Windows.

Use `Computer Drive` when you want to work from a normal folder on the PC, an external drive, or a local case folder that is not tied to a cloud sync service.

Use `Choose Root` in the File Hub tab to select the parent folder that contains your matter/client subfolders. V5 lists direct child folders in the matter dropdown. Pick one and click `Load Folder`.

V5 currently uses local sync folders, not Dropbox, OneDrive, or Google Drive cloud APIs.

## Matter Profiles

Matter profile fields include:

- Client
- Matter number
- Court
- Opposing party
- Drive type
- Drive root path
- Active matter folder path

When an active matter folder is loaded, `Save Profile` writes the profile into that folder. V5 keeps compatibility with V4 by using the existing hidden profile filename:

```text
.whisper-v4-profile.json
```

This keeps existing V4 matter folders usable without migration. Local profiles in `matter-profiles` remain as a fallback when no active matter folder profile is available.

If a selected matter folder has no saved profile yet, V5 infers a starter profile from folder names like:

```text
Becky Smith - Matter 24-1187 - Travis County Court
Becky Smith - Case 24-1187
```

## PDF Workflow

- Double-click a PDF in the File Hub document list to load it into the right viewport.
- Fillable PDFs open directly for preview, field editing, AI filling, export, and update.
- Flat PDFs can be converted with `Auto-Prepare Selected PDF` or the general auto-prepare command.
- Click a highlighted PDF field in the viewport to edit it in place.
- Double-click a field row in the Form Fields tab to edit its value.
- `Export Filled PDF` saves a separate copy.
- `Update Original PDF` creates a timestamped backup beside the original file, then replaces the original with the filled version.

Backups are named like:

```text
filename.backup-YYYYMMDD-HHMMSS.pdf
```

## Dictation And Legal Tools

V5 records microphone audio locally and transcribes it with `faster-whisper`. The default model is `base`, and the model cache is kept in `model-cache`.

Legal assistant tools use Gemini and are editable work product for attorney review. The prompts preserve V4's guardrails: do not invent facts, do not provide legal advice, and mark uncertain items as `TO VERIFY` where possible.

Available tools:

- Grammar cleanup
- Formal legal tone
- Attorney notes
- Billing entry
- Timeline
- Client letter
- Checklist
- Transcript to PDF form fields

## Gmail Drafts

Gmail draft creation uses Google OAuth and the Gmail compose scope. It does not send email automatically.

Setup:

1. Create a Google Cloud OAuth client for a Desktop app.
2. Enable the Gmail API for that Google Cloud project.
3. Download the OAuth client JSON.
4. Rename it to `gmail-credentials.json`.
5. Place it in this V5 app folder.
6. Click `Connect Gmail` in the app and approve Gmail compose access.

Local Gmail files:

- `gmail-credentials.json`: your OAuth client file, kept local.
- `.gmail-token.json`: your local Gmail OAuth token, created after connecting.

## Keyboard Shortcuts

- `F5`: start recording
- `F6`: stop recording and transcribe
- `F7`: create an email draft from the transcript
- `F8`: send transcript to loaded PDF fields
- `F9`: export filled PDF
- `F10`: update original PDF after backup
- `Alt + Left`: previous PDF page
- `Alt + Right`: next PDF page
- `Ctrl + L`: toggle large controls
- `Ctrl + M`: focus transcript box
- `Ctrl + H`: shortcut help

## Windows Setup

From this folder, run:

```bat
install_windows_v5.bat
launch_windows_v5.bat
```

Use `windows_launch_v5.pyw` for normal no-console launching after setup.

The default Gemini model is `gemini-flash-latest`, but you can edit the model field in the app if Google changes model access for your account.

## Important Limits

- V5 expects a local synced folder, not direct cloud API browsing.
- Standard upload/open flow works best with real fillable PDFs that contain AcroForm fields.
- Flat PDF auto-prepare is experimental and works best on clean digital forms with visible blank lines or checkbox squares.
- Gemini field review can improve auto-prepared field names and add obvious missing fields, but you should still inspect templates before repeated use.
- Always review AI-generated legal work, email drafts, and filled PDF values before using them.
- Keep `.gemini-api-key`, `gmail-credentials.json`, and `.gmail-token.json` local and out of shared folders unless you intentionally want them there.
