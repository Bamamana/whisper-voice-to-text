import { createChatCompletion, discoverModels } from './transcription.js';

const GRADE_STORAGE_KEY = 'wv1api_grading_settings';
const element = (id) => document.getElementById(id);

let roster = [];
let actions = [];

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

  element('analyzeGradesBtn').addEventListener('click', async () => {
    const assignment = element('gradingAssignmentInput').value.trim();
    const transcript = element('gradingTranscriptInput').value.trim();
    const model = element('gradingModelSelect').value.trim();
    const students = activeStudents();
    if (!assignment || !transcript || !model || !students.length) {
      element('gradingStatus').textContent = 'Add an assignment, transcript, roster, and grading model.';
      return;
    }
    const button = element('analyzeGradesBtn');
    button.disabled = true;
    element('gradingStatus').textContent = 'Analyzing grade notes...';
    try {
      const response = await createChatCompletion(getSettings(), model, gradingPrompt(transcript, assignment, element('gradingPeriodSelect').value, students));
      const result = normalizeResults(extractJson(response));
      actions = result.actions;
      renderActions();
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
}