import { prisma } from '../db.js';

function parsePlayedAt(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function normalizeScores(scores) {
  return (Array.isArray(scores) ? scores : [])
    .slice(0, 10)
    .map((item, index) => ({
      externalId: item.id == null || item.id === '' ? null : Number(item.id) || null,
      rank: Number(item.rank) || index + 1,
      playerName: String(item.player_name || item.playerName || 'Игрок').slice(0, 64),
      score: Number(item.score) || 0,
      linesCleared: Number(item.lines_cleared ?? item.linesCleared) || 0,
      level: Number(item.level) || 1,
      durationSeconds: Number(item.duration_seconds ?? item.durationSeconds) || 0,
      playedAt: parsePlayedAt(item.created_at ?? item.played_at ?? item.playedAt),
    }));
}

function toDocument(rows) {
  if (!rows.length) {
    return {
      updated_at: null,
      source: null,
      scores: [],
      empty: true,
      message: 'Топ-10 пока пуст. Выполните php artisan stats:push-top10 или sync_top10.',
    };
  }

  const syncedAt = rows[0].syncedAt;
  const source = rows[0].source;

  return {
    updated_at: syncedAt ? syncedAt.toISOString() : null,
    source,
    scores: rows.map((row) => ({
      rank: row.rank,
      id: row.externalId,
      player_name: row.playerName,
      score: row.score,
      lines_cleared: row.linesCleared,
      level: row.level,
      duration_seconds: row.durationSeconds,
      created_at: row.playedAt ? row.playedAt.toISOString() : null,
    })),
    empty: false,
  };
}

export async function getTop10() {
  const rows = await prisma.score.findMany({
    orderBy: [{ rank: 'asc' }, { score: 'desc' }],
    take: 10,
  });
  return toDocument(rows);
}

export async function replaceTop10({ scores, source = 'api:post' } = {}) {
  const normalized = normalizeScores(scores);
  const syncedAt = new Date();
  const sourceLabel = String(source || 'unknown').slice(0, 255);

  await prisma.$transaction(async (tx) => {
    await tx.score.deleteMany();

    if (normalized.length > 0) {
      await tx.score.createMany({
        data: normalized.map((row) => ({
          ...row,
          source: sourceLabel,
          syncedAt,
        })),
      });
    }

    await tx.syncEvent.create({
      data: {
        source: sourceLabel,
        scoresCount: normalized.length,
        payloadJson: {
          scores: normalized.map((row) => ({
            rank: row.rank,
            id: row.externalId,
            player_name: row.playerName,
            score: row.score,
            lines_cleared: row.linesCleared,
            level: row.level,
            duration_seconds: row.durationSeconds,
            created_at: row.playedAt ? row.playedAt.toISOString() : null,
          })),
        },
      },
    });
  });

  return getTop10();
}

export async function syncFromObchStats(statsUrl) {
  const response = await fetch(statsUrl);
  if (!response.ok) {
    throw new Error(`Не удалось получить статистику: HTTP ${response.status} (${statsUrl})`);
  }

  const stats = await response.json();
  if (!Array.isArray(stats.top_scores)) {
    throw new Error(
      'В ответе API нет top_scores. Проверьте show_top_scores в админке obch.',
    );
  }

  return replaceTop10({
    source: statsUrl,
    scores: stats.top_scores,
  });
}
