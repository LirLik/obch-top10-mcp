export function formatTop10(document) {
  if (!document || !Array.isArray(document.scores) || document.scores.length === 0) {
    return 'Топ-10 пока пуст. Синхронизируйте данные командой sync_top10 или php artisan stats:push-top10.';
  }

  const lines = [
    'Топ-10 результатов obch',
    `Обновлено: ${document.updated_at ?? '—'}`,
    `Источник: ${document.source ?? '—'}`,
    '',
    '| # | Игрок | Очки | Линии | Уровень | Длит. (с) | Дата |',
    '|---|-------|------|-------|---------|-----------|------|',
  ];

  for (const row of document.scores) {
    const date = row.created_at ? String(row.created_at).replace('T', ' ').slice(0, 19) : '—';
    lines.push(
      `| ${row.rank} | ${row.player_name} | ${row.score} | ${row.lines_cleared} | ${row.level} | ${row.duration_seconds} | ${date} |`,
    );
  }

  return lines.join('\n');
}
