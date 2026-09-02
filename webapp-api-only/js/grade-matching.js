function normalized(value) {
  return String(value || '').toLowerCase().replace(/[^a-z0-9]/g, '');
}

function escapePattern(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function scoreFromUnit(unit) {
  const score = unit.match(/\b(\d+(?:\.\d+)?)\s*(?:\/|out of)\s*(\d+(?:\.\d+)?)\b/i);
  return score ? `${score[1]}/${score[2]}` : '';
}

function transcriptUnits(transcript) {
  return transcript.split(/(?:\r?\n|(?<=[.!?])\s+)/).map((unit) => unit.trim()).filter(Boolean);
}

export function matchClearGrades(transcript, studentNames) {
  const actions = [];
  const unresolved = [];
  const matchedNames = new Set();
  const studentPatterns = studentNames.map((studentName) => ({
    studentName,
    pattern: new RegExp(`\\b${escapePattern(studentName).replace(/\\,\\s*/g, '\\s*,?\\s*')}\\b`, 'i')
  }));

  transcriptUnits(transcript).forEach((unit) => {
    const score = scoreFromUnit(unit);
    const matches = studentPatterns.filter(({ pattern }) => pattern.test(unit));
    if (score && matches.length === 1 && !matchedNames.has(matches[0].studentName)) {
      const studentName = matches[0].studentName;
      actions.push({
        student_name: studentName,
        score,
        notes: '',
        evidence: unit,
        confidence: 'High (local exact match)'
      });
      matchedNames.add(studentName);
    } else {
      unresolved.push(unit);
    }
  });

  return { actions, unresolved, matchedNames };
}

export function remainingStudents(studentNames, matchedNames) {
  return studentNames.filter((studentName) => !matchedNames.has(studentName));
}