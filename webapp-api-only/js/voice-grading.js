import { MicRecorder, blobToWav } from './audio.js';
import { createChatCompletion, discoverModels, transcribeBlob } from './transcription.js';
import { buildCanvasGradebookCsv, parseCanvasGradebook } from './canvas-gradebook.js';
import { matchClearGrades, remainingStudents } from './grade-matching.js';

const GRADE_STORAGE_KEY = 'wv1api_grading_settings';
const element = (id) => document.getElementById(id);

let roster = [];
let actions = [];
let canvasGradebook = null;
let unresolvedNotes = [];
let locallyMatchedNames = new Set();
const gradingRecorder = new MicRecorder();

function loadGradeSettings() {
  try {
    return JSON.parse(localStorage.getItem(GRADE_STORAGE_KEY) || '{}');
  } catch (_error) {
    return {};
  }
}

function saveGradeSettings(settings) {
  localStorage.setItem(GRADE_STORAGE_KEY, JSON.stringify(settings));
}

function normalizedHeader(value) {
  return String(value || '').toLowerCase().replace(/[^a-z0-9]/g, '');
}

function parseCsvLine(line) {
  const fields = [];
  let value = '';
  let quoted = false;
  for (let index = 0; index < line.length; index += 1) {
    const character = line[index];
    if (character === '"' && line[index + 1] === '"') {
      value += '"';
      index += 1;
    } else if (character === '"') {
      quoted = !quoted;
    } else if (character === ',' && !quoted) {
      fields.push(value.trim());
      value = '';
    } else {
      value += character;
    }
  }
  fields.push(value.trim());
  return fields;
}

function parseRosterCsv(text) {
  const lines = text.split(/\r?\n/).filter((line) => line.trim());
  if (lines.length < 2) throw new Error('Roster CSV needs a header and at least one student.');
  const headers = parseCsvLine(lines[0]).map(normalizedHeader);
  const indexOf = (...names) => headers.findIndex((header) => names.includes(header));
  const fullNameIndex = indexOf('studentname', 'fullname', 'fullstudentname', 'name', 'student');
  const firstNameIndex = indexOf('firstname', 'first', 'studentfirstname', 'givenname');
  const lastNameIndex = indexOf('lastname', 'last', 'studentlastname', 'surname', 'familyname');
  const periodIndex = indexOf('period', 'classperiod', 'class', 'section', 'block');
  if (fullNameIndex < 0 && (firstNameIndex < 0 || lastNameIndex < 0)) {
    throw new Error('Roster CSV needs Student Name or both First Name and Last Name columns.');
  }

  return lines.slice(1).map(parseCsvLine).map((fields) => {
    const fullName = fullNameIndex >= 0 ? fields[fullNameIndex] : '';
    const firstName = firstNameIndex >= 0 ? fields[firstNameIndex] : '';
    const lastName = lastNameIndex >= 0 ? fields[lastNameIndex] : '';
    const name = fullName || [lastName, firstName].filter(Boolean).join(', ');
    return { name: name.trim(), period: (periodIndex >= 0 ? fields[periodIndex] : '')?.trim() || 'All students' };
  }).filter((student) => student.name);
}

function populatePeriods() {
  const periods = [...new Set(roster.map((student) => student.period))].sort();
  element('gradingPeriodSelect').replaceChildren(...periods.map((period) => new Option(period, period)));
  element('gradingPeriodSelect').disabled = periods.length === 0;
}

function activeStudents() {
  const period = element('gradingPeriodSelect').value;
  return roster.filter((student) => student.period === period).map((student) => student.name);
}

function seedGradeRows() {
  const assignmentHeader = element('canvasAssignmentSelect').value;
  const existingScores = new Map((canvasGradebook?.students || []).map((student) => [
    String(student.Student || '').trim().toLowerCase(),
    String(student[assignmentHeader] || '').trim()
  ]));
  actions = activeStudents().map((studentName) => ({
    student_name: studentName,
    score: existingScores.get(studentName.toLowerCase()) || '',
    notes: '',
    evidence: '',
    confidence: ''
  }));
  renderActions();
}

function applyGradeActions(newActions) {
  const byStudent = new Map(actions.map((action) => [action.student_name.toLowerCase(), action]));
  newActions.forEach((newAction) => {
    const existing = byStudent.get(newAction.student_name.toLowerCase());
    if (existing) {
      Object.assign(existing, newAction);
    } else {
      actions.push(newAction);
    }
  });
}

function gradingPrompt(transcript, assignment, period, students) {
  const rosterText = students.map((name) => `- ${name}`).join('\n');
  return `You convert teacher grading transcripts into structured grade actions.

Return JSON only. Do not use markdown fences or add commentary.

Context:
- Assignment: ${assignment}
- Period: ${period}
- Remaining unmatched roster:
${rosterText}

Rules:
- Extract only grades explicitly present in the transcript.
- Match spoken names to the closest roster name using spelling, phonetics, initials, and process of elimination.
- Use the exact roster name in student_name when matched.
- Do not silently guess between equally plausible students; add a warning instead.
- Keep notes concise and classroom-appropriate.
- If there are no actionable grades, return an empty actions array.

Return exactly this JSON object shape:
{"assignment":"${assignment}","period":"${period}","actions":[{"student_name":"Last, First","score":"18/20","notes":"short note","evidence":"supporting quote","confidence":0.0}],"warnings":["review note"]}

Transcript:
${transcript}`;
}

function extractJson(text) {
  const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/i);
  const candidate = fenced ? fenced[1] : text.slice(text.indexOf('{'), text.lastIndexOf('}') + 1);
  return JSON.parse(candidate);
}

function normalizeResults(payload) {
  if (!payload || !Array.isArray(payload.actions) || !Array.isArray(payload.warnings || [])) {
    throw new Error('The grading model returned an invalid grade format.');
  }
  return {
    actions: payload.actions.map((action) => ({
      student_name: String(action.student_name || '').trim(),
      score: String(action.score || '').trim(),
      notes: String(action.notes || '').trim(),
      evidence: String(action.evidence || '').trim(),
      confidence: action.confidence === undefined || action.confidence === null ? '' : String(action.confidence)
    })).filter((action) => action.student_name && action.score),
    warnings: payload.warnings.map((warning) => String(warning).trim()).filter(Boolean)
  };
}

function cellInput(value, field, rowIndex) {
  const input = document.createElement('input');
  input.className = 'w-full border border-slate-200 bg-white px-2 py-1 text-sm';
  input.value = value;
  input.addEventListener('input', () => { actions[rowIndex][field] = input.value; });
  return input;
}

function renderActions() {
  const body = element('gradingResults');
  body.replaceChildren();
  actions.forEach((action, rowIndex) => {
    const row = document.createElement('tr');
    ['student_name', 'score', 'notes', 'evidence', 'confidence'].forEach((field) => {
      const cell = document.createElement('td');
      cell.className = 'px-3 py-2 align-top';
      cell.append(cellInput(action[field], field, rowIndex));
      row.append(cell);
    });
    body.append(row);
  });
  element('gradingEmptyState').classList.toggle('hidden', actions.length > 0);
}

function showWarnings(warnings) {
  const container = element('gradingWarnings');
  container.replaceChildren();
  warnings.forEach((warning) => {
    const item = document.createElement('p');
    item.textContent = warning;
    container.append(item);
  });
  container.classList.toggle('hidden', warnings.length === 0);
}

function showUnresolved() {
  const container = element('gradingUnresolved');
  container.replaceChildren();
  if (!unresolvedNotes.length) {
    container.classList.add('hidden');
    return;
  }
  const heading = document.createElement('p');
  heading.className = 'mb-2 text-xs font-bold uppercase text-slate-500';
  heading.textContent = `${unresolvedNotes.length} note(s) need review or AI matching`;
  container.append(heading);
  unresolvedNotes.forEach((note) => {
    const item = document.createElement('p');
    item.className = 'border-t border-slate-100 py-2';
    item.textContent = note;
    container.append(item);
  });
  container.classList.remove('hidden');
}

function runClearMatching() {
  const transcript = element('gradingTranscriptInput').value.trim();
  const students = activeStudents();
  if (!transcript || !students.length) {
    element('gradingStatus').textContent = 'Load a roster and add grade notes first.';
    return false;
  }
  const result = matchClearGrades(transcript, students);
  locallyMatchedNames = result.matchedNames;
  unresolvedNotes = result.unresolved;
  applyGradeActions(result.actions);
  renderActions();
  showUnresolved();
  showWarnings(unresolvedNotes.length ? ['Only high-confidence exact roster matches were applied locally. Review the notes below or send them to AI.'] : []);
  element('gradingStatus').textContent = `${result.actions.length} clear grade(s) matched locally; ${unresolvedNotes.length} note(s) remain.`;
  return true;
}

function downloadCsv() {
  if (!actions.length) return;
  const quote = (value) => `"${String(value).replaceAll('"', '""')}"`;
  const rows = [['Student', 'Score', 'Notes', 'Evidence', 'Confidence'], ...actions.map((action) => [
    action.student_name, action.score, action.notes, action.evidence, action.confidence
  ])];
  const blob = new Blob([rows.map((row) => row.map(quote).join(',')).join('\n')], { type: 'text/csv' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `voice-grades-${Date.now()}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
}

function downloadFile(content, filename, type) {
  const link = document.createElement('a');
  link.href = URL.createObjectURL(new Blob([content], { type }));
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

function populateCanvasAssignments() {
  const select = element('canvasAssignmentSelect');
  if (!canvasGradebook) {
    select.replaceChildren(new Option('Import a Canvas gradebook', ''));
    select.disabled = true;
    return;
  }
  select.replaceChildren(...canvasGradebook.assignments.map((assignment) => new Option(
    assignment.pointsPossible ? `${assignment.name} (${assignment.pointsPossible} points)` : assignment.name,
    assignment.header
  )));
  select.disabled = false;
  element('gradingAssignmentInput').value = canvasGradebook.assignments[0]?.name || '';
}

export function initializeVoiceGrading(getSettings) {
  const saved = loadGradeSettings();
  element('gradingAssignmentInput').value = saved.assignment || '';
  element('gradingModelSelect').append(new Option(saved.model || 'Select a chat model', saved.model || ''));

  element('gradingRosterInput').addEventListener('change', async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      roster = parseRosterCsv(await file.text());
      if (!roster.length) throw new Error('No students were found in this roster.');
      populatePeriods();
      element('gradingRosterStatus').textContent = `${roster.length} students loaded.`;
      element('gradingStatus').textContent = 'Roster ready.';
    } catch (error) {
      roster = [];
      populatePeriods();
      element('gradingRosterStatus').textContent = error.message;
    }
  });

  element('canvasGradebookInput').addEventListener('change', async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      canvasGradebook = parseCanvasGradebook(await file.text());
      roster = canvasGradebook.students.map((student) => ({
        name: String(student.Student || '').trim(),
        period: String(student.Section || '').trim() || 'Canvas Import'
      }));
      populatePeriods();
      populateCanvasAssignments();
      seedGradeRows();
      element('canvasGradebookStatus').textContent = `${roster.length} students and ${canvasGradebook.assignments.length} assignments loaded locally.`;
      element('gradingRosterStatus').textContent = 'Canvas roster loaded.';
      element('gradingStatus').textContent = 'Canvas gradebook ready for grading.';
    } catch (error) {
      canvasGradebook = null;
      populateCanvasAssignments();
      element('canvasGradebookStatus').textContent = error.message;
    }
  });

  element('canvasAssignmentSelect').addEventListener('change', (event) => {
    const assignment = canvasGradebook?.assignments.find((item) => item.header === event.target.value);
    if (assignment) {
      element('gradingAssignmentInput').value = assignment.name;
      seedGradeRows();
    }
  });

  element('gradingPeriodSelect').addEventListener('change', () => {
    if (canvasGradebook) seedGradeRows();
  });

  element('loadGradingModelsBtn').addEventListener('click', async () => {
    element('gradingStatus').textContent = 'Loading models...';
    try {
      const models = await discoverModels(getSettings());
      const current = element('gradingModelSelect').value;
      element('gradingModelSelect').replaceChildren(new Option('Select a chat model', ''), ...models.map((model) => new Option(model.label, model.id)));
      element('gradingModelSelect').value = current;
      element('gradingStatus').textContent = `${models.length} model(s) available.`;
    } catch (error) {
      element('gradingStatus').textContent = `Could not load models: ${error.message}`;
    }
  });

  element('useTranscriptBtn').addEventListener('click', () => {
    element('gradingTranscriptInput').value = element('outputText').value;
    element('gradingStatus').textContent = 'Current transcript copied.';
  });

  element('gradingRecordBtn').addEventListener('click', async () => {
    const button = element('gradingRecordBtn');
    if (!gradingRecorder.recording) {
      try {
        await gradingRecorder.start();
        button.textContent = 'Stop and transcribe';
        element('gradingStatus').textContent = 'Recording grade notes...';
      } catch (error) {
        element('gradingStatus').textContent = `Microphone failed: ${error.message}`;
      }
      return;
    }

    button.disabled = true;
    try {
      const recording = await gradingRecorder.stop();
      element('gradingStatus').textContent = 'Transcribing grade notes...';
      const wav = await blobToWav(recording);
      const transcript = await transcribeBlob(wav.blob, wav.extension, getSettings());
      const input = element('gradingTranscriptInput');
      input.value = [input.value.trim(), transcript].filter(Boolean).join('\n');
      runClearMatching();
    } catch (error) {
      element('gradingStatus').textContent = `Transcription failed: ${error.message}`;
    } finally {
      button.disabled = false;
      button.textContent = 'Start recording';
    }
  });

  element('matchClearGradesBtn').addEventListener('click', runClearMatching);

  element('analyzeGradesBtn').addEventListener('click', async () => {
    const assignment = element('gradingAssignmentInput').value.trim();
    if (!runClearMatching()) return;
    const transcript = unresolvedNotes.join('\n');
    const model = element('gradingModelSelect').value.trim();
    const students = remainingStudents(activeStudents(), locallyMatchedNames);
    if (!assignment || !transcript || !model || !students.length) {
      element('gradingStatus').textContent = transcript ? 'Select a grading model to analyze unresolved notes.' : 'All notes were matched locally; no AI review is needed.';
      return;
    }
    const button = element('analyzeGradesBtn');
    button.disabled = true;
    element('gradingStatus').textContent = 'Analyzing grade notes...';
    try {
      const response = await createChatCompletion(getSettings(), model, gradingPrompt(transcript, assignment, element('gradingPeriodSelect').value, students));
      const result = normalizeResults(extractJson(response));
      applyGradeActions(result.actions);
      unresolvedNotes = [];
      renderActions();
      showUnresolved();
      showWarnings(result.warnings);
      element('gradingStatus').textContent = `${actions.length} grade action(s) ready for review.`;
      saveGradeSettings({ assignment, model });
    } catch (error) {
      element('gradingStatus').textContent = `Analysis failed: ${error.message}`;
    } finally {
      button.disabled = false;
    }
  });

  element('exportGradesBtn').addEventListener('click', downloadCsv);
  element('exportCanvasBtn').addEventListener('click', () => {
    try {
      if (!canvasGradebook) throw new Error('Import a Canvas gradebook first.');
      const result = buildCanvasGradebookCsv(canvasGradebook, element('canvasAssignmentSelect').value, actions);
      downloadFile(result.csv, `canvas-grades-${Date.now()}.csv`, 'text/csv');
      element('gradingStatus').textContent = `${result.updated} score(s) merged into ${result.assignment}.`;
    } catch (error) {
      element('gradingStatus').textContent = `Canvas export failed: ${error.message}`;
    }
  });
}