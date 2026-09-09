function normalize(value) {
  return String(value || '').toLowerCase().replace(/[^a-z0-9]/g, '');
}

function nameTokens(value) {
  return String(value || '').toLowerCase().replace(/[^a-z0-9]/g, ' ').split(/\s+/).filter((token) => token.length > 1);
}

function similarity(left, right) {
  if (!left || !right) return 0;
  const matrix = Array.from({ length: right.length + 1 }, (_, index) => [index]);
  for (let index = 0; index <= left.length; index += 1) matrix[0][index] = index;
  for (let row = 1; row <= right.length; row += 1) {
    for (let column = 1; column <= left.length; column += 1) {
      matrix[row][column] = Math.min(
        matrix[row - 1][column] + 1,
        matrix[row][column - 1] + 1,
        matrix[row - 1][column - 1] + (right[row - 1] === left[column - 1] ? 0 : 1)
      );
    }
  }
  return 1 - matrix[right.length][left.length] / Math.max(left.length, right.length);
}

function spokenName(note) {
  const match = /^(?:change|update|correct)\s+(.+?)\s+(?:to|as)\s+.+$|^(.+?)(?:,?\s+(?:you\s+)?(?:gets?|got|has|earned|earns|receiv(?:e|es|ed)|scored?|score|was|is)\s+).+$/i.exec(note);
  return (match?.[1] || match?.[2] || note.split(/[,.:;!?]/, 1)[0]).trim();
}

export function unresolvedCandidates(note, studentNames, limit = 3) {
  const spoken = normalize(spokenName(note));
  const tokens = nameTokens(spokenName(note));
  return studentNames.map((studentName) => {
    const candidate = normalize(studentName);
    const candidateTokens = nameTokens(studentName);
    const tokenMatches = tokens.filter((token) => candidateTokens.some((candidateToken) => candidateToken.includes(token) || token.includes(candidateToken))).length;
    return { studentName, score: tokenMatches * 2 + similarity(spoken, candidate) };
  }).sort((left, right) => right.score - left.score || left.studentName.localeCompare(right.studentName)).slice(0, limit);
}

export function unresolvedGrade(note) {
  const fraction = /(\d+(?:\.\d+)?)\s*(?:\/|out of)\s*(\d+(?:\.\d+)?)/i.exec(note);
  if (fraction) return `${fraction[1]}/${fraction[2]}`;
  const namedScore = /(?:gets?|got|has|earned|earns|receiv(?:e|es|ed)|scored?|score|was|is)\s+(\d+(?:\.\d+)?)(?:\b|$)/i.exec(note);
  return namedScore ? namedScore[1] : '';
}