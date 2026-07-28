const REFRESH_MS = 15000;

const els = {
  board: document.querySelector('#board'),
  updated: document.querySelector('#updated'),
  source: document.querySelector('#source'),
  state: document.querySelector('#state'),
  refresh: document.querySelector('#refresh'),
};

function formatDate(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value).replace('T', ' ').slice(0, 19);
  }
  return date.toLocaleString('ru-RU', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function showState(message, isError = false) {
  els.state.hidden = !message;
  els.state.textContent = message || '';
  els.state.classList.toggle('error', Boolean(isError));
  els.state.classList.toggle('empty', !isError);
}

function renderScores(scores) {
  els.board.innerHTML = '';

  scores.forEach((row, index) => {
    const item = document.createElement('article');
    item.className = 'row' + (index === 0 ? ' row-top' : '');
    item.innerHTML = `
      <div class="rank">#${row.rank ?? index + 1}</div>
      <div class="player">
        <p class="player-name"></p>
        <p class="player-meta"></p>
      </div>
      <div class="score"></div>
    `;
    item.querySelector('.player-name').textContent = row.player_name || 'Игрок';
    item.querySelector('.player-meta').textContent =
      `линии ${row.lines_cleared ?? 0} · ур. ${row.level ?? 1} · ${row.duration_seconds ?? 0} с · ${formatDate(row.created_at)}`;
    item.querySelector('.score').textContent = String(row.score ?? 0);
    els.board.appendChild(item);
  });
}

async function loadTop10() {
  els.refresh.disabled = true;
  showState('');

  try {
    const response = await fetch('/api/top10', { cache: 'no-store' });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    if (data.error) {
      throw new Error(data.error);
    }

    els.updated.textContent = formatDate(data.updated_at);
    els.source.textContent = data.source || '—';

    const scores = Array.isArray(data.scores) ? data.scores : [];
    if (scores.length === 0) {
      renderScores([]);
      showState(data.message || 'Топ-10 пока пуст.');
      return;
    }

    renderScores(scores);
  } catch (error) {
    showState(`Не удалось загрузить Топ-10: ${error.message}`, true);
  } finally {
    els.refresh.disabled = false;
  }
}

els.refresh.addEventListener('click', () => {
  loadTop10();
});

loadTop10();
setInterval(loadTop10, REFRESH_MS);
