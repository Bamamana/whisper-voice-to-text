#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import shutil
import tempfile
import threading
import wave
import webbrowser
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import quote
from tkinter import filedialog, messagebox, simpledialog, ttk
import tkinter as tk

import fitz
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from google import genai
from google.genai import types
from pypdf import PdfReader, PdfWriter
from pypdf.generic import BooleanObject, NameObject


DEFAULT_GEMINI_MODEL = "gemini-flash-latest"
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]
MATTER_PROFILE_FILENAME = ".whisper-v4-profile.json"


class GeminiFormFillerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Whisper Voice To Form - V4 Legal Assistant")
        self.root.geometry("1320x820")

        self.app_dir = Path(__file__).resolve().parent
        self.api_key_file = self.app_dir / ".gemini-api-key"
        self.gmail_credentials_file = self.app_dir / "gmail-credentials.json"
        self.gmail_token_file = self.app_dir / ".gmail-token.json"
        self.model_cache_dir = self.app_dir / "model-cache"
        self.templates_dir = self.app_dir / "templates"
        self.matter_profiles_dir = self.app_dir / "matter-profiles"
        self.model_cache_dir.mkdir(exist_ok=True)
        self.templates_dir.mkdir(exist_ok=True)
        self.matter_profiles_dir.mkdir(exist_ok=True)

        self.pdf_path: Path | None = None
        self.pdf_document: fitz.Document | None = None
        self.pdf_fields: dict[str, dict] = {}
        self.pdf_field_locations: dict[str, list[tuple[int, fitz.Rect]]] = {}
        self.pdf_widget_values: dict[str, str] = {}
        self.field_values: dict[str, str] = {}
        self.current_page_index = 0
        self.preview_zoom = 1.25
        self.preview_image: tk.PhotoImage | None = None
        self.preview_editor: ttk.Entry | None = None
        self.preview_editor_window: int | None = None
        self.preview_editor_field: str | None = None
        self.recording = False
        self.record_stream = None
        self.recorded_chunks: list[np.ndarray] = []
        self.sample_rate = 16000
        self.whisper_model: WhisperModel | None = None
        self.is_busy = False

        self.api_key_var = tk.StringVar(value=self._load_api_key())
        self.gemini_model_var = tk.StringVar(value=DEFAULT_GEMINI_MODEL)
        self.whisper_model_var = tk.StringVar(value="base")
        self.pdf_status_var = tk.StringVar(value="No PDF loaded")
        self.page_status_var = tk.StringVar(value="No page loaded")
        self.recording_status_var = tk.StringVar(value="Mic idle")
        self.status_var = tk.StringVar(value="Ready")
        self.template_var = tk.StringVar(value="")
        self.email_to_var = tk.StringVar(value="")
        self.email_cc_var = tk.StringVar(value="")
        self.email_bcc_var = tk.StringVar(value="")
        self.email_subject_var = tk.StringVar(value="")
        self.matter_profile_var = tk.StringVar(value="")
        self.client_name_var = tk.StringVar(value="")
        self.matter_number_var = tk.StringVar(value="")
        self.court_var = tk.StringVar(value="")
        self.opposing_party_var = tk.StringVar(value="")
        self.dropbox_parent_path_var = tk.StringVar(value="")
        self.file_group_path_var = tk.StringVar(value="")
        self.accessibility_mode_var = tk.BooleanVar(value=False)
        self.collapsed_panels: set[str] = set()
        self.panel_button_vars = {
            "matter": tk.StringVar(value="[v] Matter"),
            "legal": tk.StringVar(value="[v] Legal Tools"),
            "email": tk.StringVar(value="[v] Email"),
            "fields": tk.StringVar(value="[v] PDF Fields"),
        }

        self._build_ui()
        self._bind_accessibility_shortcuts()
        self.refresh_template_choices()
        self.refresh_matter_profiles()

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        settings = ttk.LabelFrame(main, text="AI Settings", padding=10)
        settings.pack(fill=tk.X)

        ttk.Label(settings, text="Google AI Studio API key").grid(row=0, column=0, sticky="w")
        api_entry = ttk.Entry(settings, textvariable=self.api_key_var, show="*", width=58)
        api_entry.grid(row=0, column=1, sticky="ew", padx=(8, 6))
        ttk.Button(settings, text="Save Key", command=self.save_api_key).grid(row=0, column=2)
        ttk.Button(settings, text="Test Key", command=self.test_api_key).grid(row=0, column=3, padx=(6, 0))
        ttk.Checkbutton(settings, text="Large Controls", variable=self.accessibility_mode_var, command=self.toggle_accessibility_mode).grid(row=0, column=4, padx=(10, 0))

        ttk.Label(settings, text="Gemini model").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(settings, textvariable=self.gemini_model_var, width=28).grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))
        ttk.Label(settings, text="Whisper model").grid(row=1, column=1, sticky="e", padx=(0, 130), pady=(8, 0))
        ttk.Combobox(
            settings,
            textvariable=self.whisper_model_var,
            values=["tiny", "base", "small", "medium", "large-v3"],
            width=12,
            state="readonly",
        ).grid(row=1, column=2, sticky="w", pady=(8, 0))
        settings.columnconfigure(1, weight=1)

        actions = ttk.Frame(main)
        actions.pack(fill=tk.X, pady=(10, 8))

        ttk.Button(actions, text="Upload Fillable PDF", command=self.load_pdf).pack(side=tk.LEFT)
        ttk.Button(actions, text="Auto-Prepare Flat PDF", command=self.auto_prepare_flat_pdf).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(actions, text="Review Fields With Gemini", command=self.review_fields_with_gemini).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(actions, text="Save As Template", command=self.save_current_as_template).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(actions, text="Template:").pack(side=tk.LEFT, padx=(12, 4))
        self.template_combo = ttk.Combobox(actions, textvariable=self.template_var, width=24, state="readonly")
        self.template_combo.pack(side=tk.LEFT)
        ttk.Button(actions, text="Load Template", command=self.load_selected_template).pack(side=tk.LEFT, padx=(6, 0))

        recording_actions = ttk.Frame(main)
        recording_actions.pack(fill=tk.X, pady=(0, 8))

        ttk.Button(recording_actions, text="Start Recording", command=self.start_recording).pack(side=tk.LEFT)
        ttk.Button(recording_actions, text="Stop and Transcribe", command=self.stop_recording).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(recording_actions, text="Fix Grammar / Whisper Text", command=lambda: self.rewrite_transcript_with_gemini("grammar")).pack(side=tk.LEFT, padx=(16, 0))
        ttk.Button(recording_actions, text="Formal Legal Tone", command=lambda: self.create_legal_work_product("formal_tone")).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(recording_actions, text="Make Email", command=lambda: self.rewrite_transcript_with_gemini("email")).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(recording_actions, text="Shortcut Help", command=self.show_command_help).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(recording_actions, text="Send Transcript To PDF", command=self.send_transcript_to_ai).pack(side=tk.LEFT, padx=(16, 0))
        ttk.Button(recording_actions, text="Export Filled PDF", command=self.export_filled_pdf).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(recording_actions, text="Update Original PDF", command=self.update_original_pdf).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(main, textvariable=self.pdf_status_var).pack(anchor="w")
        ttk.Label(main, textvariable=self.recording_status_var).pack(anchor="w", pady=(2, 8))

        workspace = ttk.PanedWindow(main, orient=tk.HORIZONTAL)
        workspace.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        left_column = ttk.PanedWindow(workspace, orient=tk.VERTICAL)
        self.left_column = left_column
        preview = ttk.LabelFrame(workspace, text="PDF Preview", padding=8)
        workspace.add(left_column, weight=1)
        workspace.add(preview, weight=2)

        transcript_panel = ttk.Frame(left_column, padding=(0, 0, 8, 4))
        matter_panel = ttk.LabelFrame(left_column, text="Client / Matter Profile", padding=(0, 4, 8, 4))
        legal_panel = ttk.LabelFrame(left_column, text="Legal Work Product", padding=(0, 4, 8, 4))
        email_panel = ttk.LabelFrame(left_column, text="Email Draft", padding=(0, 4, 8, 4))
        fields_panel = ttk.Frame(left_column, padding=(0, 4, 8, 0))
        left_column.add(transcript_panel, weight=1)
        left_column.add(matter_panel, weight=0)
        left_column.add(legal_panel, weight=1)
        left_column.add(email_panel, weight=1)
        left_column.add(fields_panel, weight=1)

        transcript_header = ttk.Frame(transcript_panel)
        transcript_header.pack(fill=tk.X)
        ttk.Label(transcript_header, text="Transcript").pack(side=tk.LEFT)
        ttk.Button(transcript_header, text="Copy", command=self.copy_transcript).pack(side=tk.LEFT, padx=(8, 0))

        panel_toggles = ttk.Frame(transcript_panel)
        panel_toggles.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(panel_toggles, textvariable=self.panel_button_vars["matter"], command=lambda: self.toggle_panel("matter")).pack(side=tk.LEFT)
        ttk.Button(panel_toggles, textvariable=self.panel_button_vars["legal"], command=lambda: self.toggle_panel("legal")).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(panel_toggles, textvariable=self.panel_button_vars["email"], command=lambda: self.toggle_panel("email")).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(panel_toggles, textvariable=self.panel_button_vars["fields"], command=lambda: self.toggle_panel("fields")).pack(side=tk.LEFT, padx=(6, 0))

        self.transcript_text = tk.Text(transcript_panel, wrap=tk.WORD, height=12)
        self.transcript_text.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        self.collapsible_panes = {
            "matter": (matter_panel, 0),
            "legal": (legal_panel, 1),
            "email": (email_panel, 1),
            "fields": (fields_panel, 1),
        }

        matter_fields = ttk.Frame(matter_panel)
        matter_fields.pack(fill=tk.X)
        ttk.Label(matter_fields, text="Client").grid(row=0, column=0, sticky="w")
        ttk.Entry(matter_fields, textvariable=self.client_name_var).grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ttk.Label(matter_fields, text="Matter #").grid(row=0, column=2, sticky="w", padx=(8, 0))
        ttk.Entry(matter_fields, textvariable=self.matter_number_var, width=18).grid(row=0, column=3, sticky="ew", padx=(6, 0))
        ttk.Label(matter_fields, text="Court").grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Entry(matter_fields, textvariable=self.court_var).grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=(4, 0))
        ttk.Label(matter_fields, text="Opposing").grid(row=1, column=2, sticky="w", padx=(8, 0), pady=(4, 0))
        ttk.Entry(matter_fields, textvariable=self.opposing_party_var, width=18).grid(row=1, column=3, sticky="ew", padx=(6, 0), pady=(4, 0))
        ttk.Label(matter_fields, text="Saved").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.matter_profile_combo = ttk.Combobox(matter_fields, textvariable=self.matter_profile_var, state="readonly")
        self.matter_profile_combo.grid(row=2, column=1, sticky="ew", padx=(6, 0), pady=(6, 0))
        ttk.Button(matter_fields, text="Load", command=self.load_selected_matter_profile).grid(row=2, column=2, sticky="ew", padx=(8, 0), pady=(6, 0))
        profile_buttons = ttk.Frame(matter_fields)
        profile_buttons.grid(row=2, column=3, sticky="ew", padx=(6, 0), pady=(6, 0))
        ttk.Button(profile_buttons, text="Extract From Transcript", command=self.extract_matter_profile_from_transcript).pack(side=tk.LEFT)
        ttk.Button(profile_buttons, text="Save Profile", command=self.save_current_matter_profile).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Label(matter_fields, text="Dropbox Parent").grid(row=3, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(matter_fields, textvariable=self.dropbox_parent_path_var).grid(row=3, column=1, sticky="ew", padx=(6, 0), pady=(6, 0))
        ttk.Button(matter_fields, text="Choose Parent", command=self.select_dropbox_parent_folder).grid(row=3, column=2, sticky="ew", padx=(8, 0), pady=(6, 0))
        ttk.Button(matter_fields, text="Refresh", command=self.refresh_dropbox_matter_folders).grid(row=3, column=3, sticky="w", padx=(6, 0), pady=(6, 0))
        ttk.Label(matter_fields, text="Matter Folder").grid(row=4, column=0, sticky="w", pady=(6, 0))
        self.dropbox_folder_combo = ttk.Combobox(matter_fields, state="readonly")
        self.dropbox_folder_combo.grid(row=4, column=1, sticky="ew", padx=(6, 0), pady=(6, 0))
        self.dropbox_folder_combo.bind("<<ComboboxSelected>>", lambda _event: self.load_selected_dropbox_matter_folder())
        ttk.Button(matter_fields, text="Load Folder", command=self.load_selected_dropbox_matter_folder).grid(row=4, column=2, sticky="ew", padx=(8, 0), pady=(6, 0))
        ttk.Button(matter_fields, text="Open Selected", command=self.open_selected_matter_file).grid(row=4, column=3, sticky="w", padx=(6, 0), pady=(6, 0))
        ttk.Label(matter_fields, text="File Folder").grid(row=5, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(matter_fields, textvariable=self.file_group_path_var).grid(row=5, column=1, sticky="ew", padx=(6, 0), pady=(6, 0))
        ttk.Button(matter_fields, text="Choose Folder", command=self.select_matter_file_group).grid(row=5, column=2, sticky="ew", padx=(8, 0), pady=(6, 0))
        file_list_frame = ttk.Frame(matter_fields)
        file_list_frame.grid(row=6, column=0, columnspan=4, sticky="nsew", pady=(4, 0))
        self.matter_files_listbox = tk.Listbox(file_list_frame, height=4)
        matter_files_scrollbar = ttk.Scrollbar(file_list_frame, orient=tk.VERTICAL, command=self.matter_files_listbox.yview)
        self.matter_files_listbox.configure(yscrollcommand=matter_files_scrollbar.set)
        self.matter_files_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        matter_files_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.matter_files_listbox.bind("<Double-1>", lambda _event: self.open_selected_matter_file())
        matter_fields.columnconfigure(1, weight=1)
        matter_fields.columnconfigure(3, weight=1)

        legal_buttons = ttk.Frame(legal_panel)
        legal_buttons.pack(fill=tk.X)
        ttk.Button(legal_buttons, text="Attorney Notes", command=lambda: self.create_legal_work_product("attorney_notes")).pack(side=tk.LEFT)
        ttk.Button(legal_buttons, text="Billing Entry", command=lambda: self.create_legal_work_product("billing_entry")).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(legal_buttons, text="Timeline", command=lambda: self.create_legal_work_product("timeline")).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(legal_buttons, text="Client Letter", command=lambda: self.create_legal_work_product("client_letter")).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(legal_buttons, text="Checklist", command=lambda: self.create_legal_work_product("checklist")).pack(side=tk.LEFT, padx=(6, 0))
        self.legal_output_text = tk.Text(legal_panel, wrap=tk.WORD, height=8)
        self.legal_output_text.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        email_fields = ttk.Frame(email_panel)
        email_fields.pack(fill=tk.X)
        ttk.Label(email_fields, text="To").grid(row=0, column=0, sticky="w")
        ttk.Entry(email_fields, textvariable=self.email_to_var).grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ttk.Label(email_fields, text="CC").grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Entry(email_fields, textvariable=self.email_cc_var).grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=(4, 0))
        ttk.Label(email_fields, text="BCC").grid(row=2, column=0, sticky="w", pady=(4, 0))
        ttk.Entry(email_fields, textvariable=self.email_bcc_var).grid(row=2, column=1, sticky="ew", padx=(6, 0), pady=(4, 0))
        ttk.Label(email_fields, text="Subject").grid(row=3, column=0, sticky="w", pady=(4, 0))
        ttk.Entry(email_fields, textvariable=self.email_subject_var).grid(row=3, column=1, sticky="ew", padx=(6, 0), pady=(4, 0))
        email_fields.columnconfigure(1, weight=1)

        self.email_body_text = tk.Text(email_panel, wrap=tk.WORD, height=6)
        self.email_body_text.pack(fill=tk.BOTH, expand=True, pady=(6, 4))
        email_buttons = ttk.Frame(email_panel)
        email_buttons.pack(fill=tk.X)
        ttk.Button(email_buttons, text="Connect Gmail", command=self.connect_gmail).pack(side=tk.LEFT)
        ttk.Button(email_buttons, text="Create Gmail Draft", command=self.create_gmail_draft).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(email_buttons, text="Open Email App", command=self.open_email_app).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(email_buttons, text="Gmail Setup Help", command=self.show_gmail_setup_help).pack(side=tk.LEFT, padx=(6, 0))

        ttk.Label(fields_panel, text="PDF Fields and AI Values").pack(anchor="w")
        self.fields_tree = ttk.Treeview(fields_panel, columns=("value",), show="tree headings")
        self.fields_tree.heading("#0", text="Field")
        self.fields_tree.heading("value", text="Value")
        self.fields_tree.column("#0", width=220)
        self.fields_tree.column("value", width=320)
        self.fields_tree.pack(fill=tk.BOTH, expand=True)
        self.fields_tree.bind("<Double-1>", self.edit_selected_value)

        preview_toolbar = ttk.Frame(preview)
        preview_toolbar.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(preview_toolbar, text="Previous Page", command=self.previous_page).pack(side=tk.LEFT)
        ttk.Button(preview_toolbar, text="Next Page", command=self.next_page).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Label(preview_toolbar, textvariable=self.page_status_var).pack(side=tk.LEFT, padx=(12, 0))

        preview_body = ttk.Frame(preview)
        preview_body.pack(fill=tk.BOTH, expand=True)
        self.preview_canvas = tk.Canvas(preview_body, background="#f4f4f4")
        preview_y = ttk.Scrollbar(preview_body, orient=tk.VERTICAL, command=self.preview_canvas.yview)
        preview_x = ttk.Scrollbar(preview_body, orient=tk.HORIZONTAL, command=self.preview_canvas.xview)
        self.preview_canvas.configure(yscrollcommand=preview_y.set, xscrollcommand=preview_x.set)
        self.preview_canvas.bind("<MouseWheel>", self._scroll_preview_with_mousewheel)
        self.preview_canvas.bind("<Button-4>", self._scroll_preview_with_mousewheel)
        self.preview_canvas.bind("<Button-5>", self._scroll_preview_with_mousewheel)
        self.preview_canvas.bind("<Button-1>", self.edit_preview_field)
        self.preview_canvas.grid(row=0, column=0, sticky="nsew")
        preview_y.grid(row=0, column=1, sticky="ns")
        preview_x.grid(row=1, column=0, sticky="ew")
        preview_body.columnconfigure(0, weight=1)
        preview_body.rowconfigure(0, weight=1)

        ttk.Label(main, textvariable=self.status_var).pack(anchor="w", pady=(8, 0))

    def _load_api_key(self) -> str:
        if self.api_key_file.exists():
            return self.api_key_file.read_text(encoding="utf-8").strip()
        return ""

    def _bind_accessibility_shortcuts(self) -> None:
        shortcuts = {
            "<F5>": lambda _event: self.start_recording(),
            "<F6>": lambda _event: self.stop_recording(),
            "<F7>": lambda _event: self.rewrite_transcript_with_gemini("email"),
            "<F8>": lambda _event: self.send_transcript_to_ai(),
            "<F9>": lambda _event: self.export_filled_pdf(),
            "<F10>": lambda _event: self.update_original_pdf(),
            "<Control-l>": lambda _event: self._toggle_large_controls_shortcut(),
            "<Control-m>": lambda _event: self._focus_transcript(),
            "<Control-h>": lambda _event: self.show_command_help(),
            "<Alt-Left>": lambda _event: self.previous_page(),
            "<Alt-Right>": lambda _event: self.next_page(),
        }
        for sequence, command in shortcuts.items():
            self.root.bind(sequence, command)

    def _toggle_large_controls_shortcut(self) -> None:
        self.accessibility_mode_var.set(not self.accessibility_mode_var.get())
        self.toggle_accessibility_mode()

    def _focus_transcript(self) -> None:
        self.transcript_text.focus_set()
        self.status_var.set("Transcript box focused")

    def copy_transcript(self) -> None:
        transcript = self.transcript_text.get("1.0", tk.END).strip()
        if not transcript:
            messagebox.showerror("Nothing to copy", "The transcript box is empty.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(transcript)
        self.status_var.set("Transcript copied to clipboard")

    def toggle_panel(self, panel_name: str) -> None:
        if panel_name in self.collapsed_panels:
            self.collapsed_panels.remove(panel_name)
        else:
            self.collapsed_panels.add(panel_name)
        self._refresh_collapsible_panels()

    def _refresh_collapsible_panels(self) -> None:
        panel_labels = {
            "matter": ("[>] Matter", "[v] Matter"),
            "legal": ("[>] Legal Tools", "[v] Legal Tools"),
            "email": ("[>] Email", "[v] Email"),
            "fields": ("[>] PDF Fields", "[v] PDF Fields"),
        }

        for panel_name, (show_label, hide_label) in panel_labels.items():
            self.panel_button_vars[panel_name].set(show_label if panel_name in self.collapsed_panels else hide_label)

        for pane, _weight in self.collapsible_panes.values():
            try:
                self.left_column.forget(pane)
            except tk.TclError:
                pass

        for panel_name in ("matter", "legal", "email", "fields"):
            if panel_name in self.collapsed_panels:
                continue
            pane, weight = self.collapsible_panes[panel_name]
            self.left_column.add(pane, weight=weight)

        hidden_count = len(self.collapsed_panels)
        self.status_var.set(f"{hidden_count} panel{'s' if hidden_count != 1 else ''} collapsed")

    def select_matter_file_group(self) -> None:
        folder = filedialog.askdirectory(title="Choose matter file folder")
        if not folder:
            return
        self.file_group_path_var.set(folder)
        self.apply_profile_from_folder(Path(folder))
        self.refresh_matter_files()
        self.status_var.set(f"Matter file folder selected: {folder}")

    def select_dropbox_parent_folder(self) -> None:
        folder = filedialog.askdirectory(title="Choose parent Dropbox/client folder")
        if not folder:
            return
        self.dropbox_parent_path_var.set(folder)
        self.refresh_dropbox_matter_folders()
        self.status_var.set(f"Dropbox parent selected: {folder}")

    def refresh_dropbox_matter_folders(self) -> None:
        if not hasattr(self, "dropbox_folder_combo"):
            return
        parent_text = self.dropbox_parent_path_var.get().strip()
        if not parent_text:
            self.dropbox_folder_combo.configure(values=[])
            return
        parent = Path(parent_text)
        if not parent.exists() or not parent.is_dir():
            messagebox.showerror("Missing parent folder", "Choose an existing Dropbox parent folder first.")
            return

        folders = []
        for path in sorted(parent.iterdir(), key=lambda item: item.name.lower()):
            if path.is_dir() and not path.name.startswith("."):
                folders.append(path.name)

        self.dropbox_folder_combo.configure(values=folders)
        if folders:
            self.dropbox_folder_combo.set(folders[0])
        else:
            self.dropbox_folder_combo.set("")
        self.status_var.set(f"Found {len(folders)} matter folder{'s' if len(folders) != 1 else ''}")

    def load_selected_dropbox_matter_folder(self) -> None:
        parent_text = self.dropbox_parent_path_var.get().strip()
        folder_name = self.dropbox_folder_combo.get().strip() if hasattr(self, "dropbox_folder_combo") else ""
        if not parent_text or not folder_name:
            messagebox.showerror("Missing folder", "Choose a Dropbox parent folder and a matter folder first.")
            return

        folder = Path(parent_text) / folder_name
        if not folder.exists() or not folder.is_dir():
            messagebox.showerror("Missing folder", f"This matter folder was not found:\n{folder}")
            self.refresh_dropbox_matter_folders()
            return

        self.load_matter_folder(folder)

    def load_matter_folder(self, folder: Path) -> None:
        self.file_group_path_var.set(str(folder))
        saved_profile = self.load_profile_from_matter_folder(folder)
        if saved_profile:
            self._apply_matter_profile(saved_profile)
            self.file_group_path_var.set(str(folder))
            self.status_var.set(f"Loaded Dropbox profile from: {folder.name}")
        else:
            self._apply_matter_profile(self.infer_profile_from_folder(folder), preserve_existing=False)
            self.file_group_path_var.set(str(folder))
            self.status_var.set(f"Loaded matter folder and inferred profile: {folder.name}")
        self.refresh_matter_files()

    def load_profile_from_matter_folder(self, folder: Path) -> dict | None:
        profile_path = folder / MATTER_PROFILE_FILENAME
        if not profile_path.exists():
            return None
        try:
            data = json.loads(profile_path.read_text(encoding="utf-8"))
        except Exception as exc:
            messagebox.showwarning("Profile read failed", f"Could not read Dropbox profile file:\n{profile_path}\n\n{exc}")
            return None
        return data if isinstance(data, dict) else None

    def save_profile_to_matter_folder(self) -> Path:
        folder_text = self.file_group_path_var.get().strip()
        if not folder_text:
            raise RuntimeError("Choose or load a Dropbox matter folder before saving the profile.")
        folder = Path(folder_text)
        if not folder.exists() or not folder.is_dir():
            raise RuntimeError(f"The active matter folder does not exist:\n{folder}")

        data = self._current_matter_profile()
        data["file_group_path"] = str(folder)
        if not data.get("dropbox_parent_path") and folder.parent.exists():
            data["dropbox_parent_path"] = str(folder.parent)
        profile_path = folder / MATTER_PROFILE_FILENAME
        profile_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return profile_path

    def apply_profile_from_folder(self, folder: Path) -> None:
        profile = self.infer_profile_from_folder(folder)
        self._apply_matter_profile(profile, preserve_existing=True)

    def infer_profile_from_folder(self, folder: Path) -> dict[str, str]:
        name = folder.name.strip()
        parts = [part.strip(" -_") for part in name.replace("_", " ").split(" - ") if part.strip(" -_")]
        matter_number = ""
        client_name = ""
        opposing_party = ""
        court = ""

        for part in parts:
            lowered = part.lower()
            if not matter_number and any(char.isdigit() for char in part) and any(token in lowered for token in ("matter", "case", "#")):
                matter_number = part.replace("Matter", "").replace("matter", "").replace("Case", "").replace("case", "").replace("#", "").strip(" -_:")
            elif not court and "court" in lowered:
                court = part
            elif not opposing_party and lowered.startswith(("v ", "vs ", "versus ")):
                opposing_party = part.split(" ", 1)[-1].strip()
            elif not client_name:
                client_name = part

        if not client_name:
            cleaned = name.replace("_", " ")
            for separator in (" - ", "_", "|"):
                if separator in cleaned:
                    cleaned = cleaned.split(separator, 1)[0]
                    break
            client_name = cleaned.strip(" -_")

        return {
            "client_name": client_name,
            "matter_number": matter_number,
            "court": court,
            "opposing_party": opposing_party,
        }

    def refresh_matter_files(self) -> None:
        if not hasattr(self, "matter_files_listbox"):
            return
        self.matter_files_listbox.delete(0, tk.END)
        folder_text = self.file_group_path_var.get().strip()
        if not folder_text:
            return
        folder = Path(folder_text)
        if not folder.exists() or not folder.is_dir():
            return

        allowed_suffixes = {".doc", ".docx", ".pdf", ".txt", ".rtf", ".xlsx", ".xls", ".csv"}
        for path in sorted(folder.iterdir(), key=lambda item: item.name.lower()):
            if path.is_file() and path.suffix.lower() in allowed_suffixes:
                self.matter_files_listbox.insert(tk.END, path.name)

    def open_selected_matter_file(self) -> None:
        folder_text = self.file_group_path_var.get().strip()
        if not folder_text:
            messagebox.showerror("Missing folder", "Choose a matter file folder first.")
            return
        selected = self.matter_files_listbox.curselection() if hasattr(self, "matter_files_listbox") else ()
        if not selected:
            messagebox.showerror("No file selected", "Select a document from the matter file list first.")
            return

        file_path = Path(folder_text) / self.matter_files_listbox.get(selected[0])
        if not file_path.exists():
            messagebox.showerror("Missing file", f"This file no longer exists:\n{file_path}")
            self.refresh_matter_files()
            return
        if file_path.suffix.lower() == ".pdf":
            self.open_pdf_from_matter_folder(file_path)
            return
        try:
            os.startfile(file_path)
            self.status_var.set(f"Opened matter file: {file_path.name}")
        except Exception as exc:
            messagebox.showerror("Open file failed", str(exc))

    def open_pdf_from_matter_folder(self, file_path: Path) -> None:
        try:
            reader = PdfReader(str(file_path))
            fields = reader.get_fields() or {}
        except Exception as exc:
            messagebox.showerror("PDF error", str(exc))
            return

        if fields:
            self.load_pdf(file_path)
            self.status_var.set(f"Loaded matter PDF in V4: {file_path.name}")
            return

        should_prepare = messagebox.askyesno(
            "Flat PDF selected",
            "This PDF does not have fillable fields yet.\n\nDo you want V4 to auto-prepare a reusable fillable template from it?",
        )
        if not should_prepare:
            self.status_var.set(f"Selected flat PDF was not loaded: {file_path.name}")
            return

        output_path = self.templates_dir / f"{file_path.stem}-auto-template.pdf"
        try:
            field_count = self._create_fillable_template_from_flat_pdf(file_path, output_path)
        except Exception as exc:
            messagebox.showerror("Auto-prepare failed", str(exc))
            return

        if field_count == 0:
            messagebox.showwarning(
                "No fields detected",
                "No obvious blank lines or checkbox squares were detected. This PDF may need manual preparation in Adobe Acrobat.",
            )
            return

        self.refresh_template_choices()
        self.template_var.set(output_path.name)
        self.load_pdf(output_path)
        self.status_var.set(f"Auto-prepared and loaded matter PDF: {output_path.name}")

    def _scroll_preview_with_mousewheel(self, event) -> str:
        self.commit_preview_editor()
        if getattr(event, "num", None) == 4 or getattr(event, "delta", 0) > 0:
            self.preview_canvas.yview_scroll(-3, "units")
        else:
            self.preview_canvas.yview_scroll(3, "units")
        return "break"

    def edit_preview_field(self, event) -> str:
        field_name = self._field_at_preview_position(event.x, event.y)
        if field_name:
            self.start_inline_preview_edit(field_name)
        else:
            self.commit_preview_editor()
        return "break"

    def _field_at_preview_position(self, canvas_x: int, canvas_y: int) -> str | None:
        page_x = self.preview_canvas.canvasx(canvas_x) / self.preview_zoom
        page_y = self.preview_canvas.canvasy(canvas_y) / self.preview_zoom

        for field_name, locations in self.pdf_field_locations.items():
            for page_index, rect in locations:
                if page_index == self.current_page_index and rect.contains(fitz.Point(page_x, page_y)):
                    return field_name
        return None

    def save_api_key(self) -> None:
        self.api_key_file.write_text(self.api_key_var.get().strip(), encoding="utf-8")
        self.status_var.set("API key saved locally")

    def test_api_key(self) -> None:
        if self.is_busy:
            return
        if not self.api_key_var.get().strip():
            messagebox.showerror("Missing API key", "Enter your Google AI Studio API key first.")
            return

        self.is_busy = True
        model_name = self.gemini_model_var.get().strip() or DEFAULT_GEMINI_MODEL
        self.status_var.set(f"Testing Gemini API key with {model_name}")
        threading.Thread(target=self._test_api_key_worker, args=(model_name,), daemon=True).start()

    def _test_api_key_worker(self, model_name: str) -> None:
        try:
            client = genai.Client(api_key=self.api_key_var.get().strip())
            response = client.models.generate_content(
                model=model_name,
                contents="Reply with only: OK",
            )
            reply = (response.text or "").strip()
            if "OK" not in reply.upper():
                raise RuntimeError(f"Gemini responded, but with unexpected text: {reply}")
            self.root.after(0, self._test_api_key_done, model_name)
        except Exception as exc:
            self.root.after(0, self._task_failed, "API key test failed", str(exc))

    def _test_api_key_done(self, model_name: str) -> None:
        self.is_busy = False
        self.status_var.set(f"API key works with {model_name}")
        messagebox.showinfo("API key works", f"Gemini responded successfully using:\n{model_name}")

    def load_pdf(self, path: str | Path | None = None) -> None:
        if path is None:
            path = filedialog.askopenfilename(title="Choose a fillable PDF", filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        path = str(path)

        try:
            reader = PdfReader(path)
            fields = reader.get_fields() or {}
        except Exception as exc:
            messagebox.showerror("PDF error", str(exc))
            return

        if not fields:
            messagebox.showerror(
                "No fillable fields found",
                "This PDF does not appear to contain fillable form fields. Use Adobe Acrobat Pro > Prepare Form first.",
            )
            return

        self.pdf_path = Path(path)
        if self.pdf_document is not None:
            self.pdf_document.close()
        self.pdf_document = fitz.open(path)
        self.pdf_fields = fields
        self.pdf_widget_values = {}
        self.pdf_field_locations = self._read_pdf_field_locations()
        for field_name in self.pdf_field_locations:
            self.pdf_fields.setdefault(field_name, {})
        self.field_values = {field_name: self._initial_pdf_field_value(field_name, details) for field_name, details in self.pdf_fields.items()}
        self.current_page_index = 0
        self.pdf_status_var.set(f"Loaded PDF: {self.pdf_path.name} ({len(fields)} fields)")
        self.refresh_fields_tree()
        self.render_current_page()

    def refresh_template_choices(self) -> None:
        templates = sorted(path.name for path in self.templates_dir.glob("*.pdf"))
        if hasattr(self, "template_combo"):
            self.template_combo.configure(values=templates)
        if templates and self.template_var.get() not in templates:
            self.template_var.set(templates[0])
        elif not templates:
            self.template_var.set("")

    def refresh_matter_profiles(self) -> None:
        profiles = sorted(path.name for path in self.matter_profiles_dir.glob("*.json"))
        if hasattr(self, "matter_profile_combo"):
            self.matter_profile_combo.configure(values=profiles)
        if profiles and self.matter_profile_var.get() not in profiles:
            self.matter_profile_var.set(profiles[0])
        elif not profiles:
            self.matter_profile_var.set("")

    def load_selected_matter_profile(self) -> None:
        folder_text = self.file_group_path_var.get().strip()
        if folder_text:
            folder = Path(folder_text)
            if folder.exists() and folder.is_dir():
                profile = self.load_profile_from_matter_folder(folder)
                if profile:
                    self._apply_matter_profile(profile)
                    self.file_group_path_var.set(str(folder))
                    self.refresh_matter_files()
                    self.status_var.set(f"Loaded Dropbox folder profile: {folder.name}")
                    return

        profile_name = self.matter_profile_var.get()
        if not profile_name:
            messagebox.showerror("No profile", "No Dropbox profile exists in the active matter folder, and no local saved profile is selected.")
            return
        try:
            data = json.loads((self.matter_profiles_dir / profile_name).read_text(encoding="utf-8"))
        except Exception as exc:
            messagebox.showerror("Profile load failed", str(exc))
            return

        self._apply_matter_profile(data)
        self.refresh_matter_files()
        self.status_var.set(f"Matter profile loaded: {profile_name}")

    def save_current_matter_profile(self) -> None:
        data = self._current_matter_profile()
        if not any(data.values()):
            messagebox.showerror("Empty profile", "Enter or extract at least one client/matter detail before saving.")
            return

        folder_text = self.file_group_path_var.get().strip()
        if folder_text:
            try:
                profile_path = self.save_profile_to_matter_folder()
            except Exception as exc:
                messagebox.showerror("Dropbox profile save failed", str(exc))
                return
            self.status_var.set(f"Matter profile saved in Dropbox folder: {profile_path.name}")
            return

        default_name = " - ".join(part for part in (data["client_name"], data["matter_number"]) if part) or "matter-profile"
        profile_name = simpledialog.askstring("Save matter profile", "Profile name", initialvalue=default_name)
        if not profile_name:
            return
        safe_name = "".join(char if char.isalnum() or char in "-_ ." else "_" for char in profile_name).strip()
        if not safe_name:
            return
        if not safe_name.lower().endswith(".json"):
            safe_name += ".json"

        output_path = self.matter_profiles_dir / safe_name
        output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.refresh_matter_profiles()
        self.matter_profile_var.set(output_path.name)
        self.status_var.set(f"Matter profile saved: {output_path.name}")

    def extract_matter_profile_from_transcript(self) -> None:
        if self.is_busy:
            return
        if not self.api_key_var.get().strip():
            messagebox.showerror("Missing API key", "Enter your Google AI Studio API key first.")
            return

        transcript = self.transcript_text.get("1.0", tk.END).strip()
        if not transcript:
            messagebox.showerror("Missing transcript", "Record or type a transcript first.")
            return

        self.is_busy = True
        self.status_var.set("Extracting client/matter profile with Gemini")
        threading.Thread(target=self._extract_matter_profile_worker, args=(transcript,), daemon=True).start()

    def _extract_matter_profile_worker(self, transcript: str) -> None:
        try:
            prompt = (
                "Extract client and matter profile details from this legal dictation. "
                "Return strict JSON only with this exact shape: "
                "{\"client_name\":\"\",\"matter_number\":\"\",\"court\":\"\",\"opposing_party\":\"\"}. "
                "Use empty strings for anything not clearly stated. Do not invent details.\n\n"
                f"Transcript:\n{transcript}"
            )
            client = genai.Client(api_key=self.api_key_var.get().strip())
            response = client.models.generate_content(
                model=self.gemini_model_var.get().strip() or DEFAULT_GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            profile = self._parse_json_response(response.text or "")
            self.root.after(0, self._matter_profile_extracted, profile)
        except Exception as exc:
            self.root.after(0, self._task_failed, "Matter profile extraction failed", str(exc))

    def _matter_profile_extracted(self, profile: dict) -> None:
        self.is_busy = False
        self._apply_matter_profile(profile)
        self.status_var.set("Matter profile extracted. Review it, then click Save Profile if you want to reuse it.")

    def _current_matter_profile(self) -> dict[str, str]:
        return {
            "client_name": self.client_name_var.get().strip(),
            "matter_number": self.matter_number_var.get().strip(),
            "court": self.court_var.get().strip(),
            "opposing_party": self.opposing_party_var.get().strip(),
            "dropbox_parent_path": self.dropbox_parent_path_var.get().strip(),
            "file_group_path": self.file_group_path_var.get().strip(),
        }

    def _apply_matter_profile(self, profile: dict, preserve_existing: bool = False) -> None:
        fields = [
            (self.client_name_var, "client_name"),
            (self.matter_number_var, "matter_number"),
            (self.court_var, "court"),
            (self.opposing_party_var, "opposing_party"),
            (self.dropbox_parent_path_var, "dropbox_parent_path"),
            (self.file_group_path_var, "file_group_path"),
        ]
        for variable, key in fields:
            value = str(profile.get(key, "") or "")
            if preserve_existing and variable.get().strip():
                continue
            variable.set(value)
        self.refresh_dropbox_matter_folders()
        self.refresh_matter_files()

    def load_selected_template(self) -> None:
        template_name = self.template_var.get()
        if not template_name:
            messagebox.showerror("No template", "No saved template is selected.")
            return
        self.load_pdf(self.templates_dir / template_name)

    def save_current_as_template(self) -> None:
        if self.pdf_path is None:
            messagebox.showerror("Missing PDF", "Load or auto-prepare a PDF first.")
            return

        template_name = simpledialog.askstring("Save template", "Template file name", initialvalue=self.pdf_path.stem)
        if not template_name:
            return
        safe_name = "".join(char if char.isalnum() or char in "-_ ." else "_" for char in template_name).strip()
        if not safe_name:
            return
        if not safe_name.lower().endswith(".pdf"):
            safe_name += ".pdf"

        output_path = self.templates_dir / safe_name
        if self.pdf_path.resolve() != output_path.resolve():
            shutil.copy2(self.pdf_path, output_path)
        self.refresh_template_choices()
        self.template_var.set(output_path.name)
        self.status_var.set(f"Template saved: {output_path.name}")

    def auto_prepare_flat_pdf(self) -> None:
        source = filedialog.askopenfilename(title="Choose a flat PDF to auto-prepare", filetypes=[("PDF files", "*.pdf")])
        if not source:
            return

        output_name = f"{Path(source).stem}-auto-template.pdf"
        output_path = self.templates_dir / output_name
        try:
            field_count = self._create_fillable_template_from_flat_pdf(Path(source), output_path)
        except Exception as exc:
            messagebox.showerror("Auto-prepare failed", str(exc))
            return

        if field_count == 0:
            messagebox.showwarning(
                "No fields detected",
                "No obvious blank lines or checkbox squares were detected. This form may need manual preparation in Adobe Acrobat.",
            )
            return

        self.refresh_template_choices()
        self.template_var.set(output_path.name)
        self.load_pdf(output_path)
        self.status_var.set(f"Auto-prepared template with {field_count} fields: {output_path.name}")

    def review_fields_with_gemini(self) -> None:
        if self.is_busy:
            return
        if self.pdf_path is None or not self.pdf_fields:
            messagebox.showerror("Missing PDF", "Load or auto-prepare a PDF first.")
            return
        if not self.api_key_var.get().strip():
            messagebox.showerror("Missing API key", "Enter your Google AI Studio API key first.")
            return

        self.commit_preview_editor()
        self.is_busy = True
        self.status_var.set("Sending detected fields to Gemini for review")
        threading.Thread(target=self._gemini_field_review_worker, daemon=True).start()

    def _gemini_field_review_worker(self) -> None:
        try:
            if self.pdf_path is None:
                raise RuntimeError("No PDF is loaded.")

            review_payload, image_parts = self._build_field_review_payload(self.pdf_path)
            prompt = (
                "You are reviewing a PDF form that has been auto-prepared with interactive fields. "
                "Use the page images and the detected field rectangles to improve the field layer. "
                "Return strict JSON only with this shape: "
                "{\"renames\":[{\"old_name\":\"...\",\"new_name\":\"...\",\"label\":\"...\"}],"
                "\"missing_fields\":[{\"page\":1,\"type\":\"text\",\"name\":\"...\",\"bbox\":[x0,y0,x1,y1]}],"
                "\"notes\":[\"...\"]}. "
                "Use snake_case field names. Rename vague fields like page_1_text_3 to meaningful names. "
                "Only suggest missing fields when a clear blank line, empty box, or checkbox exists. "
                "Coordinates must be PDF point coordinates matching the supplied field rectangles. "
                "Do not suggest fields for labels, titles, instructions, or filled static text.\n\n"
                f"Detected fields and page sizes:\n{json.dumps(review_payload, indent=2)}"
            )

            client = genai.Client(api_key=self.api_key_var.get().strip())
            response = client.models.generate_content(
                model=self.gemini_model_var.get().strip() or DEFAULT_GEMINI_MODEL,
                contents=[prompt, *image_parts],
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            review = self._parse_json_response(response.text or "")
            output_path, rename_count, missing_count = self._apply_gemini_field_review(review)
            self.root.after(0, self._gemini_field_review_done, output_path, rename_count, missing_count)
        except Exception as exc:
            self.root.after(0, self._task_failed, "Gemini field review failed", str(exc))

    def _build_field_review_payload(self, pdf_path: Path) -> tuple[dict, list[types.Part]]:
        payload_pages = []
        image_parts: list[types.Part] = []
        doc = fitz.open(pdf_path)
        try:
            for page_index, page in enumerate(doc):
                page_fields = []
                for field_name, locations in self.pdf_field_locations.items():
                    for location_page_index, rect in locations:
                        if location_page_index != page_index:
                            continue
                        field_type = "checkbox" if "checkbox" in field_name.lower() else "text"
                        page_fields.append(
                            {
                                "name": field_name,
                                "type": field_type,
                                "bbox": [round(rect.x0, 2), round(rect.y0, 2), round(rect.x1, 2), round(rect.y1, 2)],
                            }
                        )

                payload_pages.append(
                    {
                        "page": page_index + 1,
                        "width": round(page.rect.width, 2),
                        "height": round(page.rect.height, 2),
                        "text": page.get_text("text")[:4000],
                        "fields": page_fields,
                    }
                )

                pixmap = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
                image_parts.append(types.Part.from_bytes(data=pixmap.tobytes("png"), mime_type="image/png"))
        finally:
            doc.close()

        return {"pages": payload_pages}, image_parts

    def _apply_gemini_field_review(self, review: dict) -> tuple[Path, int, int]:
        if self.pdf_path is None:
            raise RuntimeError("No PDF is loaded.")

        output_path = self.templates_dir / f"{self.pdf_path.stem}-gemini-reviewed.pdf"
        rename_map = self._build_review_rename_map(review.get("renames", []))
        missing_fields = review.get("missing_fields", [])
        doc = fitz.open(self.pdf_path)
        used_names = self._collect_widget_names(doc)
        rename_count = 0
        missing_count = 0

        try:
            for page in doc:
                for widget in page.widgets() or []:
                    new_name = rename_map.get(widget.field_name)
                    if not new_name:
                        continue
                    final_name = self._unique_field_name(new_name, used_names - {widget.field_name})
                    used_names.discard(widget.field_name)
                    used_names.add(final_name)
                    widget.field_name = final_name
                    widget.update()
                    rename_count += 1

            for item in missing_fields if isinstance(missing_fields, list) else []:
                try:
                    page_number = int(item.get("page", 1))
                    page = doc[page_number - 1]
                    bbox = item.get("bbox", [])
                    if len(bbox) != 4:
                        continue
                    rect = fitz.Rect(float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
                    rect = rect & page.rect
                    if rect.width < 6 or rect.height < 6:
                        continue
                    field_type = str(item.get("type", "text")).lower()
                    field_name = self._unique_field_name(self._sanitize_field_name(str(item.get("name", "missing_field"))), used_names)
                    widget = fitz.Widget()
                    widget.rect = rect
                    widget.field_name = field_name
                    widget.field_value = ""
                    widget.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX if field_type == "checkbox" else fitz.PDF_WIDGET_TYPE_TEXT
                    page.add_widget(widget)
                    used_names.add(field_name)
                    missing_count += 1
                except Exception:
                    continue

            doc.save(output_path, deflate=True, garbage=4)
        finally:
            doc.close()

        return output_path, rename_count, missing_count

    def _build_review_rename_map(self, renames) -> dict[str, str]:
        rename_map: dict[str, str] = {}
        if isinstance(renames, dict):
            items = renames.items()
            for old_name, new_value in items:
                new_name = new_value.get("new_name", "") if isinstance(new_value, dict) else str(new_value)
                sanitized = self._sanitize_field_name(new_name)
                if old_name and sanitized:
                    rename_map[str(old_name)] = sanitized
            return rename_map

        if isinstance(renames, list):
            for item in renames:
                if not isinstance(item, dict):
                    continue
                old_name = str(item.get("old_name", ""))
                new_name = self._sanitize_field_name(str(item.get("new_name", "")))
                if old_name and new_name:
                    rename_map[old_name] = new_name
        return rename_map

    def _collect_widget_names(self, doc: fitz.Document) -> set[str]:
        names: set[str] = set()
        for page in doc:
            for widget in page.widgets() or []:
                if widget.field_name:
                    names.add(widget.field_name)
        return names

    def _sanitize_field_name(self, field_name: str) -> str:
        cleaned = "".join(char.lower() if char.isalnum() else "_" for char in field_name.strip())
        cleaned = "_".join(part for part in cleaned.split("_") if part)
        if cleaned and cleaned[0].isdigit():
            cleaned = f"field_{cleaned}"
        return cleaned

    def _unique_field_name(self, field_name: str, used_names: set[str]) -> str:
        base = self._sanitize_field_name(field_name) or "field"
        candidate = base
        suffix = 2
        while candidate in used_names:
            candidate = f"{base}_{suffix}"
            suffix += 1
        return candidate

    def _gemini_field_review_done(self, output_path: Path, rename_count: int, missing_count: int) -> None:
        self.is_busy = False
        self.refresh_template_choices()
        self.template_var.set(output_path.name)
        self.load_pdf(output_path)
        self.status_var.set(f"Gemini review saved: {output_path.name} ({rename_count} renamed, {missing_count} added)")

    def _create_fillable_template_from_flat_pdf(self, source_path: Path, output_path: Path) -> int:
        doc = fitz.open(source_path)
        total_fields = 0
        for page_index, page in enumerate(doc):
            candidates = self._detect_flat_form_fields(page)
            for candidate_index, (field_type, rect) in enumerate(candidates, start=1):
                widget = fitz.Widget()
                widget.rect = rect
                widget.field_name = f"page_{page_index + 1}_{field_type}_{candidate_index}"
                widget.field_value = ""
                if field_type == "checkbox":
                    widget.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
                else:
                    widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
                page.add_widget(widget)
                total_fields += 1

        if total_fields:
            doc.save(output_path, deflate=True, garbage=4)
        doc.close()
        return total_fields

    def _detect_flat_form_fields(self, page: fitz.Page) -> list[tuple[str, fitz.Rect]]:
        candidates: list[tuple[str, fitz.Rect]] = []
        for drawing in page.get_drawings():
            for item in drawing.get("items", []):
                kind = item[0]
                if kind == "l":
                    p1, p2 = item[1], item[2]
                    if abs(p1.y - p2.y) <= 1.5 and abs(p2.x - p1.x) >= 50:
                        x0, x1 = sorted((p1.x, p2.x))
                        y = min(p1.y, page.rect.height - 4)
                        candidates.append(("text", fitz.Rect(x0, max(0, y - 16), x1, min(page.rect.height, y + 4))))
                elif kind == "re":
                    rect = fitz.Rect(item[1])
                    width = rect.width
                    height = rect.height
                    if 7 <= width <= 24 and 7 <= height <= 24 and abs(width - height) <= 6:
                        candidates.append(("checkbox", rect))
                    elif width >= 45 and 8 <= height <= 40:
                        candidates.append(("text", rect))

        return self._deduplicate_detected_fields(candidates)

    def _deduplicate_detected_fields(self, candidates: list[tuple[str, fitz.Rect]]) -> list[tuple[str, fitz.Rect]]:
        deduped: list[tuple[str, fitz.Rect]] = []
        for field_type, rect in candidates:
            if rect.width < 6 or rect.height < 6:
                continue
            if any(field_type == existing_type and rect.intersects(existing_rect) for existing_type, existing_rect in deduped):
                continue
            deduped.append((field_type, rect))
        return deduped

    def _initial_pdf_field_value(self, field_name: str, details: dict) -> str:
        widget_value = self.pdf_widget_values.get(field_name, "")
        if widget_value:
            return widget_value

        value = self._clean_pdf_value(details.get("/V", ""))
        if value:
            return value

        return ""

    def _clean_pdf_value(self, value) -> str:
        if value in (None, ""):
            return ""
        text = str(value)
        if text.startswith("/"):
            text = text[1:]
        return text

    def _read_pdf_field_locations(self) -> dict[str, list[tuple[int, fitz.Rect]]]:
        locations: dict[str, list[tuple[int, fitz.Rect]]] = {}
        if self.pdf_document is None:
            return locations

        for page_index, page in enumerate(self.pdf_document):
            for widget in page.widgets() or []:
                if not widget.field_name:
                    continue
                locations.setdefault(widget.field_name, []).append((page_index, fitz.Rect(widget.rect)))
                widget_value = self._clean_pdf_value(getattr(widget, "field_value", ""))
                if widget_value and not self.pdf_widget_values.get(widget.field_name):
                    self.pdf_widget_values[widget.field_name] = widget_value
        return locations

    def previous_page(self) -> None:
        if self.pdf_document is None or self.current_page_index <= 0:
            return
        self.commit_preview_editor()
        self.current_page_index -= 1
        self.render_current_page()

    def next_page(self) -> None:
        if self.pdf_document is None or self.current_page_index >= self.pdf_document.page_count - 1:
            return
        self.commit_preview_editor()
        self.current_page_index += 1
        self.render_current_page()

    def render_current_page(self) -> None:
        self.clear_preview_editor()
        self.preview_canvas.delete("all")
        if self.pdf_document is None:
            self.page_status_var.set("No page loaded")
            return

        page = self.pdf_document[self.current_page_index]
        matrix = fitz.Matrix(self.preview_zoom, self.preview_zoom)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        self.preview_image = tk.PhotoImage(data=pixmap.tobytes("png"))
        self.preview_canvas.create_image(0, 0, anchor=tk.NW, image=self.preview_image)
        self.preview_canvas.configure(scrollregion=(0, 0, pixmap.width, pixmap.height))
        self.page_status_var.set(f"Page {self.current_page_index + 1} of {self.pdf_document.page_count}")

        for field_name, locations in self.pdf_field_locations.items():
            for page_index, rect in locations:
                if page_index != self.current_page_index:
                    continue
                self._draw_field_overlay(field_name, rect)

    def _draw_field_overlay(self, field_name: str, rect: fitz.Rect) -> None:
        x0 = rect.x0 * self.preview_zoom
        y0 = rect.y0 * self.preview_zoom
        x1 = rect.x1 * self.preview_zoom
        y1 = rect.y1 * self.preview_zoom
        value = self.field_values.get(field_name, "")
        outline = "#2d6cdf" if value else "#c46a00"
        fill = "#eaf2ff" if value else "#fff6e8"
        self.preview_canvas.create_rectangle(x0, y0, x1, y1, outline=outline, width=2)
        if value:
            self.preview_canvas.create_rectangle(x0 + 1, y0 + 1, x1 - 1, y1 - 1, fill=fill, outline="")
            self.preview_canvas.create_text(
                x0 + 4,
                y0 + 3,
                anchor=tk.NW,
                text=value,
                fill="#111111",
                width=max(20, int(x1 - x0 - 8)),
            )

    def start_inline_preview_edit(self, field_name: str) -> None:
        self.commit_preview_editor()
        rect = self._field_rect_on_current_page(field_name)
        if rect is None:
            return

        x0 = rect.x0 * self.preview_zoom
        y0 = rect.y0 * self.preview_zoom
        x1 = rect.x1 * self.preview_zoom
        y1 = rect.y1 * self.preview_zoom
        editor = ttk.Entry(self.preview_canvas)
        editor.insert(0, self.field_values.get(field_name, ""))
        editor.icursor(tk.END)
        editor.bind("<Return>", lambda _event: self.commit_preview_editor())
        editor.bind("<Escape>", lambda _event: self.clear_preview_editor())
        editor.bind("<FocusOut>", lambda _event: self.commit_preview_editor())

        self.preview_editor = editor
        self.preview_editor_field = field_name
        self.preview_editor_window = self.preview_canvas.create_window(
            x0 + 2,
            y0 + 2,
            anchor=tk.NW,
            window=editor,
            width=max(24, int(x1 - x0 - 4)),
            height=max(22, int(y1 - y0 - 4)),
        )
        editor.focus_set()

    def _field_rect_on_current_page(self, field_name: str) -> fitz.Rect | None:
        for page_index, rect in self.pdf_field_locations.get(field_name, []):
            if page_index == self.current_page_index:
                return rect
        return None

    def commit_preview_editor(self) -> str:
        if self.preview_editor is None or self.preview_editor_field is None:
            return "break"

        field_name = self.preview_editor_field
        self.field_values[field_name] = self.preview_editor.get()
        self.clear_preview_editor()
        self.refresh_fields_tree()
        if self.fields_tree.exists(field_name):
            self.fields_tree.selection_set(field_name)
            self.fields_tree.see(field_name)
        self.render_current_page()
        return "break"

    def clear_preview_editor(self) -> str:
        editor = self.preview_editor
        editor_window = self.preview_editor_window
        self.preview_editor = None
        self.preview_editor_window = None
        self.preview_editor_field = None
        if editor_window is not None:
            self.preview_canvas.delete(editor_window)
        if editor is not None:
            editor.destroy()
        return "break"

    def refresh_fields_tree(self) -> None:
        self.fields_tree.delete(*self.fields_tree.get_children())
        for field_name in sorted(self.pdf_fields):
            self.fields_tree.insert("", tk.END, iid=field_name, text=field_name, values=(self.field_values.get(field_name, ""),))

    def edit_selected_value(self, _event=None) -> None:
        selected = self.fields_tree.selection()
        if not selected:
            return
        self.edit_field_value(selected[0])

    def edit_field_value(self, field_name: str) -> None:
        self.commit_preview_editor()
        current_value = self.field_values.get(field_name, "")
        new_value = simpledialog.askstring("Edit field value", field_name, initialvalue=current_value)
        if new_value is None:
            return
        self.field_values[field_name] = new_value
        self.refresh_fields_tree()
        if self.fields_tree.exists(field_name):
            self.fields_tree.selection_set(field_name)
            self.fields_tree.see(field_name)
        self.render_current_page()

    def start_recording(self) -> None:
        if self.recording or self.is_busy:
            return

        self.recorded_chunks = []

        def callback(indata, frames, time_info, status):
            if status:
                self.root.after(0, self.recording_status_var.set, f"Mic warning: {status}")
            self.recorded_chunks.append(indata.copy())

        try:
            self.record_stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                callback=callback,
            )
            self.record_stream.start()
            self.recording = True
            self.recording_status_var.set("Recording... click Stop and Transcribe when done")
            self.status_var.set("Recording")
        except Exception as exc:
            self.recording = False
            self.record_stream = None
            messagebox.showerror("Mic error", str(exc))

    def stop_recording(self) -> None:
        if not self.recording or self.record_stream is None:
            return

        try:
            self.record_stream.stop()
            self.record_stream.close()
        finally:
            self.record_stream = None
            self.recording = False

        if not self.recorded_chunks:
            self.recording_status_var.set("Mic idle")
            messagebox.showerror("No audio", "No microphone audio was captured.")
            return

        audio = np.concatenate(self.recorded_chunks, axis=0)
        temp_wav = tempfile.NamedTemporaryFile(prefix="whisper_form_", suffix=".wav", delete=False)
        temp_wav_path = Path(temp_wav.name)
        temp_wav.close()

        with wave.open(str(temp_wav_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio.tobytes())

        self.is_busy = True
        self.recording_status_var.set("Transcribing recording...")
        self.status_var.set("Loading Whisper and transcribing")
        threading.Thread(target=self._transcribe_worker, args=(temp_wav_path,), daemon=True).start()

    def _transcribe_worker(self, audio_path: Path) -> None:
        try:
            if self.whisper_model is None:
                self.whisper_model = WhisperModel(
                    self.whisper_model_var.get(),
                    device="cpu",
                    compute_type="int8",
                    download_root=str(self.model_cache_dir),
                )
            segments, _ = self.whisper_model.transcribe(str(audio_path), beam_size=5)
            transcript = "\n".join(segment.text.strip() for segment in segments if segment.text).strip()
            self.root.after(0, self._transcription_done, transcript)
        except Exception as exc:
            self.root.after(0, self._task_failed, "Transcription failed", str(exc))

    def _transcription_done(self, transcript: str) -> None:
        self.is_busy = False
        self.transcript_text.delete("1.0", tk.END)
        self.transcript_text.insert("1.0", transcript)
        self.recording_status_var.set("Mic idle")
        self.status_var.set("Transcript ready")

    def toggle_accessibility_mode(self) -> None:
        enabled = self.accessibility_mode_var.get()
        scale = 1.25 if enabled else 1.0
        self.root.tk.call("tk", "scaling", scale)
        style = ttk.Style(self.root)
        if enabled:
            style.configure("TButton", padding=(12, 8))
            style.configure("TEntry", padding=(6, 4))
            self.status_var.set("Large controls enabled")
        else:
            style.configure("TButton", padding=(6, 3))
            style.configure("TEntry", padding=(1, 1))
            self.status_var.set("Large controls disabled")

    def run_voice_command(self) -> None:
        command = self.transcript_text.get("1.0", tk.END).strip().lower()
        if not command:
            messagebox.showerror("Missing command", "Dictate or type a command in the transcript box first.")
            return

        if "clear transcript" in command:
            self.transcript_text.delete("1.0", tk.END)
            self.status_var.set("Transcript cleared")
        elif "make email" in command or "draft email" in command:
            self.rewrite_transcript_with_gemini("email")
        elif "create gmail" in command or "gmail draft" in command:
            self.create_gmail_draft()
        elif "connect gmail" in command:
            self.connect_gmail()
        elif "fill form" in command or "send transcript" in command:
            self.send_transcript_to_ai()
        elif "save pdf" in command or "export pdf" in command:
            self.export_filled_pdf()
        elif "update original" in command or "overwrite pdf" in command:
            self.update_original_pdf()
        elif "attorney notes" in command or "legal notes" in command:
            self.create_legal_work_product("attorney_notes")
        elif "billing" in command or "time entry" in command:
            self.create_legal_work_product("billing_entry")
        elif "timeline" in command or "chronology" in command:
            self.create_legal_work_product("timeline")
        elif "client letter" in command or "letter" in command:
            self.create_legal_work_product("client_letter")
        elif "checklist" in command:
            self.create_legal_work_product("checklist")
        elif "formal" in command or "legal tone" in command:
            self.create_legal_work_product("formal_tone")
        elif "large controls" in command or "accessibility" in command:
            self.accessibility_mode_var.set(not self.accessibility_mode_var.get())
            self.toggle_accessibility_mode()
        else:
            messagebox.showinfo(
                "Command not recognized",
                "Try commands like: make email, fill form, export PDF, attorney notes, billing entry, timeline, client letter, checklist, or large controls.",
            )

    def show_command_help(self) -> None:
        help_window = tk.Toplevel(self.root)
        help_window.title("V4 Shortcut Help")
        help_window.geometry("680x520")

        container = ttk.Frame(help_window, padding=12)
        container.pack(fill=tk.BOTH, expand=True)
        text = tk.Text(container, wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True)

        help_text = """One-Hand Workflow Shortcuts

These are meant to reduce mouse travel and small precise clicks. Voice commands are optional; the main workflow is buttons plus keyboard shortcuts.

Function keys:
F5  Start recording
F6  Stop and transcribe
F7  Make email draft
F8  Send transcript to PDF
F9  Export filled PDF
F10 Update original PDF with backup

Navigation:
Alt + Left   Previous PDF page
Alt + Right  Next PDF page

Comfort shortcuts:
Ctrl + L  Toggle Large Controls
Ctrl + M  Focus the transcript box
Ctrl + H  Open this help window

Suggested one-hand workflow:
1. Press F5 and dictate notes or form answers.
2. Press F6 to transcribe.
3. Use Attorney Notes, Billing Entry, Timeline, Client Letter, Checklist, or Send Transcript To PDF.
4. Review/edit the result before using it.
5. Use Export Filled PDF for a separate copy, or Update Original PDF to update the loaded PDF after V4 creates a backup.

Optional typed commands:
If desired, type a simple command in the transcript box and run the command method from code or future UI. Supported commands include make email, fill form, export PDF, attorney notes, billing entry, timeline, client letter, checklist, and large controls.
"""
        text.insert("1.0", help_text)
        text.configure(state=tk.DISABLED)
        ttk.Button(container, text="Close", command=help_window.destroy).pack(anchor="e", pady=(8, 0))

    def create_legal_work_product(self, mode: str) -> None:
        if self.is_busy:
            return
        if not self.api_key_var.get().strip():
            messagebox.showerror("Missing API key", "Enter your Google AI Studio API key first.")
            return

        transcript = self.transcript_text.get("1.0", tk.END).strip()
        if not transcript:
            messagebox.showerror("Missing transcript", "Record or type a transcript first.")
            return

        self.is_busy = True
        self.status_var.set(f"Creating {self._legal_mode_label(mode)} with Gemini")
        threading.Thread(target=self._legal_work_product_worker, args=(mode, transcript), daemon=True).start()

    def _legal_work_product_worker(self, mode: str, transcript: str) -> None:
        try:
            prompt = self._build_legal_prompt(mode, transcript)
            client = genai.Client(api_key=self.api_key_var.get().strip())
            response = client.models.generate_content(
                model=self.gemini_model_var.get().strip() or DEFAULT_GEMINI_MODEL,
                contents=prompt,
            )
            output = (response.text or "").strip()
            if not output:
                raise RuntimeError("Gemini returned an empty response.")
            self.root.after(0, self._legal_work_product_done, mode, output)
        except Exception as exc:
            self.root.after(0, self._task_failed, "Legal drafting failed", str(exc))

    def _build_legal_prompt(self, mode: str, transcript: str) -> str:
        context = self._client_matter_context()
        base = (
            "You are helping a lawyer turn dictated notes into editable legal work product. "
            "Do not provide legal advice, do not invent facts, and mark uncertain items as TO VERIFY. "
            "Keep the output practical, concise, and ready for attorney review.\n\n"
            f"Client and matter context:\n{context}\n\n"
            f"Transcript:\n{transcript}\n\n"
        )
        instructions = {
            "formal_tone": "Rewrite the transcript in a formal legal tone while preserving all facts and meaning.",
            "attorney_notes": "Create attorney notes with headings: Key facts, Legal issues to consider, Open questions, Documents/evidence needed, Next steps.",
            "billing_entry": "Create a billing entry with Date: TO VERIFY, Client/Matter, Task, Billing narrative, and Time: TO VERIFY unless time is clearly stated.",
            "timeline": "Create a chronological timeline. Use TO VERIFY for unclear dates and include people, events, and source details when present.",
            "client_letter": "Draft a client letter with greeting, concise summary, requested action items, and professional closing. Do not include recipient address unless stated.",
            "checklist": "Create a matter checklist with completed items, pending items, missing information, documents to request, and deadlines to verify.",
        }
        return base + instructions.get(mode, instructions["attorney_notes"])

    def _client_matter_context(self) -> str:
        items = {
            "client_name": self.client_name_var.get().strip(),
            "matter_number": self.matter_number_var.get().strip(),
            "court": self.court_var.get().strip(),
            "opposing_party": self.opposing_party_var.get().strip(),
        }
        return "\n".join(f"- {key}: {value or 'TO VERIFY'}" for key, value in items.items())

    def _legal_mode_label(self, mode: str) -> str:
        labels = {
            "formal_tone": "formal legal rewrite",
            "attorney_notes": "attorney notes",
            "billing_entry": "billing entry",
            "timeline": "timeline",
            "client_letter": "client letter",
            "checklist": "checklist",
        }
        return labels.get(mode, "legal draft")

    def _legal_work_product_done(self, mode: str, output: str) -> None:
        self.is_busy = False
        if mode == "formal_tone":
            self.transcript_text.delete("1.0", tk.END)
            self.transcript_text.insert("1.0", output)
        elif mode == "client_letter":
            self.email_subject_var.set(self.email_subject_var.get() or "Draft client letter")
            self.email_body_text.delete("1.0", tk.END)
            self.email_body_text.insert("1.0", output)

        self.legal_output_text.delete("1.0", tk.END)
        self.legal_output_text.insert("1.0", output)
        self.status_var.set(f"{self._legal_mode_label(mode).title()} ready for review")

    def rewrite_transcript_with_gemini(self, mode: str) -> None:
        if self.is_busy:
            return
        if not self.api_key_var.get().strip():
            messagebox.showerror("Missing API key", "Enter your Google AI Studio API key first.")
            return

        transcript = self.transcript_text.get("1.0", tk.END).strip()
        if not transcript:
            messagebox.showerror("Missing transcript", "Record or type a transcript first.")
            return

        self.is_busy = True
        label = "email" if mode == "email" else "grammar cleanup"
        self.status_var.set(f"Sending transcript to Gemini for {label}")
        threading.Thread(target=self._rewrite_transcript_worker, args=(mode, transcript), daemon=True).start()

    def _rewrite_transcript_worker(self, mode: str, transcript: str) -> None:
        try:
            if mode == "email":
                instruction = (
                    "Turn the transcript into a clear, professional email draft. "
                    "Preserve the speaker's intent and important details. "
                    "Return strict JSON only with this shape: "
                    "{\"to\":\"\",\"cc\":\"\",\"bcc\":\"\",\"subject\":\"...\",\"body\":\"...\"}. "
                    "Put email addresses in to/cc/bcc only if they are clearly spoken. "
                    "Add a concise subject line, greeting, body, and closing in body. "
                    "Do not invent names, dates, attachments, commitments, or facts not present in the transcript. "
                    "If a recipient name is unknown, use a generic greeting."
                )
                result_label = "Email draft ready"
            else:
                instruction = (
                    "Clean up this voice-to-text transcript. "
                    "Fix grammar, punctuation, capitalization, and likely speech recognition mistakes. "
                    "Keep the same meaning, same facts, same order, and same overall voice. "
                    "Do not add new details, remove important details, or turn it into a different format."
                )
                result_label = "Transcript cleaned up"

            prompt = f"{instruction}\n\nTranscript:\n{transcript}"
            client = genai.Client(api_key=self.api_key_var.get().strip())
            request = {
                "model": self.gemini_model_var.get().strip() or DEFAULT_GEMINI_MODEL,
                "contents": prompt,
            }
            if mode == "email":
                request["config"] = types.GenerateContentConfig(response_mime_type="application/json")
            response = client.models.generate_content(**request)
            rewritten = (response.text or "").strip()
            if not rewritten:
                raise RuntimeError("Gemini returned an empty response.")
            if mode == "email":
                email_draft = self._parse_json_response(rewritten)
                self.root.after(0, self._email_draft_done, email_draft, result_label)
                return
            self.root.after(0, self._rewrite_transcript_done, rewritten, result_label)
        except Exception as exc:
            self.root.after(0, self._task_failed, "Gemini transcript rewrite failed", str(exc))

    def _rewrite_transcript_done(self, rewritten: str, result_label: str) -> None:
        self.is_busy = False
        self.transcript_text.delete("1.0", tk.END)
        self.transcript_text.insert("1.0", rewritten)
        self.status_var.set(result_label)

    def _email_draft_done(self, email_draft: dict, result_label: str) -> None:
        self.is_busy = False
        self.email_to_var.set(str(email_draft.get("to", "") or ""))
        self.email_cc_var.set(str(email_draft.get("cc", "") or ""))
        self.email_bcc_var.set(str(email_draft.get("bcc", "") or ""))
        self.email_subject_var.set(str(email_draft.get("subject", "") or ""))
        body = str(email_draft.get("body", "") or "")
        self.email_body_text.delete("1.0", tk.END)
        self.email_body_text.insert("1.0", body)
        self.transcript_text.delete("1.0", tk.END)
        self.transcript_text.insert("1.0", body)
        self.status_var.set(result_label)

    def connect_gmail(self) -> None:
        if self.is_busy:
            return
        self.is_busy = True
        self.status_var.set("Connecting to Gmail")
        threading.Thread(target=self._connect_gmail_worker, daemon=True).start()

    def _connect_gmail_worker(self) -> None:
        try:
            self._get_gmail_service()
            self.root.after(0, self._gmail_connected)
        except Exception as exc:
            self.root.after(0, self._task_failed, "Gmail connection failed", str(exc))

    def _gmail_connected(self) -> None:
        self.is_busy = False
        self.status_var.set("Gmail connected")
        messagebox.showinfo("Gmail connected", "Gmail is connected. You can now create drafts.")

    def create_gmail_draft(self) -> None:
        if self.is_busy:
            return
        draft = self._current_email_draft()
        if not draft["to"]:
            messagebox.showerror("Missing recipient", "Enter a recipient in the To field before creating a Gmail draft.")
            return
        if not draft["subject"] and not draft["body"]:
            messagebox.showerror("Missing email", "Create or type an email subject/body first.")
            return

        self.is_busy = True
        self.status_var.set("Creating Gmail draft")
        threading.Thread(target=self._create_gmail_draft_worker, args=(draft,), daemon=True).start()

    def _create_gmail_draft_worker(self, draft: dict[str, str]) -> None:
        try:
            service = self._get_gmail_service()
            message = EmailMessage()
            message["To"] = draft["to"]
            if draft["cc"]:
                message["Cc"] = draft["cc"]
            if draft["bcc"]:
                message["Bcc"] = draft["bcc"]
            message["Subject"] = draft["subject"]
            message.set_content(draft["body"])

            encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            result = service.users().drafts().create(userId="me", body={"message": {"raw": encoded}}).execute()
            self.root.after(0, self._gmail_draft_created, result.get("id", ""))
        except Exception as exc:
            self.root.after(0, self._task_failed, "Gmail draft failed", str(exc))

    def _gmail_draft_created(self, draft_id: str) -> None:
        self.is_busy = False
        self.status_var.set(f"Gmail draft created: {draft_id}")
        messagebox.showinfo("Gmail draft created", "Draft created in Gmail. Review it in Gmail before sending.")

    def open_email_app(self) -> None:
        draft = self._current_email_draft()
        if not draft["subject"] and not draft["body"]:
            messagebox.showerror("Missing email", "Create or type an email subject/body first.")
            return
        mailto = f"mailto:{quote(draft['to'])}?subject={quote(draft['subject'])}&body={quote(draft['body'])}"
        if draft["cc"]:
            mailto += f"&cc={quote(draft['cc'])}"
        if draft["bcc"]:
            mailto += f"&bcc={quote(draft['bcc'])}"
        webbrowser.open(mailto)
        self.status_var.set("Opened email draft in default email app")

    def show_gmail_setup_help(self) -> None:
        help_window = tk.Toplevel(self.root)
        help_window.title("Gmail Setup Help")
        help_window.geometry("760x620")

        container = ttk.Frame(help_window, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        text = tk.Text(container, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        instructions = f"""Gmail Draft Setup - Option 1: Use Your Own Google OAuth Client

This setup lets each person use their own Google Cloud OAuth credentials. Their Gmail login token stays on their own computer.

What you need:
- A Google account
- Internet access
- This V4 app folder:
    {self.app_dir}

Step 1 - Open Google Cloud Console
Go to:
https://console.cloud.google.com/

Step 2 - Create or select a project
- Click the project selector at the top.
- Choose an existing project or create a new one.
- A name like "Whisper Voice To Form Gmail" is fine.

Step 3 - Enable the Gmail API
- In Google Cloud Console, search for "Gmail API".
- Open Gmail API.
- Click Enable.

Step 4 - Configure the OAuth consent screen
- Go to APIs & Services > OAuth consent screen.
- Choose External unless this is a Google Workspace internal app.
- Fill in the required app name, user support email, and developer contact email.
- For a private/test setup, keep the app in Testing mode.

Step 5 - Add yourself as a test user
- On the OAuth consent screen page, find Test users.
- Add the Gmail address that will use this app.
- If someone else is using the app, add their Gmail address too.

Step 6 - Create OAuth credentials
- Go to APIs & Services > Credentials.
- Click Create Credentials.
- Choose OAuth client ID.
- Application type: Desktop app.
- Give it a name such as "Whisper Voice To Form Desktop".
- Click Create.

Step 7 - Download the JSON file
- Download the OAuth client JSON file.
- Rename it exactly to:
    gmail-credentials.json

Step 8 - Put the file in the V4 app folder
Place gmail-credentials.json here:
{self.app_dir}

Step 9 - Connect Gmail in the app
- Return to V4.
- Click Connect Gmail.
- Your browser should open.
- Log into Gmail.
- Approve Gmail compose access.

Step 10 - Create drafts
- Use Make Email to create an editable email draft.
- Review the To, Subject, and Body fields.
- Click Create Gmail Draft.
- Open Gmail and review the draft before sending.

Privacy notes:
- This app creates Gmail drafts only. It does not auto-send email.
- Your Gmail token is saved locally as .gmail-token.json.
- Do not share gmail-credentials.json or .gmail-token.json publicly.
- For legal, medical, student, or client information, review your confidentiality rules before sending text to Gemini.
"""
        text.insert("1.0", instructions)
        text.configure(state=tk.DISABLED)

        buttons = ttk.Frame(container)
        buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(buttons, text="Open Google Cloud Console", command=lambda: webbrowser.open("https://console.cloud.google.com/")).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Close", command=help_window.destroy).pack(side=tk.RIGHT)

    def _current_email_draft(self) -> dict[str, str]:
        return {
            "to": self.email_to_var.get().strip(),
            "cc": self.email_cc_var.get().strip(),
            "bcc": self.email_bcc_var.get().strip(),
            "subject": self.email_subject_var.get().strip(),
            "body": self.email_body_text.get("1.0", tk.END).strip(),
        }

    def _get_gmail_service(self):
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise RuntimeError("Gmail dependencies are missing. Re-run install_windows_v4.bat.") from exc

        credentials = None
        if self.gmail_token_file.exists():
            credentials = Credentials.from_authorized_user_file(str(self.gmail_token_file), GMAIL_SCOPES)

        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())

        if not credentials or not credentials.valid:
            if not self.gmail_credentials_file.exists():
                raise RuntimeError(
                    "Missing gmail-credentials.json. Create a Google Cloud OAuth Desktop client, "
                    "download its JSON file, rename it to gmail-credentials.json, and place it in the V4 app folder."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(self.gmail_credentials_file), GMAIL_SCOPES)
            credentials = flow.run_local_server(port=0)

        self.gmail_token_file.write_text(credentials.to_json(), encoding="utf-8")
        return build("gmail", "v1", credentials=credentials)

    def send_transcript_to_ai(self) -> None:
        if self.is_busy:
            return
        if not self.pdf_fields:
            messagebox.showerror("Missing PDF", "Upload a fillable PDF first.")
            return
        if not self.api_key_var.get().strip():
            messagebox.showerror("Missing API key", "Enter your Google AI Studio API key first.")
            return

        transcript = self.transcript_text.get("1.0", tk.END).strip()
        if not transcript:
            messagebox.showerror("Missing transcript", "Record or type a transcript first.")
            return

        self.is_busy = True
        self.status_var.set("Sending transcript and PDF fields to Gemini")
        threading.Thread(target=self._gemini_worker, args=(transcript,), daemon=True).start()

    def _gemini_worker(self, transcript: str) -> None:
        try:
            client = genai.Client(api_key=self.api_key_var.get().strip())
            field_payload = []
            for name, details in self.pdf_fields.items():
                field_payload.append(
                    {
                        "name": name,
                        "type": str(details.get("/FT", "")),
                        "label": str(details.get("/TU", "")),
                        "current_value": self.field_values.get(name, ""),
                    }
                )

            prompt = (
                "You fill Adobe PDF form fields from a voice transcript. "
                "Return strict JSON only. Use exact PDF field names as keys. "
                "Use empty strings for fields that are not answered. "
                "Do not invent personal information. For checkboxes, use Yes or Off.\n\n"
                f"PDF fields:\n{json.dumps(field_payload, indent=2)}\n\n"
                f"Transcript:\n{transcript}"
            )
            response = client.models.generate_content(
                model=self.gemini_model_var.get().strip() or DEFAULT_GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            values = self._parse_json_response(response.text or "")
            clean_values = {name: str(values.get(name, "")) for name in self.pdf_fields}
            self.root.after(0, self._gemini_done, clean_values)
        except Exception as exc:
            self.root.after(0, self._task_failed, "Gemini request failed", str(exc))

    def _parse_json_response(self, text: str) -> dict:
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = stripped.strip("`")
            if stripped.lower().startswith("json"):
                stripped = stripped[4:].strip()
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise ValueError("Gemini did not return a JSON object.")
        return parsed

    def _gemini_done(self, values: dict[str, str]) -> None:
        self.is_busy = False
        self.field_values.update(values)
        self.refresh_fields_tree()
        self.render_current_page()
        self.status_var.set("AI values ready for review. Double-click a value to edit it.")

    def export_filled_pdf(self) -> None:
        if self.pdf_path is None:
            messagebox.showerror("Missing PDF", "Upload a fillable PDF first.")
            return

        output_path = filedialog.asksaveasfilename(
            title="Save filled PDF",
            defaultextension=".pdf",
            initialfile=f"{self.pdf_path.stem}-filled.pdf",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not output_path:
            return

        try:
            self.write_filled_pdf(Path(output_path))

            self.status_var.set(f"Filled PDF saved: {output_path}")
            messagebox.showinfo("Export complete", f"Saved filled PDF:\n{output_path}")
        except Exception as exc:
            messagebox.showerror("PDF export failed", str(exc))

    def update_original_pdf(self) -> None:
        if self.pdf_path is None:
            messagebox.showerror("Missing PDF", "Load a PDF first.")
            return
        if not self.pdf_path.exists():
            messagebox.showerror("Missing PDF", f"The loaded PDF no longer exists:\n{self.pdf_path}")
            return

        self.commit_preview_editor()
        confirmed = messagebox.askyesno(
            "Update original PDF",
            "This will update the currently loaded PDF file in its original folder.\n\n"
            "V4 will make a timestamped backup first. Continue?",
        )
        if not confirmed:
            return

        original_path = self.pdf_path
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = original_path.with_name(f"{original_path.stem}.backup-{timestamp}{original_path.suffix}")
        temp_path = original_path.with_name(f".{original_path.stem}.v4-update-{timestamp}{original_path.suffix}")

        try:
            shutil.copy2(original_path, backup_path)
            self.write_filled_pdf(temp_path)
            if self.pdf_document is not None:
                self.pdf_document.close()
                self.pdf_document = None
            os.replace(temp_path, original_path)
            self.load_pdf(original_path)
            self.status_var.set(f"Original PDF updated. Backup saved: {backup_path.name}")
            messagebox.showinfo(
                "Original PDF updated",
                f"Updated:\n{original_path}\n\nBackup saved:\n{backup_path}",
            )
        except Exception as exc:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            messagebox.showerror("Update original PDF failed", str(exc))

    def write_filled_pdf(self, output_path: Path) -> None:
        if self.pdf_path is None:
            raise RuntimeError("No PDF is loaded.")

        reader = PdfReader(str(self.pdf_path))
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        if "/AcroForm" in reader.trailer["/Root"]:
            writer._root_object.update({NameObject("/AcroForm"): reader.trailer["/Root"]["/AcroForm"]})
            writer._root_object["/AcroForm"].update({NameObject("/NeedAppearances"): BooleanObject(True)})

        values = {name: value for name, value in self.field_values.items() if value != ""}
        for page in writer.pages:
            writer.update_page_form_field_values(page, values)

        with open(output_path, "wb") as output_file:
            writer.write(output_file)

    def _task_failed(self, title: str, error: str) -> None:
        self.is_busy = False
        self.status_var.set(title)
        self.recording_status_var.set("Mic idle")
        messagebox.showerror(title, error)


def main() -> None:
    root = tk.Tk()
    GeminiFormFillerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
