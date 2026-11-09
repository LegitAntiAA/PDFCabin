'use strict';

// All traffic goes to the serving origin, or the explicitly configured local API.
function readPreference(key, fallback = '') {
  try { return localStorage.getItem(key) ?? fallback; } catch { return fallback; }
}
function savePreference(key, value) {
  try { localStorage.setItem(key, value); } catch { /* Private/file contexts may disable storage. */ }
}
const LOCAL_API_ORIGIN = ['http:', '', 'localhost:8420'].join('/');
const API_BASE = location.protocol.startsWith('http')
  ? '' : (readPreference('pdfcabin_api_base') || LOCAL_API_ORIGIN).replace(/\/+$/, '');

const I18N = {
  en: {
    skip: 'Skip to your files', workspace: 'YOUR DOCUMENT WORKSPACE', localWorkspace: 'Local workspace',
    search: 'Search document text', searchLabel: 'Search document text', searchHint: 'Search the text inside your PDFs',
    language: 'Switch to Russian', theme: 'Switch to light theme', themeDark: 'Switch to dark theme',
    token: 'Server access token', donate: 'Support PDFCabin', chooseFiles: 'Choose PDFs', choose: 'Choose PDFs',
    dropTitle: 'Drop PDFs here', dropHint: 'Add one or more PDF files.', dropOr: 'or', uploadHint: 'PDF files · multiple files welcome',
    library: 'Your files', filesTitle: 'Your files', allFiles: 'All files', scanned: 'Scanned', searchable: 'Searchable',
    filterAll: 'All files', filterScanned: 'Scanned', filterText: 'Searchable', filters: 'Filter files',
    sort: 'Sort files', sortRecent: 'Recently modified', sortName: 'Name A–Z', sortSize: 'Largest first',
    refresh: 'Refresh files', selectAll: 'Select all visible files', loading: 'Loading your files…',
    emptyTitle: 'Drop PDFs here', emptyText: 'Add your first PDF to merge, compress, or recognize its text.',
    emptyHint: 'Your files will appear here.', noFiltered: 'No files in this view.', noFilteredHint: 'Choose another filter to see your files.',
    offline: 'Cannot reach the server.', offlineHint: 'Start PDFCabin, then try again.', retry: 'Try again',
    connection: 'Checking server…', connected: 'Server connected', disconnected: 'Server unavailable',
    serverConnected: 'Server connected', serverUnavailable: 'Server unavailable', index: 'Pages indexed: {count}',
    indexUnavailable: 'Search index unavailable', indexWaiting: 'Search index loading…', version: 'Version {version}',
    jobs: 'Tasks', jobsTitle: 'Tasks', jobsHint: 'OCR runs on your server.', closeJobs: 'Close tasks',
    noJobs: 'No tasks yet.', noJobsHint: 'OCR tasks will appear here.', activeJobs: '{count} active',
    selected: '{count} selected', clearSelection: 'Clear selection', merge: 'Merge PDFs', compress: 'Compress',
    ocr: 'Run OCR', delete: 'Move to trash', mergeHint: 'Select at least 2 PDFs to merge.',
    download: 'Download PDF', more: 'More actions for {name}', selectFile: 'Select {name}',
    split: 'Split PDF', rotate: 'Rotate pages', deletePages: 'Delete pages', info: 'File details', extract: 'Extract text',
    ocrBadge: 'OCR ✓', scannedBadge: 'SCANNED', unknownPages: 'Pages unavailable', previewUnavailable: 'Preview unavailable',
    preview: 'First page of {name}', files_one: '{count} file', files_other: '{count} files',
    pages_one: '{count} page', pages_other: '{count} pages', close: 'Close', cancel: 'Cancel', done: 'Done',
    save: 'Save PDF', output: 'Output filename', outputHint: 'A new PDF is saved alongside your files.',
    pages: 'Pages', pagesHint: 'Use 1-3,5,8- to select pages. A trailing dash means to the end.',
    invalidPages: 'Enter valid page numbers, for example 1-3,5,8-.', invalidOutput: 'Enter a relative filename ending in .pdf.',
    overwrite: 'Replace existing output files', overwriteHint: 'Only files with the same output names will be replaced.',
    conflictTitle: 'A file with this name exists.', conflictHint: 'Enable replacement, then run the operation again.',
    replace: 'Replace files', uploadConflictHint: 'Existing files with these names will be replaced by this upload.',
    notPdf: 'Not a PDF: {name}', uploadBusy: 'An upload is already in progress.',
    uploading: 'Uploading PDFs: {count}…', uploadProcessing: 'Saving your PDFs…', uploaded: 'Files added: {count}.',
    uploadProgress: 'Upload progress', networkError: 'Cannot reach the server. Check that PDFCabin is running.',
    requestError: 'Request failed ({status}).', authRequired: 'This server requires a token.',
    tokenHint: 'The token is saved in this browser and sent only to your PDFCabin server.',
    tokenPlaceholder: 'Enter your server token', connect: 'Connect', tokenSaved: 'Token saved.',
    invalidToken: 'The token was not accepted. Check it and try again.',
    mergeTitle: 'Merge PDFs', mergeDescription: 'Files will be joined in this order.',
    moveUp: 'Move {name} up', moveDown: 'Move {name} down',
    splitTitle: 'Split PDF', splitDescription: 'Save selected page ranges or split every N pages.',
    splitMode: 'Split by', ranges: 'Page ranges', everyN: 'Every N pages', splitValue: 'Page ranges',
    splitEvery: 'Pages per file', outputDir: 'Output folder (optional)', outputDirHint: 'Leave empty to use the source folder.',
    invalidEvery: 'Enter a whole number between 1 and {max}.',
    rotateTitle: 'Rotate pages', angle: 'Rotation clockwise',
    deletePagesTitle: 'Delete pages', deletePagesDescription: 'Save a copy with the selected pages removed.',
    cannotDeleteAll: 'Keep at least one page in the PDF.',
    compressTitle: 'Compress PDFs', compressDescription: 'Choose how to reduce the file size.',
    fast: 'Fast', fastHint: 'Optimize the PDF structure without downsampling images.',
    strong: 'Strong', strongHint: 'Downsample images to 150 dpi. Best for large scans.',
    strongUnavailable: 'Strong compression is unavailable on this server.',
    compressionSummary: '{before} → {after}', smaller: '{percent}% smaller', larger: '{percent}% larger', sameSize: 'Size unchanged',
    ocrTitle: 'Recognize text', ocrDescription: 'Add a searchable text layer to scanned pages.',
    languages: 'Recognition languages', lang_rus: 'Russian', lang_eng: 'English',
    force: 'Redo the existing text layer', existingText: 'Some selected PDFs already contain text. Enable redo to process them again.',
    chooseLanguage: 'Select at least one recognition language.', noLanguages: 'No OCR languages are available on this server.',
    ocrQueued: 'OCR tasks queued: {count}.', queued: 'Queued', running: 'Recognizing text…', completed: 'Completed', failed: 'Failed',
    ocrDone: 'Text recognized: {name}', jobMissing: 'This task is no longer available.',
    deleteTitle: 'Move files to trash?', deleteDescription: 'The server will move these files into its trash folder.',
    deleted: 'Files moved to trash: {count}.', created: 'Saved {name}', createdMany: 'PDFs saved: {count}.',
    partiallyCompleted: 'Files processed: {count}. The remaining files are still selected for this operation.',
    partiallyQueued: 'OCR tasks queued: {count}. The remaining files have not been queued.',
    processing: 'Working…', sourceFiles: 'Selected PDFs', fileName: 'Filename', filePath: 'Path', fileSize: 'File size',
    pageCount: 'Pages', encrypted: 'Encrypted', title: 'Title', author: 'Author', createdAt: 'Created', yes: 'Yes', no: 'No', unspecified: 'Not set',
    extractTitle: 'Extract text', extractHint: 'Leave pages empty to read the entire PDF.', extractAction: 'Extract text',
    extractedPage: 'Page {page}', noText: 'No text was found. Run OCR if this is a scanned PDF.',
    copyText: 'Copy text', copiedText: 'Text copied.', copyAddress: 'Copy address', addressCopied: 'Address copied.',
    copyFailed: 'Copy was unavailable. Select the text and copy it manually.',
    donateDescription: 'If PDFCabin saves you time, you can support its development.',
    searchLoading: 'Searching…', searchEmpty: 'No matches found.', searchHelp: 'Search uses exact word forms. Run OCR to add scanned text to the index.',
    searchPage: 'Page {page}', searchResults: 'Search results', searchResultLabel: 'Download {name}, match on page {page}',
    downloadStarted: 'Download started.', lockNotice: 'Authentication required', viewAll: 'Show all files',
    localOnly: 'Your documents stay on your infrastructure.', privacyLabel: 'Stored on your server',
    keyboardHint: 'Press / to search', uploadLabel: 'Upload PDF files', libraryEyebrow: 'THE WORKBENCH', selectedActions: 'Actions for selected files',
  },
  ru: {
    skip: 'Перейти к файлам', workspace: 'ВАША МАСТЕРСКАЯ ДОКУМЕНТОВ', localWorkspace: 'Локальное пространство',
    search: 'Поиск по тексту документов', searchLabel: 'Поиск по тексту документов', searchHint: 'Найти текст внутри ваших PDF',
    language: 'Переключить на английский', theme: 'Включить светлую тему', themeDark: 'Включить тёмную тему',
    token: 'Токен доступа к серверу', donate: 'Поддержать PDFCabin', chooseFiles: 'Выбрать PDF', choose: 'Выбрать PDF',
    dropTitle: 'Перетащите PDF сюда', dropHint: 'Добавьте один или несколько PDF-файлов.', dropOr: 'или', uploadHint: 'PDF-файлы · можно сразу несколько',
    library: 'Ваши файлы', filesTitle: 'Ваши файлы', allFiles: 'Все файлы', scanned: 'Сканы', searchable: 'С текстом',
    filterAll: 'Все файлы', filterScanned: 'Сканы', filterText: 'С текстом', filters: 'Фильтр файлов',
    sort: 'Сортировка файлов', sortRecent: 'Сначала изменённые', sortName: 'По имени', sortSize: 'Сначала большие',
    refresh: 'Обновить файлы', selectAll: 'Выбрать все видимые файлы', loading: 'Загружаем ваши файлы…',
    emptyTitle: 'Перетащите PDF сюда', emptyText: 'Добавьте PDF, чтобы объединить, сжать или распознать его текст.',
    emptyHint: 'Здесь появятся ваши файлы.', noFiltered: 'Здесь пока нет файлов.', noFilteredHint: 'Выберите другой фильтр.',
    offline: 'Не удалось подключиться к серверу.', offlineHint: 'Запустите PDFCabin и повторите попытку.', retry: 'Повторить',
    connection: 'Проверяем сервер…', connected: 'Сервер подключён', disconnected: 'Сервер недоступен',
    serverConnected: 'Сервер подключён', serverUnavailable: 'Сервер недоступен', index: 'В индексе страниц: {count}',
    indexUnavailable: 'Поисковый индекс недоступен', indexWaiting: 'Загружаем поисковый индекс…', version: 'Версия {version}',
    jobs: 'Задачи', jobsTitle: 'Задачи', jobsHint: 'Текст распознаётся на вашем сервере.', closeJobs: 'Закрыть задачи',
    noJobs: 'Задач пока нет.', noJobsHint: 'Здесь появятся задачи распознавания.', activeJobs: 'Активных: {count}',
    selected: 'Выбрано: {count}', clearSelection: 'Снять выделение', merge: 'Объединить PDF', compress: 'Сжать',
    ocr: 'Распознать', delete: 'В корзину', mergeHint: 'Выберите минимум 2 PDF для объединения.',
    download: 'Скачать PDF', more: 'Действия с {name}', selectFile: 'Выбрать {name}',
    split: 'Разделить PDF', rotate: 'Повернуть страницы', deletePages: 'Удалить страницы', info: 'Сведения о файле', extract: 'Извлечь текст',
    ocrBadge: 'OCR ✓', scannedBadge: 'СКАН', unknownPages: 'Страницы недоступны', previewUnavailable: 'Превью недоступно',
    preview: 'Первая страница {name}', files_one: '{count} файл', files_few: '{count} файла', files_many: '{count} файлов', files_other: '{count} файла',
    pages_one: '{count} страница', pages_few: '{count} страницы', pages_many: '{count} страниц', pages_other: '{count} страницы',
    close: 'Закрыть', cancel: 'Отмена', done: 'Готово', save: 'Сохранить PDF', output: 'Имя нового файла',
    outputHint: 'Новый PDF сохранится рядом с вашими файлами.', pages: 'Страницы',
    pagesHint: 'Формат: 1-3,5,8-. Дефис в конце — до последней страницы.',
    invalidPages: 'Укажите допустимые страницы, например 1-3,5,8-.', invalidOutput: 'Укажите относительное имя файла с расширением .pdf.',
    overwrite: 'Заменить существующие файлы результата', overwriteHint: 'Заменятся только файлы с совпадающими выходными именами.',
    conflictTitle: 'Файл с таким именем уже существует.', conflictHint: 'Разрешите замену и повторите операцию.',
    replace: 'Заменить файлы', uploadConflictHint: 'Файлы с этими именами будут заменены загружаемыми.',
    notPdf: 'Это не PDF: {name}', uploadBusy: 'Загрузка уже выполняется.',
    uploading: 'Загружаем файлы: {count}…', uploadProcessing: 'Сохраняем ваши PDF…', uploaded: 'Добавлено файлов: {count}.',
    uploadProgress: 'Загрузка файлов', networkError: 'Не удалось подключиться к серверу. Проверьте, запущен ли PDFCabin.',
    requestError: 'Ошибка запроса ({status}).', authRequired: 'Для доступа к серверу нужен токен.',
    tokenHint: 'Токен сохраняется в этом браузере и отправляется только вашему серверу PDFCabin.',
    tokenPlaceholder: 'Введите токен сервера', connect: 'Подключиться', tokenSaved: 'Токен сохранён.',
    invalidToken: 'Сервер не принял токен. Проверьте его и повторите попытку.',
    mergeTitle: 'Объединить PDF', mergeDescription: 'Файлы будут объединены в этом порядке.',
    moveUp: 'Переместить {name} выше', moveDown: 'Переместить {name} ниже',
    splitTitle: 'Разделить PDF', splitDescription: 'Сохраните выбранные диапазоны или разделите PDF каждые N страниц.',
    splitMode: 'Способ разделения', ranges: 'По диапазонам', everyN: 'Каждые N страниц', splitValue: 'Диапазоны страниц',
    splitEvery: 'Страниц в одном файле', outputDir: 'Папка результата (необязательно)', outputDirHint: 'Оставьте пустым, чтобы сохранить в папке исходного файла.',
    invalidEvery: 'Введите целое число от 1 до {max}.', rotateTitle: 'Повернуть страницы', angle: 'Поворот по часовой стрелке',
    deletePagesTitle: 'Удалить страницы', deletePagesDescription: 'Сохраните копию без выбранных страниц.',
    cannotDeleteAll: 'В PDF должна остаться хотя бы одна страница.',
    compressTitle: 'Сжать PDF', compressDescription: 'Выберите способ уменьшения файла.',
    fast: 'Быстрое', fastHint: 'Оптимизация структуры PDF без уменьшения разрешения изображений.',
    strong: 'Сильное', strongHint: 'Уменьшение разрешения изображений до 150 dpi. Подходит для больших сканов.',
    strongUnavailable: 'Сильное сжатие недоступно на этом сервере.',
    compressionSummary: '{before} → {after}', smaller: 'Меньше на {percent}%', larger: 'Больше на {percent}%', sameSize: 'Размер не изменился',
    ocrTitle: 'Распознать текст', ocrDescription: 'Добавьте текстовый слой для поиска по сканам.',
    languages: 'Языки распознавания', lang_rus: 'Русский', lang_eng: 'Английский', force: 'Распознать существующий текстовый слой заново',
    existingText: 'В некоторых выбранных PDF уже есть текст. Для повторной обработки включите распознавание заново.',
    chooseLanguage: 'Выберите хотя бы один язык распознавания.', noLanguages: 'На сервере нет доступных языков OCR.',
    ocrQueued: 'В очередь добавлено задач: {count}.', queued: 'В очереди', running: 'Распознаём текст…', completed: 'Завершено', failed: 'Ошибка',
    ocrDone: 'Текст распознан: {name}', jobMissing: 'Эта задача больше недоступна.',
    deleteTitle: 'Переместить файлы в корзину?', deleteDescription: 'Сервер перенесёт эти файлы в свою папку trash.',
    deleted: 'Перемещено в корзину: {count}.', created: 'Сохранён {name}', createdMany: 'Сохранено PDF: {count}.',
    partiallyCompleted: 'Обработано файлов: {count}. В этой операции остались только необработанные файлы.',
    partiallyQueued: 'В очередь добавлено задач: {count}. Остальные файлы ещё не добавлены.',
    processing: 'Обрабатываем…', sourceFiles: 'Выбранные PDF', fileName: 'Имя файла', filePath: 'Путь', fileSize: 'Размер файла',
    pageCount: 'Страницы', encrypted: 'Зашифрован', title: 'Название', author: 'Автор', createdAt: 'Создан', yes: 'Да', no: 'Нет', unspecified: 'Не указано',
    extractTitle: 'Извлечь текст', extractHint: 'Оставьте поле страниц пустым, чтобы прочитать весь PDF.', extractAction: 'Извлечь текст',
    extractedPage: 'Страница {page}', noText: 'Текст не найден. Если это скан, запустите распознавание.',
    copyText: 'Скопировать текст', copiedText: 'Текст скопирован.', copyAddress: 'Скопировать адрес', addressCopied: 'Адрес скопирован.',
    copyFailed: 'Скопировать не удалось. Выделите текст и скопируйте вручную.',
    donateDescription: 'Если PDFCabin экономит вам время, можно поддержать его разработку.',
    searchLoading: 'Ищем…', searchEmpty: 'Совпадений нет.', searchHelp: 'Поиск по точным словоформам. Для поиска по скану сначала распознайте текст.',
    searchPage: 'Страница {page}', searchResults: 'Результаты поиска', searchResultLabel: 'Скачать {name}, совпадение на странице {page}',
    downloadStarted: 'Скачивание началось.', lockNotice: 'Нужна авторизация', viewAll: 'Показать все файлы',
    localOnly: 'Your documents stay on your infrastructure.', privacyLabel: 'Хранятся на вашем сервере',
    keyboardHint: 'Нажмите / для поиска', uploadLabel: 'Загрузить PDF-файлы', libraryEyebrow: 'МАСТЕРСКАЯ', selectedActions: 'Действия с выбранными файлами',
  },
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const state = {
  lang: readPreference('pdfcabin_lang', 'en') === 'ru' ? 'ru' : 'en',
  theme: readPreference('pdfcabin_theme', 'dark') === 'light' ? 'light' : 'dark',
  token: readPreference('pdfcabin_token'), files: [], selected: new Set(), filter: 'all', sort: 'recent',
  health: null, stats: null, connected: false, loaded: false, loading: true, addresses: [],
  jobs: new Map(), uploadBusy: false, uploadCount: 0, uploadPhase: 'uploading', booting: false, drawerOpen: false,
  authRequired: false, lastError: '',
};
function t(key, values = {}) {
  return (I18N[state.lang][key] ?? I18N.en[key] ?? key).replace(/\{(\w+)\}/g, (_, k) => String(values[k] ?? ''));
}
function countLabel(type, count) {
  return t(`${type}_${new Intl.PluralRules(state.lang).select(count)}`, {count});
}
function escapeHTML(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[char]));
}
function formatSize(bytes) {
  if (!Number.isFinite(bytes)) return '—';
  const units = ['B', 'KB', 'MB', 'GB'];
  const index = Math.min(bytes > 0 ? Math.floor(Math.log(bytes) / Math.log(1024)) : 0, 3);
  return `${new Intl.NumberFormat(state.lang, {maximumFractionDigits: index > 0 ? 1 : 0}).format(bytes / 1024 ** index)} ${units[index]}`;
}
function baseName(path) { return String(path).split('/').pop(); }
function outputName(path, suffix) { return path.replace(/\.pdf$/i, '') + suffix + '.pdf'; }
function endpoint(path, params = {}) {
  const query = new URLSearchParams(params).toString();
  return API_BASE + path + (query ? `?${query}` : '');
}
const ICONS = {
  download: '<path d="M12 3v12m-4-4 4 4 4-4M5 16v4h14v-4"/>',
  more: '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>', check: '<path d="m5 12 4 4L19 6"/>',
  file: '<path d="M14 3H6v18h12V7l-4-4Zm0 0v5h4M9 12h6m-6 4h6"/>',
  split: '<path d="M8 3H4v18h4m8-18h4v18h-4M12 2v3m0 4v3m0 4v3m0 2v1"/>',
  rotate: '<path d="M3 10a9 9 0 1 1 3 9M3 4v6h6"/>',
  trash: '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v.1"/>',
  text: '<path d="M4 5h16M4 10h16M4 15h10M4 20h13"/>',
  up: '<path d="m6 14 6-6 6 6"/>', down: '<path d="m6 10 6 6 6-6"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',
  moon: '<path d="M20 14.2A8.5 8.5 0 0 1 9.8 4 8.5 8.5 0 1 0 20 14.2Z"/>',
  alert: '<path d="m12 3 10 18H2L12 3Zm0 6v5m0 3v.1"/>',
  copy: '<rect x="8" y="8" width="12" height="13" rx="2"/><path d="M16 8V3H3v13h5"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
};
function icon(name) {
  return `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ICONS.file}</svg>`;
}
function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function actionButton(label, iconName, className = 'icon-button') {
  const node = element('button', className);
  node.type = 'button'; node.setAttribute('aria-label', label); node.title = label;
  if (iconName) node.innerHTML = icon(iconName);
  return node;
}
function toast(message, kind = 'info') {
  const activeDialog = $('#auth-modal').open ? $('#auth-modal') : $('#modal').open ? $('#modal') : null;
  let host = activeDialog ? $('.modal-toasts', activeDialog) : $('#toasts');
  if (!host) {
    host = element('div', 'toasts modal-toasts'); host.setAttribute('aria-live', 'polite');
    activeDialog.append(host);
  }
  const node = element('div', `toast toast-${kind}`);
  node.setAttribute('role', kind === 'error' ? 'alert' : 'status');
  const symbol = element('span', 'toast-icon'); symbol.innerHTML = icon(kind === 'error' ? 'alert' : kind === 'success' ? 'check' : 'info');
  const close = actionButton(t('close'), 'close', 'icon-button toast-close');
  close.addEventListener('click', () => node.remove());
  node.append(symbol, element('span', 'toast-message', message), close);
  host.append(node);
  while (host.children.length > 4) host.firstElementChild.remove();
  setTimeout(() => node.remove(), kind === 'error' ? 12000 : 6000);
}

class ApiError extends Error {
  constructor(status, detail) { super(detail); this.status = status; }
}
class Cancelled extends Error {}
function errorDetail(body, status) {
  if (typeof body?.detail === 'string') return body.detail;
  if (Array.isArray(body?.detail)) return body.detail.map(item => item.msg).filter(Boolean).join('; ');
  return t(status === 401 ? 'invalidToken' : 'requestError', {status});
}
let authPromise = null;
function requestToken(tokenAtSend = null) {
  if (tokenAtSend !== null && state.token && state.token !== tokenAtSend) return Promise.resolve();
  if (authPromise) return authPromise;
  state.authRequired = true; renderStatus();
  $('#token-button').hidden = false;
  const dialog = $('#auth-modal');
  dialog.innerHTML = `<form class="modal-form"><div class="modal-header"><h2 id="auth-title">${t('token')}</h2>
    <button type="button" class="icon-button" data-auth-cancel aria-label="${t('close')}">${icon('close')}</button></div>
    <div class="modal-body"><p>${t('authRequired')}</p><label class="field"><span>${t('token')}</span>
    <input name="token" type="password" required autocomplete="off" spellcheck="false" placeholder="${t('tokenPlaceholder')}" autofocus></label>
    <p class="field-hint">${t('tokenHint')}</p></div><div class="modal-footer"><button type="button" class="button secondary" data-auth-cancel>${t('cancel')}</button>
    <button type="submit" class="button primary">${t('connect')}</button></div></form>`;
  dialog.setAttribute('aria-labelledby', 'auth-title');
  authPromise = new Promise((resolve, reject) => {
    let accepted = false;
    const cancel = () => dialog.close();
    $$('[data-auth-cancel]', dialog).forEach(button => button.addEventListener('click', cancel));
    $('form', dialog).addEventListener('submit', event => {
      event.preventDefault();
      const input = $('[name="token"]', dialog);
      const value = input.value.trim();
      if (!value) { input.focus(); return; }
      state.token = value; savePreference('pdfcabin_token', value); accepted = true; dialog.close();
    });
    dialog.addEventListener('close', () => {
      authPromise = null;
      if (accepted) resolve(); else reject(new Cancelled());
    }, {once: true});
    dialog.showModal();
  });
  return authPromise;
}
async function api(path, options = {}, retried = false) {
  const {params, json, responseType, ...fetchOptions} = options;
  const tokenAtSend = state.token;
  const headers = new Headers(fetchOptions.headers || {});
  if (tokenAtSend) headers.set('Authorization', `Bearer ${tokenAtSend}`);
  if (json !== undefined) headers.set('Content-Type', 'application/json');
  let response;
  try {
    response = await fetch(endpoint(path, params), {...fetchOptions, headers, ...(json !== undefined ? {body: JSON.stringify(json)} : {})});
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new ApiError(0, t('networkError'));
  }
  if (response.status === 401 && !retried) {
    await requestToken(tokenAtSend);
    return api(path, options, true);
  }
  if (!response.ok) {
    if (response.status === 401) $('#token-button').hidden = false;
    let body; try { body = await response.json(); } catch { body = null; }
    throw new ApiError(response.status, errorDetail(body, response.status));
  }
  if (state.authRequired) { state.authRequired = false; renderStatus(); }
  if (responseType === 'blob') return response.blob();
  return response.status === 204 ? null : response.json();
}
function showError(error) {
  if (error instanceof Cancelled || error.name === 'AbortError') return;
  if (error.status === 0 || error.status === 401) {
    state.connected = error.status === 401; state.authRequired = error.status === 401;
    state.lastError = error.message; renderStatus();
  }
  toast(error.message || t('requestError', {status: '—'}), 'error');
}
async function downloadPDF(path) {
  try {
    const blob = await api('/api/download', {params: {path}, responseType: 'blob'});
    const url = URL.createObjectURL(blob);
    const link = element('a'); link.href = url; link.download = baseName(path); document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch (error) { showError(error); }
}

function xhrUpload(files, overwrite, retried = false) {
  const tokenAtSend = state.token;
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', endpoint('/api/upload', {overwrite: String(overwrite)}));
    if (tokenAtSend) xhr.setRequestHeader('Authorization', `Bearer ${tokenAtSend}`);
    xhr.upload.onprogress = event => {
      const meter = $('#upload-meter');
      if (event.lengthComputable) {
        const percent = Math.round(event.loaded / event.total * 100);
        meter.value = percent; $('#upload-percent').textContent = `${percent}%`;
        if (percent === 100) { state.uploadPhase = 'uploadProcessing'; renderUploadLabel(); }
      } else { meter.removeAttribute('value'); $('#upload-percent').textContent = '…'; }
    };
    xhr.onload = async () => {
      let body; try { body = JSON.parse(xhr.responseText); } catch { body = null; }
      if (xhr.status === 401 && !retried) {
        try { await requestToken(tokenAtSend); resolve(await xhrUpload(files, overwrite, true)); } catch (error) { reject(error); }
      } else if (xhr.status >= 200 && xhr.status < 300) { state.authRequired = false; resolve(body); }
      else reject(new ApiError(xhr.status, errorDetail(body, xhr.status)));
    };
    xhr.onerror = () => reject(new ApiError(0, t('networkError')));
    xhr.onabort = () => reject(new Cancelled());
    const form = new FormData();
    for (const file of files) form.append('files', file, file.name);
    xhr.send(form);
  });
}
async function uploadFiles(files, overwrite = false) {
  files = [...files];
  if (!files.length) return;
  if (state.uploadBusy) { toast(t('uploadBusy')); return; }
  const invalid = files.find(file => !/\.pdf$/i.test(file.name));
  if (invalid) { toast(t('notPdf', {name: invalid.name}), 'error'); return; }
  state.uploadBusy = true; state.uploadCount = files.length; state.uploadPhase = 'uploading';
  $('#choose-files').disabled = true; $('#file-input').disabled = true;
  $('#dropzone').setAttribute('aria-disabled', 'true'); $('#upload-progress').hidden = false;
  renderUploadLabel(); $('#upload-meter').value = 0; $('#upload-percent').textContent = '0%';
  try {
    const result = await xhrUpload(files, overwrite);
    invalidateThumbnails((result.saved || []).map(file => file.path));
    toast(t('uploaded', {count: result.saved?.length || 0}), 'success');
    if (modalContext?.kind === 'uploadConflict') closeModal(true);
  } catch (error) {
    showError(error);
    if (error.status === 409) openModal('uploadConflict', [], {files, detail: error.message});
  } finally {
    state.uploadBusy = false; $('#choose-files').disabled = false; $('#file-input').disabled = false;
    $('#dropzone').removeAttribute('aria-disabled'); $('#upload-progress').hidden = true;
    await refreshFiles(); await refreshStats();
  }
}
function renderUploadLabel() {
  $('#upload-label').textContent = t(state.uploadPhase, {count: state.uploadCount});
}

const thumbCache = new Map();
let thumbnailActive = 0;
const thumbnailQueue = [];
function invalidateThumbnails(paths) {
  const changed = new Set(paths);
  for (const [key, entry] of thumbCache) {
    if (changed.has(entry.path)) {
      if (entry.url) URL.revokeObjectURL(entry.url);
      thumbCache.delete(key);
    }
  }
}
function thumbnail(file) {
  const key = `${file.path}#1`;
  const cached = thumbCache.get(key);
  if (cached && cached.mtime === file.mtime && cached.size === file.size) return cached.promise;
  if (cached) invalidateThumbnails([file.path]);
  const entry = {path: file.path, mtime: file.mtime, size: file.size};
  entry.promise = new Promise((resolve, reject) => {
    thumbnailQueue.push(async () => {
      try {
        const blob = await api('/api/file/thumb', {params: {path: file.path, page: 1}, responseType: 'blob'});
        const url = URL.createObjectURL(blob);
        if (thumbCache.get(key) !== entry) { URL.revokeObjectURL(url); throw new Cancelled(); }
        entry.url = url; resolve(url);
      } catch (error) {
        if (thumbCache.get(key) === entry) thumbCache.delete(key);
        reject(error);
      }
    });
  });
  thumbCache.set(key, entry); drainThumbnails(); return entry.promise;
}
function drainThumbnails() {
  while (thumbnailActive < 4 && thumbnailQueue.length) {
    thumbnailActive++;
    thumbnailQueue.shift()().finally(() => { thumbnailActive--; drainThumbnails(); });
  }
}
const thumbnailObserver = 'IntersectionObserver' in window ? new IntersectionObserver(entries => {
  entries.filter(entry => entry.isIntersecting).forEach(entry => {
    thumbnailObserver.unobserve(entry.target); loadCardThumbnail(entry.target);
  });
}, {rootMargin: '200px'}) : null;
function loadCardThumbnail(preview) {
  const file = state.files.find(item => item.path === preview.dataset.path);
  if (!file) return;
  thumbnail(file).then(url => {
    if (!preview.isConnected) return;
    const image = $('img', preview); image.src = url; image.hidden = false;
    $('.preview-placeholder', preview).hidden = true;
  }).catch(error => {
    if (!preview.isConnected || error instanceof Cancelled) return;
    const placeholder = $('.preview-placeholder', preview);
    placeholder.replaceChildren(element('span', '', t('previewUnavailable')));
    if (error.status === 401) $('#token-button').hidden = false;
  });
}
function visibleFiles() {
  return state.files.filter(file => state.filter === 'all' || (state.filter === 'text' ? file.has_text : !file.has_text))
    .sort((a, b) => {
      if (state.sort === 'name') return a.name.localeCompare(b.name, state.lang);
      const difference = state.sort === 'size' ? b.size - a.size : b.mtime - a.mtime;
      return difference || a.name.localeCompare(b.name, state.lang);
    });
}
function closeMenus() {
  $$('.file-menu').forEach(menu => { menu.hidden = true; });
  $$('.file-actions [aria-expanded]').forEach(button => button.setAttribute('aria-expanded', 'false'));
  $$('.file-card.menu-open').forEach(card => card.classList.remove('menu-open'));
}
function renderFiles() {
  const focused = document.activeElement;
  const focusedCard = focused?.closest('.file-card');
  const focusedPath = focusedCard?.dataset.path;
  const focusWasCheckbox = focused?.matches('input[type="checkbox"]');
  const focusWasDownload = focusedCard && focused === $('.file-actions button', focusedCard);
  thumbnailObserver?.disconnect();
  const grid = $('#file-grid'); grid.replaceChildren();
  const files = visibleFiles();
  $('#file-count').textContent = countLabel('files', state.files.length);
  $('#loading-state').hidden = !state.loading;
  $('#empty-state').hidden = state.loading || !state.loaded || files.length > 0;
  const emptyTitle = $('[data-i18n="emptyTitle"]');
  const emptyText = $('[data-i18n="emptyText"]');
  if (emptyTitle) emptyTitle.textContent = t(state.files.length ? 'noFiltered' : 'emptyTitle');
  if (emptyText) emptyText.textContent = t(state.files.length ? 'noFilteredHint' : 'emptyText');
  $('#dropzone').classList.toggle('has-files', state.files.length > 0);
  grid.hidden = state.loading || !files.length;
  for (const file of files) {
    const card = element('article', 'file-card'); card.dataset.path = file.path;
    const preview = element('div', 'file-preview'); preview.dataset.path = file.path;
    const image = element('img'); image.alt = t('preview', {name: file.name}); image.hidden = true; image.decoding = 'async';
    const placeholder = element('div', 'preview-placeholder'); placeholder.innerHTML = icon('file');
    const label = element('label', 'file-select');
    const checkbox = element('input'); checkbox.type = 'checkbox'; checkbox.checked = state.selected.has(file.path);
    checkbox.setAttribute('aria-label', t('selectFile', {name: file.name}));
    checkbox.addEventListener('change', () => {
      checkbox.checked ? state.selected.add(file.path) : state.selected.delete(file.path); renderSelection();
    });
    label.append(checkbox);
    const badge = element('span', `file-badge ${file.has_text ? 'badge-text' : 'badge-scanned'}`, t(file.has_text ? 'ocrBadge' : 'scannedBadge'));
    preview.append(placeholder, image, label, badge);
    const body = element('div', 'file-body');
    const name = element('h3', 'file-name', file.name); name.title = file.path;
    const meta = element('p', 'file-meta', `${file.pages === null ? t('unknownPages') : countLabel('pages', file.pages)} · ${formatSize(file.size)}`);
    body.append(name, meta);
    const actions = element('div', 'file-actions');
    const download = actionButton(t('download'), 'download'); download.addEventListener('click', () => downloadPDF(file.path));
    const more = actionButton(t('more', {name: file.name}), 'more'); more.setAttribute('aria-expanded', 'false'); more.setAttribute('aria-haspopup', 'menu');
    const menu = element('div', 'file-menu'); menu.hidden = true; menu.setAttribute('role', 'menu');
    for (const [kind, key, iconName] of [['split','split','split'], ['rotate','rotate','rotate'], ['deletePages','deletePages','trash'], ['info','info','info'], ['extract','extract','text'], ['download','download','download']]) {
      const action = actionButton(t(key), iconName, 'menu-item'); action.setAttribute('role', 'menuitem');
      action.append(element('span', '', t(key)));
      action.addEventListener('click', () => {
        closeMenus();
        if (kind === 'download') downloadPDF(file.path);
        else { openModal(kind, [file.path]); modalReturnFocus = more; }
      });
      menu.append(action);
    }
    more.addEventListener('click', () => {
      const opening = menu.hidden; closeMenus(); menu.hidden = !opening; more.setAttribute('aria-expanded', String(opening));
      card.classList.toggle('menu-open', opening); if (opening) $('button', menu).focus();
    });
    menu.addEventListener('keydown', event => {
      const buttons = $$('button', menu), current = buttons.indexOf(document.activeElement);
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') { event.preventDefault(); buttons[(current + (event.key === 'ArrowDown' ? 1 : -1) + buttons.length) % buttons.length].focus(); }
      if (event.key === 'Escape') { event.stopPropagation(); closeMenus(); more.focus(); }
    });
    actions.append(download, more); card.append(preview, body, actions, menu);
    card.addEventListener('click', event => {
      if (event.target.closest('button,input,label,.file-menu')) return;
      state.selected.has(file.path) ? state.selected.delete(file.path) : state.selected.add(file.path); renderSelection();
    });
    grid.append(card);
    if (thumbnailObserver) thumbnailObserver.observe(preview); else loadCardThumbnail(preview);
  }
  renderSelection();
  if (focusedPath && !$('#modal').open && !$('#auth-modal').open) {
    const replacement = $$('.file-card').find(card => card.dataset.path === focusedPath);
    if (replacement) $(focusWasCheckbox ? 'input[type="checkbox"]' : focusWasDownload ? '.file-actions button' : '.file-actions button:last-child', replacement)?.focus({preventScroll: true});
  }
}
function renderSelection() {
  const count = state.selected.size;
  $('#selection-bar').hidden = count === 0;
  $('#selection-count').textContent = t('selected', {count});
  $('#merge-button').disabled = count < 2;
  $('#merge-button').title = count < 2 ? t('mergeHint') : t('merge');
  document.body.classList.toggle('has-selection', count > 0);
  for (const card of $$('.file-card')) {
    const selected = state.selected.has(card.dataset.path); card.classList.toggle('is-selected', selected);
    $('input[type="checkbox"]', card).checked = selected;
  }
  const visible = visibleFiles();
  const selectedVisible = visible.filter(file => state.selected.has(file.path)).length;
  $('#select-all').checked = visible.length > 0 && selectedVisible === visible.length;
  $('#select-all').indeterminate = selectedVisible > 0 && selectedVisible < visible.length;
  $('#select-all').disabled = visible.length === 0;
}
function renderStatus() {
  const label = $('#connection-status');
  label.textContent = t(state.authRequired ? 'lockNotice' : state.connected ? 'connected' : state.booting ? 'connection' : 'disconnected');
  label.dataset.state = state.connected ? 'connected' : state.booting ? 'connecting' : 'disconnected';
  label.classList.toggle('is-connected', state.connected && !state.authRequired);
  label.classList.toggle('is-error', !state.connected && !state.booting);
  $('#index-stats').textContent = state.stats ? state.stats.index_ok ? t('index', {count: state.stats.pages}) : t('indexUnavailable') : t('indexWaiting');
  $('#version-label').textContent = state.health?.version ? `v${state.health.version}` : '';
  $('#connection-error').hidden = !state.authRequired && (state.connected || state.booting);
  $('#connection-error h3').textContent = t(state.authRequired ? 'authRequired' : 'offline');
  $('#error-message').textContent = state.authRequired ? t('authRequired') : state.lastError || t('offlineHint');
}
let fileRequest = 0;
async function refreshFiles() {
  const request = ++fileRequest;
  try {
    const files = await api('/api/files');
    if (request !== fileRequest) return;
    const byPath = new Map(files.map(file => [file.path, file]));
    invalidateThumbnails(state.files.filter(file => !byPath.has(file.path) || byPath.get(file.path).mtime !== file.mtime || byPath.get(file.path).size !== file.size).map(file => file.path));
    state.files = files; state.loaded = true; state.connected = true;
    state.selected = new Set([...state.selected].filter(path => byPath.has(path)));
  } catch (error) { if (request === fileRequest) showError(error); }
  finally { if (request === fileRequest) { state.loading = false; renderFiles(); renderStatus(); } }
}
async function refreshStats() {
  try { state.stats = await api('/api/stats'); renderStatus(); } catch (error) { showError(error); }
}

let jobTimer = null;
let polling = false;
function isActive(job) { return job.status === 'queued' || job.status === 'running'; }
function renderJobs() {
  const list = $('#jobs-list'); list.replaceChildren();
  const jobs = [...state.jobs.values()].sort((a, b) => Number(isActive(b)) - Number(isActive(a)) || b.created_at - a.created_at);
  const active = jobs.filter(isActive).length;
  $('#jobs-count').textContent = String(active); $('#jobs-count').hidden = !active;
  if (!jobs.length) {
    const empty = element('div', 'jobs-empty'); empty.innerHTML = icon('clock');
    empty.append(element('p', '', t('noJobs')), element('small', '', t('noJobsHint'))); list.append(empty);
  }
  for (const job of jobs) {
    const card = element('article', 'job-card');
    const heading = element('div', 'job-heading');
    heading.append(element('strong', 'job-name', baseName(job.params?.path || job.id)));
    const statusKey = {queued: 'queued', running: 'running', done: 'completed', error: 'failed'}[job.status] || 'queued';
    heading.append(element('span', `job-state ${job.status}`, t(statusKey))); card.append(heading);
    const meter = element('progress', 'job-progress'); meter.max = 100;
    // The v0.1 API reports 0 and 100. An indeterminate bar does not invent percentages.
    if (job.status === 'running') meter.removeAttribute('value'); else meter.value = job.status === 'done' ? 100 : 0;
    meter.setAttribute('aria-label', `${baseName(job.params?.path || job.id)}: ${t(statusKey)}`); card.append(meter);
    if (job.error) card.append(element('p', 'job-error', job.error));
    const footer = element('div', 'job-footer');
    const timestamp = element('time', '', new Intl.DateTimeFormat(state.lang, {hour: '2-digit', minute: '2-digit'}).format(new Date(job.created_at * 1000)));
    timestamp.dateTime = new Date(job.created_at * 1000).toISOString(); footer.append(timestamp);
    if (job.status === 'done' && job.result?.output) {
      const download = actionButton(t('download'), 'download', 'button ghost'); download.append(element('span', '', t('download')));
      download.addEventListener('click', () => downloadPDF(job.result.output)); footer.append(download);
    }
    card.append(footer); list.append(card);
  }
}
function toggleJobs(open = !state.drawerOpen) {
  state.drawerOpen = open; $('#jobs-drawer').hidden = !open; $('#jobs-toggle').setAttribute('aria-expanded', String(open));
  if (open) $('#jobs-close').focus(); else $('#jobs-toggle').focus();
}
function schedulePoll() {
  clearTimeout(jobTimer);
  if ([...state.jobs.values()].some(isActive)) jobTimer = setTimeout(pollJobs, 1500);
}
async function loadJobs() {
  const jobs = await api('/api/jobs'); state.jobs = new Map(jobs.map(job => [job.id, job])); renderJobs(); schedulePoll();
}
async function pollJobs() {
  if (polling) return;
  polling = true; let changed = false, pause = false;
  const active = [...state.jobs.values()].filter(isActive);
  const responses = await Promise.allSettled(active.map(job => api(`/api/jobs/${encodeURIComponent(job.id)}`)));
  responses.forEach((response, index) => {
    const old = active[index];
    if (response.status === 'rejected') {
      if (response.reason.status === 404) { state.jobs.set(old.id, {...old, status: 'error', error: t('jobMissing')}); }
      else { if (!pause) showError(response.reason); pause = true; }
      return;
    }
    const job = response.value; state.jobs.set(job.id, job);
    if (job.status === 'done') {
      changed = true; if (job.result?.output) invalidateThumbnails([job.result.output]);
      toast(t('ocrDone', {name: baseName(job.result?.output || old.params.path)}), 'success');
    } else if (job.status === 'error') toast(job.error || t('failed'), 'error');
  });
  renderJobs();
  if (changed) { await refreshFiles(); await refreshStats(); }
  polling = false; if (!pause) schedulePoll();
}

let searchTimer, searchController, searchSequence = 0;
function hideSearch() {
  clearTimeout(searchTimer); searchController?.abort(); searchSequence++;
  $('#search-results').hidden = true; $('#search-input').setAttribute('aria-expanded', 'false');
}
function safeSnippet(text) {
  return escapeHTML(text).replaceAll('&lt;mark&gt;', '<mark>').replaceAll('&lt;/mark&gt;', '</mark>');
}
async function searchDocuments() {
  const query = $('#search-input').value.trim();
  if (!query) { hideSearch(); return; }
  searchController?.abort(); searchController = new AbortController();
  const sequence = ++searchSequence;
  const results = $('#search-results'); results.replaceChildren(element('p', 'search-message', t('searchLoading')));
  results.hidden = false; $('#search-input').setAttribute('aria-expanded', 'true');
  try {
    const hits = await api('/api/search', {params: {q: query, limit: 20}, signal: searchController.signal});
    if (sequence !== searchSequence) return;
    results.replaceChildren();
    if (!hits.length) results.append(element('p', 'search-message', t('searchEmpty')), element('p', 'search-help', t('searchHelp')));
    for (const hit of hits) {
      const button = element('button', 'search-result'); button.type = 'button';
      button.setAttribute('aria-label', t('searchResultLabel', {name: hit.path, page: hit.page}));
      const heading = element('span', 'search-result-heading'); heading.append(element('strong', '', hit.path), element('small', '', t('searchPage', {page: hit.page})));
      const snippet = element('span', 'search-snippet'); snippet.innerHTML = safeSnippet(hit.snippet);
      button.append(heading, snippet); button.addEventListener('click', () => { hideSearch(); downloadPDF(hit.path); }); results.append(button);
    }
  } catch (error) {
    if (sequence !== searchSequence || error.name === 'AbortError' || error instanceof Cancelled) return;
    results.replaceChildren(element('p', 'search-message', error.message));
  }
}

let modalContext = null;
let modalReturnFocus = null;
function field(name, label, value = '', options = {}) {
  return `<label class="field"><span>${escapeHTML(t(label))}</span><input name="${name}" type="${options.type || 'text'}"
    aria-label="${escapeHTML(t(label))}" ${options.hint ? `aria-describedby="hint-${name}"` : ''}
    value="${escapeHTML(value)}" ${options.required ? 'required' : ''} ${options.type === 'number' ? 'min="1" step="1"' : ''}
    ${options.placeholder ? `placeholder="${escapeHTML(options.placeholder)}"` : ''} autocomplete="off" spellcheck="false">
    ${options.hint ? `<small id="hint-${name}">${escapeHTML(t(options.hint))}</small>` : ''}</label>`;
}
function pageField(value = '', required = true, hint = 'pagesHint') {
  return field('pages', 'pages', value, {required, placeholder: '1-3,5,8-', hint});
}
function overwriteField() {
  return `<div class="overwrite-field"><label class="check-row"><input type="checkbox" name="overwrite"><span>${t('overwrite')}</span></label>
    <p class="field-hint">${t('overwriteHint')}</p><p class="notice conflict-help" hidden>${t('conflictHint')}</p></div>`;
}
function sourceList(paths) {
  return `<ul class="source-list" aria-label="${t('sourceFiles')}">${paths.map(path => `<li>${escapeHTML(baseName(path))}</li>`).join('')}</ul>`;
}
function closeModal(force = false) {
  if (modalContext?.busy && !force) return;
  $('#modal').close(); modalContext = null;
  if (modalReturnFocus?.isConnected) modalReturnFocus.focus();
}
function openModal(kind, paths = [], extra = {}) {
  if (modalContext?.busy) return;
  const dialog = $('#modal');
  modalReturnFocus = document.activeElement;
  modalContext = {kind, paths: [...paths], pending: [...paths], completed: 0, busy: false, ...extra};
  const ctx = modalContext;
  const path = paths[0] || '';
  let title = `${kind}Title`, body = '', submit = 'save';
  const simpleOutput = suffix => field('output', 'output', outputName(path, suffix), {required: true, hint: 'outputHint'});
  switch (kind) {
    case 'merge':
      if (paths.length < 2) { toast(t('mergeHint')); modalContext = null; return; }
      body = `<p>${t('mergeDescription')}</p><ol class="merge-list"></ol>${field('output', 'output', 'merged.pdf', {required: true})}${overwriteField()}`;
      submit = 'merge'; break;
    case 'split':
      body = `<p>${t('splitDescription')}</p>${sourceList(paths)}<label class="field"><span>${t('splitMode')}</span><select name="mode"><option value="ranges">${t('ranges')}</option><option value="every_n">${t('everyN')}</option></select></label>
        <div class="split-value-field">${field('value', 'splitValue', '', {required: true, placeholder: '1-3,5,8-', hint: 'pagesHint'})}</div>
        ${field('output_dir', 'outputDir', '', {hint: 'outputDirHint'})}${overwriteField()}`; submit = 'split'; break;
    case 'rotate':
      body = sourceList(paths) + `<label class="field"><span>${t('angle')}</span><select name="angle"><option value="90">90°</option><option value="180">180°</option><option value="270">270°</option></select></label>`
        + pageField('1-') + simpleOutput('_rotated') + overwriteField(); break;
    case 'deletePages':
      body = `<p>${t('deletePagesDescription')}</p>${sourceList(paths)}${pageField()}${simpleOutput('_edited')}${overwriteField()}`; break;
    case 'compress':
      body = `<p>${t('compressDescription')}</p>${sourceList(paths)}<fieldset class="choice-group"><legend class="sr-only">${t('compressTitle')}</legend>
        <label class="choice-row"><input type="radio" name="level" value="fast" checked><span><strong>${t('fast')}</strong><small>${t('fastHint')}</small></span></label>
        <label class="choice-row"><input type="radio" name="level" value="strong" ${state.health?.ghostscript ? '' : 'disabled'}><span><strong>${t('strong')}</strong><small>${t('strongHint')}</small></span></label></fieldset>
        ${state.health?.ghostscript ? '' : `<p class="notice">${t('strongUnavailable')}</p>`}
        ${paths.length === 1 ? simpleOutput('_compressed') : ''}${overwriteField()}`; submit = 'compress'; break;
    case 'ocr': {
      const languages = state.health?.langs || [];
      body = `<p>${t('ocrDescription')}</p>${sourceList(paths)}<fieldset class="choice-group"><legend>${t('languages')}</legend>
        ${languages.map(lang => `<label class="choice-row"><input type="checkbox" name="languages" value="${escapeHTML(lang)}" ${['rus','eng'].includes(lang) ? 'checked' : ''}><span>${escapeHTML(I18N[state.lang][`lang_${lang}`] || lang)}</span></label>`).join('')}</fieldset>
        ${languages.length ? '' : `<p class="notice notice-error">${t('noLanguages')}</p>`}
        ${paths.some(p => state.files.find(file => file.path === p)?.has_text) ? `<p class="notice">${t('existingText')}</p>` : ''}
        <label class="check-row"><input type="checkbox" name="force"><span>${t('force')}</span></label>`; submit = 'ocr'; break;
    }
    case 'delete':
      body = `<p>${t('deleteDescription')}</p>${sourceList(paths)}`; submit = 'delete'; break;
    case 'info':
      title = 'info'; body = `<p class="modal-loading" role="status">${t('loading')}</p>`; submit = null; break;
    case 'extract':
      body = sourceList(paths) + pageField('', false, 'extractHint') + '<div class="extraction-result" hidden></div>'; submit = 'extractAction'; break;
    case 'donate':
      title = 'donate'; submit = null;
      body = `<p>${t('donateDescription')}</p><div class="donation-list"></div>`; break;
    case 'uploadConflict':
      title = 'conflictTitle'; body = `<p class="notice notice-error">${escapeHTML(ctx.detail)}</p><p>${t('uploadConflictHint')}</p>${sourceList(ctx.files.map(file => file.name))}`;
      submit = 'replace'; break;
    default: return;
  }
  dialog.innerHTML = `<form class="modal-form"><div class="modal-header"><h2 id="modal-title">${t(title)}</h2>
    <button type="button" class="icon-button" data-close-modal aria-label="${t('close')}">${icon('close')}</button></div>
    <div class="modal-body">${body}<p class="modal-feedback notice notice-error" role="alert" hidden></p></div>
    <div class="modal-footer"><button type="button" class="button secondary" data-close-modal>${t(submit ? 'cancel' : 'close')}</button>
    ${submit ? `<button type="submit" class="button primary${kind === 'delete' ? ' danger' : ''}">${t(submit)}</button>` : ''}</div></form>`;
  $$('[data-close-modal]', dialog).forEach(button => button.addEventListener('click', () => closeModal()));
  $('form', dialog).addEventListener('submit', event => { event.preventDefault(); submitModal(ctx, event.currentTarget); });
  if (kind === 'merge') renderMergeOrder();
  if (kind === 'split') $('[name="mode"]', dialog).addEventListener('change', event => {
    $('.split-value-field', dialog).innerHTML = event.target.value === 'every_n'
      ? field('value', 'splitEvery', '1', {required: true, type: 'number'})
      : field('value', 'splitValue', '', {required: true, placeholder: '1-3,5,8-', hint: 'pagesHint'});
  });
  if (!dialog.open) dialog.showModal();
  const first = $('input:not([type="checkbox"]):not([type="radio"]),select', dialog);
  if (first) { first.focus(); if (first.type === 'text') first.select(); }
  if (kind === 'info') loadInfo(ctx);
  if (kind === 'donate') renderDonate();
}
function renderMergeOrder() {
  const list = $('.merge-list', $('#modal')); list.replaceChildren();
  modalContext.paths.forEach((path, index) => {
    const row = element('li', 'merge-row');
    row.append(element('span', '', `${index + 1}. ${baseName(path)}`));
    for (const [delta, name, key] of [[-1,'up','moveUp'], [1,'down','moveDown']]) {
      const button = actionButton(t(key, {name: baseName(path)}), name);
      button.disabled = index + delta < 0 || index + delta >= modalContext.paths.length;
      button.addEventListener('click', () => {
        const paths = modalContext.paths; [paths[index], paths[index + delta]] = [paths[index + delta], paths[index]];
        renderMergeOrder(); const newRow = $('.merge-list', $('#modal')).children[index + delta];
        const target = $$('button', newRow).find(item => !item.disabled); target?.focus();
      }); row.append(button);
    }
    list.append(row);
  });
}
function validatePages(value, total, allowEmpty = false) {
  value = value.replace(/\s/g, '');
  if (allowEmpty && !value) return '';
  if (!/^\d+(?:-\d*)?(?:,\d+(?:-\d*)?)*$/.test(value)) throw new Error(t('invalidPages'));
  for (const part of value.split(',')) {
    const [startText, endText] = part.split('-');
    const start = Number(startText), end = endText === '' ? total : endText === undefined ? start : Number(endText);
    if (!Number.isSafeInteger(start) || start < 1 || (total && start > total) || (end !== null && end !== undefined && (!Number.isSafeInteger(end) || end < start || (total && end > total)))) throw new Error(t('invalidPages'));
  }
  return value;
}
function outputValue(form) {
  const value = form.get('output')?.trim();
  if (!value || !/\.pdf$/i.test(value) || value.startsWith('/') || value.includes('\\') || value.split('/').includes('..') || /^[A-Za-z]:/.test(value)) throw new Error(t('invalidOutput'));
  return value;
}
function modalPayload(ctx, form) {
  const path = ctx.paths[0], total = state.files.find(file => file.path === path)?.pages;
  const overwrite = form.get('overwrite') === 'on';
  switch (ctx.kind) {
    case 'merge': return {paths: ctx.paths, output: outputValue(form), overwrite};
    case 'split': {
      const mode = form.get('mode'); let value = form.get('value').trim();
      if (mode === 'ranges') value = validatePages(value, total);
      else if (!/^\d+$/.test(value) || Number(value) < 1 || !Number.isSafeInteger(Number(value)) || (total && Number(value) > total)) throw new Error(t('invalidEvery', {max: total || '…'}));
      const output_dir = form.get('output_dir').trim();
      return {path, mode, value, overwrite, ...(output_dir ? {output_dir} : {})};
    }
    case 'rotate': return {path, pages: validatePages(form.get('pages'), total), angle: Number(form.get('angle')), output: outputValue(form), overwrite};
    case 'deletePages': {
      const pages = validatePages(form.get('pages'), total);
      if (total) {
        const selected = new Set();
        for (const part of pages.split(',')) {
          const [start, end] = part.split('-');
          for (let page = Number(start); page <= (end === undefined ? Number(start) : end === '' ? total : Number(end)); page++) selected.add(page);
        }
        if (selected.size >= total) throw new Error(t('cannotDeleteAll'));
      }
      return {path, pages, output: outputValue(form), overwrite};
    }
    case 'compress': return {level: form.get('level'), overwrite, ...(ctx.paths.length === 1 ? {output: outputValue(form)} : {})};
    case 'ocr': {
      const languages = form.getAll('languages'); if (!languages.length) throw new Error(t('chooseLanguage'));
      return {languages, force: form.get('force') === 'on'};
    }
    case 'extract': {
      const pages = validatePages(form.get('pages'), total, true); return {path, ...(pages ? {pages} : {})};
    }
    default: return {};
  }
}
async function submitModal(ctx, formElement) {
  if (ctx !== modalContext || ctx.busy || !formElement.reportValidity()) return;
  const feedback = $('.modal-feedback', formElement); feedback.hidden = true;
  let payload;
  try { payload = modalPayload(ctx, new FormData(formElement)); }
  catch (error) { feedback.textContent = error.message; feedback.hidden = false; return; }
  const controls = $$('button,input,select', formElement).map(node => [node, node.disabled]);
  const submit = $('[type="submit"]', formElement), originalText = submit?.textContent;
  ctx.busy = true; controls.forEach(([node]) => { node.disabled = true; });
  if (submit) submit.textContent = t('processing');
  try {
    if (ctx.kind === 'uploadConflict') { await uploadFiles(ctx.files, true); return; }
    if (ctx.kind === 'extract') {
      const result = await api('/api/extract-text', {method: 'POST', json: payload});
      renderExtractedText(result.pages, formElement); return;
    }
    if (['ocr','compress','delete'].includes(ctx.kind)) await performBatch(ctx, payload);
    else {
      const route = {merge: 'merge', split: 'split', rotate: 'rotate', deletePages: 'delete-pages'}[ctx.kind];
      const result = await api(`/api/${route}`, {method: 'POST', json: payload});
      const outputs = result.outputs || [result.output]; invalidateThumbnails(outputs);
      toast(outputs.length === 1 ? t('created', {name: baseName(outputs[0])}) : t('createdMany', {count: outputs.length}), 'success');
    }
    closeModal(true);
    if (ctx.kind === 'ocr') toggleJobs(true);
  } catch (error) {
    if (!(error instanceof Cancelled)) {
      feedback.textContent = (ctx.completed ? `${t(ctx.kind === 'ocr' ? 'partiallyQueued' : 'partiallyCompleted', {count: ctx.completed})} ` : '') + error.message;
      feedback.hidden = false; showError(error);
      if (error.status === 409) {
        const help = $('.conflict-help', formElement); if (help) help.hidden = false;
      }
      const list = $('.source-list', formElement);
      if (list && ctx.pending.length !== ctx.paths.length) list.outerHTML = sourceList(ctx.pending);
    }
  } finally {
    ctx.busy = false;
    controls.forEach(([node, disabled]) => { node.disabled = disabled; });
    if (submit) submit.textContent = originalText;
    if (ctx === modalContext && !$('#auth-modal').open) {
      const result = ctx.kind === 'extract' ? $('.extracted-text', formElement) : null;
      (result || submit)?.focus({preventScroll: true});
    }
    if (!['extract','uploadConflict'].includes(ctx.kind)) { await refreshFiles(); await refreshStats(); }
    const help = $('.conflict-help', formElement);
    if (ctx === modalContext && help && !help.hidden) $('[name="overwrite"]', formElement)?.focus();
  }
}
async function performBatch(ctx, payload) {
  while (ctx.pending.length) {
    const path = ctx.pending[0]; let result;
    if (ctx.kind === 'delete') {
      result = await api('/api/file', {method: 'DELETE', params: {path}});
      state.selected.delete(path); invalidateThumbnails([path]);
    } else {
      result = await api(`/api/${ctx.kind}`, {method: 'POST', json: {...payload, path}});
      if (ctx.kind === 'ocr') {
        const job = {id: result.job_id, kind: 'ocr', params: {path, ...payload}, status: 'queued', progress: 0, created_at: Date.now() / 1000, finished_at: null, result: null, error: null};
        state.jobs.set(job.id, job); renderJobs(); schedulePoll();
      } else {
        invalidateThumbnails([result.output]);
        const delta = result.size_before ? (1 - result.size_after / result.size_before) * 100 : 0;
        const change = Math.abs(delta) < 0.05 ? t('sameSize') : t(delta > 0 ? 'smaller' : 'larger', {percent: new Intl.NumberFormat(state.lang, {maximumFractionDigits: 1}).format(Math.abs(delta))});
        toast(`${baseName(result.output)} · ${t('compressionSummary', {before: formatSize(result.size_before), after: formatSize(result.size_after)})} · ${change}`, 'success');
      }
    }
    ctx.pending.shift(); ctx.completed++;
  }
  if (ctx.kind === 'ocr') toast(t('ocrQueued', {count: ctx.completed}), 'success');
  if (ctx.kind === 'delete') toast(t('deleted', {count: ctx.completed}), 'success');
}
async function loadInfo(ctx) {
  try {
    const info = await api('/api/file/info', {params: {path: ctx.paths[0]}});
    if (ctx !== modalContext) return;
    const table = element('table', 'info-table');
    const rows = [
      ['fileName', baseName(ctx.paths[0])], ['filePath', ctx.paths[0]], ['pageCount', info.pages],
      ['fileSize', formatSize(info.size_bytes)], ['encrypted', t(info.encrypted ? 'yes' : 'no')],
      ['title', info.title || t('unspecified')], ['author', info.author || t('unspecified')], ['createdAt', info.created || t('unspecified')],
    ];
    const tbody = element('tbody');
    for (const [key, value] of rows) { const row = element('tr'); const th = element('th', '', t(key)); th.scope = 'row'; row.append(th, element('td', '', String(value ?? '—'))); tbody.append(row); }
    table.append(tbody); $('.modal-loading', $('#modal')).replaceWith(table);
  } catch (error) {
    if (ctx === modalContext) $('.modal-loading', $('#modal')).textContent = error.message || t('authRequired');
  }
}
async function copyText(text, successKey) {
  try {
    if (navigator.clipboard && window.isSecureContext) await navigator.clipboard.writeText(text);
    else {
      const field = element('textarea', 'clipboard-helper'); field.value = text; field.setAttribute('aria-label', t('copyText'));
      const parent = $('#modal').open ? $('#modal') : document.body;
      const focused = document.activeElement; parent.append(field); field.select();
      const copied = document.execCommand('copy'); field.remove(); focused?.focus();
      if (!copied) throw new Error();
    }
    toast(t(successKey), 'success');
  } catch { toast(t('copyFailed'), 'error'); }
}
function renderDonate() {
  const list = $('.donation-list', $('#modal'));
  for (const {network, address} of state.addresses) {
    const row = element('div', 'donation-item');
    row.append(element('strong', 'donation-network', network));
    const code = element('code', 'donation-address', address); row.append(code);
    const copy = actionButton(t('copyAddress'), 'copy', 'button secondary'); copy.append(element('span', '', t('copyAddress')));
    copy.addEventListener('click', () => copyText(address, 'addressCopied')); row.append(copy); list.append(row);
  }
}
function renderExtractedText(pages, form) {
  const result = $('.extraction-result', form); result.replaceChildren(); result.hidden = false;
  const entries = Object.entries(pages || {}).sort((a, b) => Number(a[0]) - Number(b[0]));
  if (!entries.some(([,text]) => text.trim())) { result.append(element('p', 'notice', t('noText'))); return; }
  const text = entries.map(([page, content]) => `${t('extractedPage', {page})}\n${content}`).join('\n\n');
  const pre = element('pre', 'extracted-text', text); pre.tabIndex = 0; pre.setAttribute('aria-label', t('extractTitle'));
  const copy = actionButton(t('copyText'), 'copy', 'button secondary'); copy.append(element('span', '', t('copyText')));
  copy.addEventListener('click', () => copyText(text, 'copiedText')); result.append(pre, copy);
}

function applyTheme() {
  document.documentElement.dataset.theme = state.theme;
  const button = $('#theme-toggle'); button.innerHTML = icon(state.theme === 'dark' ? 'sun' : 'moon');
  button.setAttribute('aria-label', t(state.theme === 'dark' ? 'theme' : 'themeDark'));
  button.title = button.getAttribute('aria-label');
}
function translatePage() {
  document.documentElement.lang = state.lang;
  document.title = `PDFCabin — ${t('library')}`;
  $$('[data-i18n]').forEach(node => { node.textContent = t(node.dataset.i18n); });
  $$('[data-i18n-placeholder]').forEach(node => { node.placeholder = t(node.dataset.i18nPlaceholder); });
  $$('[data-i18n-label]').forEach(node => { node.setAttribute('aria-label', t(node.dataset.i18nLabel)); });
  $('#lang-toggle span').textContent = state.lang.toUpperCase();
  applyTheme(); renderFiles(); renderJobs(); renderStatus(); renderUploadLabel();
}
async function boot() {
  if (state.booting) return;
  state.booting = true; state.loading = !state.loaded;
  $('#refresh-button').disabled = true; $('#retry-button').disabled = true;
  renderFiles(); renderStatus();
  try {
    state.health = await api('/api/health'); state.connected = true; state.authRequired = false; state.lastError = '';
    const results = await Promise.allSettled([
      refreshFiles(), refreshStats(), loadJobs(),
      api('/api/donate').then(result => { state.addresses = result.addresses || []; $('#donate-button').hidden = !state.addresses.length; }),
    ]);
    results.filter(result => result.status === 'rejected').forEach(result => showError(result.reason));
  } catch (error) {
    state.connected = error.status === 401 || error instanceof Cancelled;
    state.authRequired = state.connected;
    $('#error-message').textContent = error instanceof Cancelled ? t('authRequired') : error.message;
    showError(error);
  } finally {
    state.booting = false; state.loading = false;
    $('#refresh-button').disabled = false; $('#retry-button').disabled = false;
    renderFiles(); renderStatus();
  }
}

$('#choose-files').addEventListener('click', () => $('#file-input').click());
$('#file-input').addEventListener('change', event => {
  const files = [...event.target.files]; event.target.value = ''; uploadFiles(files);
});
$('#dropzone').addEventListener('keydown', event => {
  if (event.target === event.currentTarget && (event.key === 'Enter' || event.key === ' ')) {
    event.preventDefault(); if (!state.uploadBusy) $('#file-input').click();
  }
});
let dragDepth = 0;
document.addEventListener('dragenter', event => {
  if (!Array.from(event.dataTransfer?.types || []).includes('Files')) return;
  event.preventDefault(); dragDepth++; $('#dropzone').classList.add('is-dragging');
});
document.addEventListener('dragover', event => {
  if (Array.from(event.dataTransfer?.types || []).includes('Files')) { event.preventDefault(); event.dataTransfer.dropEffect = 'copy'; }
});
document.addEventListener('dragleave', event => {
  if (!Array.from(event.dataTransfer?.types || []).includes('Files')) return;
  dragDepth = Math.max(0, dragDepth - 1); if (!dragDepth) $('#dropzone').classList.remove('is-dragging');
});
document.addEventListener('drop', event => {
  if (!event.dataTransfer?.files.length) return;
  event.preventDefault(); dragDepth = 0; $('#dropzone').classList.remove('is-dragging');
  if (!$('#modal').open && !$('#auth-modal').open) uploadFiles(event.dataTransfer.files);
});
$('#lang-toggle').addEventListener('click', () => {
  state.lang = state.lang === 'en' ? 'ru' : 'en'; savePreference('pdfcabin_lang', state.lang); translatePage();
  if (!$('#search-results').hidden) searchDocuments();
});
$('#theme-toggle').addEventListener('click', () => {
  state.theme = state.theme === 'dark' ? 'light' : 'dark'; savePreference('pdfcabin_theme', state.theme); applyTheme();
});
$('#token-button').addEventListener('click', async () => {
  try { await requestToken(); await boot(); } catch (error) { showError(error); }
});
$('#donate-button').addEventListener('click', () => openModal('donate'));
$('#refresh-button').addEventListener('click', boot);
$('#retry-button').addEventListener('click', boot);
$('#sort-select').addEventListener('change', event => { state.sort = event.target.value; renderFiles(); });
$('#filter-tabs').addEventListener('click', event => {
  const button = event.target.closest('[data-filter]'); if (!button) return;
  state.filter = button.dataset.filter;
  $$('[data-filter]').forEach(item => {
    const active = item === button; item.classList.toggle('is-active', active); item.setAttribute('aria-pressed', String(active));
  }); renderFiles();
});
$('#select-all').addEventListener('change', event => {
  visibleFiles().forEach(file => event.target.checked ? state.selected.add(file.path) : state.selected.delete(file.path)); renderSelection();
});
$('#clear-selection').addEventListener('click', () => { state.selected.clear(); renderSelection(); $('#select-all').focus(); });
for (const kind of ['merge','compress','ocr','delete']) {
  $(`#${kind}-button`).addEventListener('click', () => { if (state.selected.size) openModal(kind, [...state.selected]); });
}
$('#jobs-toggle').addEventListener('click', () => toggleJobs());
$('#jobs-close').addEventListener('click', () => toggleJobs(false));
$('#modal').addEventListener('cancel', event => { if (modalContext?.busy) event.preventDefault(); });
$('#modal').addEventListener('close', () => {
  modalContext = null;
  if (modalReturnFocus?.isConnected) modalReturnFocus.focus({preventScroll: true});
});
$('#modal').addEventListener('click', event => {
  if (event.target !== event.currentTarget) return;
  const rect = event.currentTarget.getBoundingClientRect();
  if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) closeModal();
});
$('#search-input').addEventListener('input', () => {
  clearTimeout(searchTimer);
  if (!$('#search-input').value.trim()) hideSearch(); else searchTimer = setTimeout(searchDocuments, 300);
});
$('#search-input').addEventListener('keydown', event => {
  if (event.key === 'Enter') { event.preventDefault(); clearTimeout(searchTimer); searchDocuments(); }
  if (event.key === 'ArrowDown' && !$('#search-results').hidden) { event.preventDefault(); $('.search-result')?.focus(); }
  if (event.key === 'Escape') hideSearch();
});
$('#search-results').addEventListener('keydown', event => {
  const buttons = $$('.search-result'), index = buttons.indexOf(document.activeElement);
  if (event.key === 'ArrowDown' && index >= 0) { event.preventDefault(); buttons[(index + 1) % buttons.length].focus(); }
  if (event.key === 'ArrowUp' && index >= 0) { event.preventDefault(); if (index === 0) $('#search-input').focus(); else buttons[index - 1].focus(); }
  if (event.key === 'Escape') { hideSearch(); $('#search-input').focus(); }
});
document.addEventListener('click', event => {
  if (!event.target.closest('.file-menu,.file-actions')) closeMenus();
  if (!event.target.closest('.search-container')) hideSearch();
});
document.addEventListener('keydown', event => {
  if (event.key === '/' && !event.ctrlKey && !event.metaKey && !event.altKey && !event.target.closest('input,textarea,select,[contenteditable="true"]') && !$('#modal').open && !$('#auth-modal').open) {
    event.preventDefault(); $('#search-input').focus();
  }
  if (event.key === 'Escape' && !$('#modal').open && !$('#auth-modal').open) {
    closeMenus(); hideSearch(); if (state.drawerOpen) toggleJobs(false);
  }
});
window.addEventListener('pagehide', () => {
  clearTimeout(jobTimer); searchController?.abort();
  for (const entry of thumbCache.values()) if (entry.url) URL.revokeObjectURL(entry.url);
  thumbCache.clear();
});
window.addEventListener('pageshow', event => { if (event.persisted) boot(); });

translatePage();
boot();
