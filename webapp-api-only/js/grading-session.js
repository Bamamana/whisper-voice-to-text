const GRADE_SESSION_KEY = 'wv1api_grading_session';

export function loadGradeSession() {
  try {
    return JSON.parse(localStorage.getItem(GRADE_SESSION_KEY) || 'null');
  } catch (_error) {
    return null;
  }
}

export function saveGradeSession(session) {
  localStorage.setItem(GRADE_SESSION_KEY, JSON.stringify(session));
}

export function clearGradeSession() {
  localStorage.removeItem(GRADE_SESSION_KEY);
}