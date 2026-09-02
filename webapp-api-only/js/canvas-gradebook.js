const ASSIGNMENT_HEADER = /^(.+?)\s+\((\d+)\)\s*$/;

function parseCanvasCsvLine(line) {
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
      fields.push(value);
      value = '';
    } else {
      value += character;
    }
  }
  fields.push(value);
  return fields;
}

function csvRows(text) {
  const rows = [];
  let row = '';
  let quoted = false;
  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    if (character === '"') {
      row += character;
      if (text[index + 1] === '"') {
        row += text[index + 1];
        index += 1;
      } else {
        quoted = !quoted;
      }
    } else if ((character === '\n' || character === '\r') && !quoted) {
      if (row.trim()) rows.push(parseCanvasCsvLine(row).map((value) => value.trim()));
      row = '';
      if (character === '\r' && text[index + 1] === '\n') index += 1;
    } else {
      row += character;
    }
  }
  if (row.trim()) rows.push(parseCanvasCsvLine(row).map((value) => value.trim()));
  return rows;
}

function rowObject(headers, fields) {
  return Object.fromEntries(headers.map((header, index) => [header, fields[index] || '']));
}

function pointsRow(row) {
  return String(row?.Student || '').trim().toLowerCase() === 'points possible';
}

export function parseCanvasGradebook(text) {
  const rows = csvRows(text);
  if (rows.length < 2) throw new Error('Canvas export needs a header and at least one row.');
  const headers = rows[0];
  const assignments = headers.map((header) => {
    const match = header.match(ASSIGNMENT_HEADER);
    return match ? { header, name: match[1].trim(), id: match[2] } : null;
  }).filter(Boolean);
  if (!assignments.length) throw new Error('No Canvas assignment columns were found. Export the Canvas gradebook as CSV.');

  const dataRows = rows.slice(1).map((fields) => rowObject(headers, fields));
  const pointsPossible = pointsRow(dataRows[0]) ? dataRows.shift() : null;
  assignments.forEach((assignment) => {
    assignment.pointsPossible = String(pointsPossible?.[assignment.header] || '').trim();
  });
  const students = dataRows.filter((row) => String(row.Student || '').trim());
  if (!students.length) throw new Error('No student rows were found in this Canvas export.');
  return { headers, pointsPossible, students, assignments };
}

function numeric(value) {
  const number = Number.parseFloat(String(value || '').trim());
  return Number.isFinite(number) ? number : null;
}

function canvasScore(score, pointsPossible) {
  const value = String(score || '').trim();
  const slash = value.match(/^(\d+(?:\.\d+)?)\s*(?:\/|out of)\s*(\d+(?:\.\d+)?)$/i);
  if (slash) {
    const earned = Number.parseFloat(slash[1]);
    const denominator = Number.parseFloat(slash[2]);
    const canvasPoints = numeric(pointsPossible);
    if (canvasPoints !== null && denominator > 0) {
      return ((earned / denominator) * canvasPoints).toFixed(2);
    }
  }
  const plainNumber = numeric(value);
  return plainNumber === null ? null : plainNumber.toFixed(2);
}

function quoteCsv(value) {
  return `"${String(value || '').replaceAll('"', '""')}"`;
}

export function buildCanvasGradebookCsv(template, assignmentHeader, actions) {
  const assignment = template.assignments.find((item) => item.header === assignmentHeader);
  if (!assignment) throw new Error('Choose a Canvas assignment before exporting.');
  const byStudent = new Map(actions.map((action) => [action.student_name.trim().toLowerCase(), action]));
  let updated = 0;
  const outputRows = [];
  if (template.pointsPossible) outputRows.push(template.pointsPossible);
  template.students.forEach((student) => {
    const action = byStudent.get(String(student.Student || '').trim().toLowerCase());
    const score = action?.score.trim() ? canvasScore(action.score, assignment.pointsPossible) : null;
    const maximum = numeric(assignment.pointsPossible);
    if (action?.score.trim() && (score === null || numeric(score) < 0 || (maximum !== null && numeric(score) > maximum))) {
      throw new Error(`${action.student_name} has a score outside this assignment's valid range: ${action.score}`);
    }
    const row = { ...student };
    if (score !== null) {
      row[assignmentHeader] = score;
      updated += 1;
    }
    outputRows.push(row);
  });
  const lines = [template.headers, ...outputRows.map((row) => template.headers.map((header) => row[header] || ''))]
    .map((row) => row.map(quoteCsv).join(','));
  return { csv: lines.join('\n'), updated, assignment: assignment.name };
}