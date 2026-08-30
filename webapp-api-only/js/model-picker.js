// Dynamic model picker modal (pattern from Visual Planner ai-model-catalog.js).

let dialog = null;

function ensureDialog() {
  if (dialog) return dialog;
  const root = document.createElement('div');
  root.className = 'fixed inset-0 z-[140] hidden items-center justify-center bg-slate-900/60 p-4 backdrop-blur-sm';
  root.append(document.createRange().createContextualFragment(`
    <div class="w-full max-w-md rounded-xl border border-slate-700 bg-slate-800 shadow-2xl" role="dialog" aria-modal="true">
      <div class="border-b border-slate-700 px-5 py-4">
        <h3 class="text-base font-bold text-slate-100">Choose Whisper model</h3>
        <p class="mt-1 text-xs text-slate-400">Models are loaded live from the selected provider.</p>
      </div>
      <div class="space-y-4 p-5">
        <div data-role="status" class="text-xs text-slate-400">Loading models...</div>
        <label class="block text-xs font-bold uppercase text-slate-400">Model
          <select data-role="model" class="mt-1 block w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm font-semibold text-slate-100"></select>
        </label>
        <p data-role="error" class="hidden text-xs font-semibold text-rose-400"></p>
      </div>
      <div class="flex justify-end gap-2 border-t border-slate-700 px-5 py-3">
        <button type="button" data-role="cancel" class="rounded-lg px-3 py-1.5 text-sm font-semibold text-slate-300 hover:bg-slate-700">Cancel</button>
        <button type="button" data-role="confirm" class="rounded-lg bg-brand-600 px-4 py-1.5 text-sm font-bold text-white hover:bg-brand-700">Use model</button>
      </div>
    </div>`));
  document.body.appendChild(root);
  dialog = {
    root,
    status: root.querySelector('[data-role="status"]'),
    model: root.querySelector('[data-role="model"]'),
    error: root.querySelector('[data-role="error"]'),
    cancel: root.querySelector('[data-role="cancel"]'),
    confirm: root.querySelector('[data-role="confirm"]')
  };
  return dialog;
}

// fetchModels: async () => [{ id, label }]
export async function promptForModel(fetchModels, selectedModel = '') {
  const elements = ensureDialog();
  elements.status.textContent = 'Loading models...';
  elements.status.classList.remove('hidden');
  elements.model.replaceChildren();
  elements.model.classList.add('hidden');
  elements.error.classList.add('hidden');
  elements.root.classList.remove('hidden');
  elements.root.classList.add('flex');

  let models = [];
  try {
    models = await fetchModels();
  } catch (error) {
    elements.status.classList.add('hidden');
    elements.error.textContent = error.message;
    elements.error.classList.remove('hidden');
  }

  if (models.length > 0) {
    elements.status.classList.add('hidden');
    elements.model.classList.remove('hidden');
    elements.model.replaceChildren(...models.map((model) => new Option(model.label || model.id, model.id)));
    const preferred = models.find((model) => model.id === selectedModel)?.id || models[0].id;
    elements.model.value = preferred;
  } else if (!elements.error.textContent) {
    elements.status.textContent = 'No models found for this provider.';
  }

  return new Promise((resolve) => {
    const finish = (value) => {
      elements.root.classList.add('hidden');
      elements.root.classList.remove('flex');
      elements.cancel.onclick = null;
      elements.confirm.onclick = null;
      resolve(value);
    };
    elements.cancel.onclick = () => finish(null);
    elements.confirm.onclick = () => {
      if (!elements.model.value) return;
      finish({ model: elements.model.value });
    };
  });
}
