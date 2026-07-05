# Whisper Voice To Form - V6

V6 keeps the V3 PDF form workflow and adds a Word document editing workflow driven by local transcription plus Gemini.

## What V6 Can Do

1. Records microphone audio locally.
2. Transcribes it with `faster-whisper`.
3. Loads fillable PDFs, previews fields, fills them with Gemini, and exports filled copies.
4. Auto-prepares some flat PDFs into reusable fillable templates.
5. Reviews detected PDF fields with Gemini to improve names and add obvious missing fields.
6. Creates editable email drafts from transcript text and can save Gmail drafts.
7. Uploads Word `.docx` files.
8. Shows numbered Word paragraphs in a review panel.
9. Uses Gemini to map a spoken edit instruction to one exact DOCX change.
10. Applies that DOCX change locally and saves an edited `.docx` copy.

## DOCX Workflow

Use the DOCX path like this:

1. Click `Upload Word Document`.
2. Record or type the edit instruction in the transcript box.
3. Optionally select the paragraph you think should change to give Gemini a hint.
4. Click `Apply Transcript To DOCX`.
5. Review the selected paragraph and the last-change summary.
6. Click `Save Edited DOCX`.

V6 works best when the spoken instruction is explicit, for example:

- `After the sentence that says payment is due on receipt, add this exact sentence: Payment must be received within ten business days.`
- `Replace the sentence that begins with The tenant shall with this exact sentence: The tenant shall maintain the premises in good working order.`
- `Insert a new paragraph after paragraph 12 that says: This agreement may be terminated by either party upon thirty days written notice.`

## Important Limits

- PDF behavior is the same general workflow as V3.
- The DOCX workflow supports `.docx`, not legacy `.doc`.
- Sentence-level DOCX edits may flatten inline formatting inside the changed paragraph.
- New DOCX paragraphs inherit nearby paragraph style, but complex structures are not preserved perfectly.
- Tables, headers, footers, comments, tracked changes, text boxes, and heavily formatted inline content are not the first target.
- Always review the transcript before applying a DOCX edit if exact wording matters.
- Always review AI-filled PDF values, email drafts, and saved DOCX output before using them.

## Gmail Draft Setup

Gmail draft creation uses Google OAuth and is separate from your Gemini API key.

1. Create a Google Cloud OAuth client for a Desktop app.
2. Enable the Gmail API for that Google Cloud project.
3. Download the OAuth client JSON.
4. Rename it to `gmail-credentials.json`.
5. Place it in this V6 app folder.
6. Click `Connect Gmail` in the app and approve Gmail compose access.

Click `Gmail Setup Help` in the app to open the detailed setup steps in a separate window.

## Windows Setup

From this folder, run:

```bat
install_windows_v6.bat
launch_windows_v6.bat
```

Use `windows_launch_v6.pyw` for normal no-console launching after setup.

The default Gemini model is `gemini-flash-latest`, but you can edit the model field in the app if Google changes model access for your account.
