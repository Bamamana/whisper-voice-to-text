export function recordAudit(auditLog, action, source, previousScore = '') {
  auditLog.push({ timestamp: new Date().toISOString(), student: action.student_name, previous_score: previousScore, score: action.score, source, evidence: action.evidence || '' });
}

export function scoreIssue(canvasGradebook, assignmentHeader, score) {
  const maximum = Number.parseFloat(canvasGradebook?.assignments.find((assignment) => assignment.header === assignmentHeader)?.pointsPossible);
  const value = String(score || '').trim();
  if (!value || !Number.isFinite(maximum)) return '';
  const slash = value.match(/^(\d+(?:\.\d+)?)\s*(?:\/|out of)\s*(\d+(?:\.\d+)?)$/i);
  const earned = Number.parseFloat(slash ? slash[1] : value);
  const possible = slash ? Number.parseFloat(slash[2]) : maximum;
  return !Number.isFinite(earned) || !Number.isFinite(possible) || earned < 0 || possible <= 0 || (earned / possible) * maximum > maximum ? `Score must be between 0 and ${maximum} points.` : '';
}

export function updateProgress(progressElement, total, graded) {
  progressElement.textContent = total ? `${graded} of ${total} graded` : '0 graded';
}