function downloadFile(content, filename, type) {
  const link = document.createElement('a');
  link.href = URL.createObjectURL(new Blob([content], { type }));
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

function csv(actions) {
  const quote = (value) => `"${String(value).replaceAll('"', '""')}"`;
  const rows = [['Student', 'Score', 'Notes', 'Evidence', 'Confidence'], ...actions.map((action) => [action.student_name, action.score, action.notes, action.evidence, action.confidence])];
  return rows.map((row) => row.map(quote).join(',')).join('\n');
}

export function exportGradeActions(actions) {
  if (actions.length) downloadFile(csv(actions), `voice-grades-${Date.now()}.csv`, 'text/csv');
}

export function exportChangedGrades(actions, changedStudentNames) {
  const changed = actions.filter((action) => changedStudentNames.has(action.student_name));
  if (changed.length) downloadFile(csv(changed), `changed-voice-grades-${Date.now()}.csv`, 'text/csv');
}

export function exportGradeAudit(auditLog) {
  if (!auditLog.length) return;
  const quote = (value) => `"${String(value).replaceAll('"', '""')}"`;
  const rows = [['Timestamp', 'Student', 'Previous score', 'Score', 'Source', 'Evidence'], ...auditLog.map((entry) => [entry.timestamp, entry.student, entry.previous_score, entry.score, entry.source, entry.evidence])];
  downloadFile(rows.map((row) => row.map(quote).join(',')).join('\n'), `voice-grading-audit-${Date.now()}.csv`, 'text/csv');
}

export { downloadFile };