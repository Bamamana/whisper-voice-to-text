const NICKNAMES = { ally: 'allison', andy: 'andrew', ben: 'benjamin', beth: 'elizabeth', bob: 'robert', charlie: 'charles', chris: 'christopher', dan: 'daniel', danny: 'daniel', jen: 'jennifer', joe: 'joseph', jon: 'jonathan', liz: 'elizabeth', maggie: 'margaret', matt: 'matthew', mike: 'michael', nate: 'nathan', nick: 'nicholas', rob: 'robert', sam: 'samuel', tom: 'thomas', tony: 'anthony', will: 'william', zach: 'zachary' };
const NUMBER_WORDS = { zero: 0, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10, eleven: 11, twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15, sixteen: 16, seventeen: 17, eighteen: 18, nineteen: 19, twenty: 20, thirty: 30, forty: 40, fifty: 50, sixty: 60, seventy: 70, eighty: 80, ninety: 90, hundred: 100 };
const WHOLE_CLASS = /^(?:overall|the class|as a class|everyone|everybody|most of (?:you|the class)|many of you|a lot of you|in general)\b/i;

function normalized(value) { return String(value || '').toLowerCase().replace(/[^a-z0-9]/g, ''); }
function tokens(value) { return String(value || '').toLowerCase().replace(/[^a-z0-9]/g, ' ').split(/\s+/).filter(Boolean); }

function variants(studentName) {
  const value = String(studentName || '').trim();
  const [lastPart, firstPart] = value.includes(',') ? value.split(',', 2).map((part) => part.trim()) : ['', value];
  const first = tokens(firstPart)[0] || '';
  const last = tokens(lastPart)[0] || tokens(firstPart).slice(-1)[0] || '';
  return [...new Set([value, `${firstPart} ${lastPart}`.trim(), `${lastPart} ${firstPart}`.trim(), first, last].filter(Boolean))];
}

function phonetic(value) {
  const input = normalized(value);
  const groups = { b: '1', f: '1', p: '1', v: '1', c: '2', g: '2', j: '2', k: '2', q: '2', s: '2', x: '2', z: '2', d: '3', t: '3', l: '4', m: '5', n: '5', r: '6' };
  let output = ''; let previous = '';
  for (const character of input) {
    if ('aeiouhwy'.includes(character)) continue;
    const code = groups[character] || character;
    if (code !== previous) output += code;
    previous = code;
  }
  return output.slice(0, 4);
}

function editSimilarity(left, right) {
  if (!left || !right) return 0;
  const matrix = Array.from({ length: right.length + 1 }, (_, index) => [index]);
  for (let index = 0; index <= left.length; index += 1) matrix[0][index] = index;
  for (let row = 1; row <= right.length; row += 1) for (let column = 1; column <= left.length; column += 1) matrix[row][column] = Math.min(matrix[row - 1][column] + 1, matrix[row][column - 1] + 1, matrix[row - 1][column - 1] + (right[row - 1] === left[column - 1] ? 0 : 1));
  return 1 - (matrix[right.length][left.length] / Math.max(left.length, right.length));
}

function parseNumberWords(value) {
  const words = tokens(value);
  if (!words.length || words.some((word) => !(word in NUMBER_WORDS))) return null;
  let current = 0;
  words.forEach((word) => { current = word === 'hundred' ? Math.max(current, 1) * 100 : current + NUMBER_WORDS[word]; });
  return current;
}

function scoreAndNotes(rest) {
  const numeric = [...rest.matchAll(/(\d+(?:\.\d+)?)\s*(?:\/|out of)\s*(\d+(?:\.\d+)?)/gi)];
  if (numeric.length) {
    let selected = numeric[0];
    for (const candidate of numeric.slice(1)) if (/(?:no|actually|i mean|sorry|rather|change that to|make that|wait|scratch that|oops)\b/i.test(rest.slice(selected.index + selected[0].length, candidate.index))) selected = candidate;
    return { score: `${selected[1]}/${selected[2]}`, notes: rest.slice(selected.index + selected[0].length).replace(/^[\s.,;-]+/, '').trim() };
  }
  const word = /((?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|\s|-)+?)\s+out of\s+((?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|\s|-)+)/i.exec(rest);
  if (word) {
    const earned = parseNumberWords(word[1]); const possible = parseNumberWords(word[2]);
    if (earned !== null && possible !== null) return { score: `${earned}/${possible}`, notes: rest.slice(word.index + word[0].length).trim() };
  }
  const bare = /^\s*(\d+(?:\.\d+)?)\b\s*(.*)$/.exec(rest);
  return bare ? { score: bare[1], notes: bare[2].replace(/^[\s.,;-]+/, '').trim() } : null;
}

function candidateFor(spokenName, studentNames) {
  const spoken = normalized(spokenName); const spokenTokens = tokens(spokenName);
  if (spoken.length < 3) return null;
  const exact = studentNames.filter((student) => variants(student).some((name) => normalized(name) === spoken));
  if (exact.length === 1) return { studentName: exact[0], confidence: 'High (exact match)' };
  if (exact.length > 1) return null;
  if (spokenTokens.length === 2 && spokenTokens.some((token) => token.length === 1)) {
    const [initial] = spokenTokens.filter((token) => token.length === 1);
    const longToken = spokenTokens.find((token) => token.length >= 3);
    const initialMatches = studentNames.filter((studentName) => variants(studentName).some((name) => {
      const nameTokens = tokens(name);
      return nameTokens.some((token) => token[0] === initial) && nameTokens.some((token) => token === longToken || (token.length >= 3 && editSimilarity(longToken, token) >= 0.75) || (token.length >= 3 && phonetic(longToken) === phonetic(token)));
    }));
    if (longToken && initialMatches.length === 1) return { studentName: initialMatches[0], confidence: 'High (name and initial match)' };
  }
  const canonical = spokenTokens.map((token) => NICKNAMES[token] || token);
  const candidates = studentNames.map((studentName) => {
    const nameVariants = variants(studentName);
    const studentTokens = new Set(nameVariants.flatMap(tokens).map((token) => NICKNAMES[token] || token));
    const spokenCodes = spokenTokens.map(phonetic).filter(Boolean);
    return { studentName, tokenMatch: canonical.every((token) => studentTokens.has(token)), phoneticMatch: spokenTokens.length > 1 && nameVariants.some((name) => { const codes = new Set(tokens(name).map(phonetic)); return spokenCodes.every((code) => codes.has(code)); }), similarity: Math.max(...nameVariants.map((name) => editSimilarity(spoken, normalized(name)))) };
  });
  const strong = candidates.filter((candidate) => candidate.tokenMatch || candidate.phoneticMatch);
  if (strong.length === 1) return { studentName: strong[0].studentName, confidence: strong[0].tokenMatch ? 'High (unique name variant)' : 'Medium (unique phonetic match)' };
  if (strong.length > 1) return null;
  candidates.sort((left, right) => right.similarity - left.similarity);
  const [best, second] = candidates;
  if (best && best.similarity >= 0.80 && (!second || best.similarity - second.similarity >= 0.15)) return { studentName: best.studentName, confidence: `Medium (unique fuzzy match ${best.similarity.toFixed(2)})` };
  return null;
}

function extractAction(unit, studentNames) {
  if (WHOLE_CLASS.test(unit)) return null;
  const match = /^(.+?)(?:,?\s+(?:you\s+)?(?:gets?|got|has|earned|earns|receiv(?:e|es|ed)|scored?|score|was|is)\s+)(.+)$/i.exec(unit) || /^(.+?)(?:,?\s+)(\d+(?:\.\d+)?\s*(?:\/|out of)\s*\d+(?:\.\d+)?\b.*)$/i.exec(unit);
  if (!match) return null;
  const score = scoreAndNotes(match[2]); const candidate = score && candidateFor(match[1].trim(), studentNames);
  return candidate ? { student_name: candidate.studentName, score: score.score, notes: score.notes, evidence: unit, confidence: candidate.confidence } : null;
}

export function matchClearGrades(transcript, studentNames) {
  const actions = []; const unresolved = []; const matchedNames = new Set();
  transcript.replace(/\r?\n/g, '. ').split(/(?<=[.!?])\s+/).map((unit) => unit.trim()).filter(Boolean).forEach((unit) => {
    const action = extractAction(unit, studentNames.filter((name) => !matchedNames.has(name)));
    if (action) { actions.push(action); matchedNames.add(action.student_name); } else unresolved.push(unit);
  });
  return { actions, unresolved, matchedNames };
}

export function remainingStudents(studentNames, matchedNames) { return studentNames.filter((studentName) => !matchedNames.has(studentName)); }