import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { formatTop10 } from './format.js';
import { getTop10, replaceTop10, syncFromObchStats } from './services/topScoresService.js';

function defaultStatsUrl() {
  return process.env.OBCH_STATS_URL || 'http://obch/api/stats';
}

export function createMcpServer() {
  const server = new McpServer({
    name: 'obch-top10-mcp',
    version: '1.1.0',
  });

  server.tool(
    'get_top10',
    'Показать сохранённый Топ-10 результатов из obch (MariaDB)',
    {},
    async () => {
      const document = await getTop10();
      return {
        content: [{ type: 'text', text: formatTop10(document) }],
      };
    },
  );

  server.tool(
    'sync_top10',
    'Забрать актуальный Топ-10 из API obch, сохранить в БД и показать',
    {
      stats_url: z
        .string()
        .url()
        .optional()
        .describe(`URL GET /api/stats (по умолчанию ${defaultStatsUrl()})`),
    },
    async ({ stats_url }) => {
      const document = await syncFromObchStats(stats_url || defaultStatsUrl());
      return {
        content: [{ type: 'text', text: formatTop10(document) }],
      };
    },
  );

  server.tool(
    'save_top10',
    'Принять и сохранить Топ-10 в БД (массив результатов), затем показать',
    {
      scores: z
        .array(
          z.object({
            id: z.union([z.number(), z.string()]).optional(),
            player_name: z.string().optional(),
            score: z.number(),
            lines_cleared: z.number().optional(),
            level: z.number().optional(),
            duration_seconds: z.number().optional(),
            created_at: z.string().nullable().optional(),
          }),
        )
        .max(10)
        .describe('Массив до 10 результатов, отсортированных по score DESC'),
      source: z.string().optional().describe('Метка источника (artisan, agent и т.п.)'),
    },
    async ({ scores, source }) => {
      const document = await replaceTop10({
        source: source || 'mcp:save_top10',
        scores,
      });
      return {
        content: [{ type: 'text', text: formatTop10(document) }],
      };
    },
  );

  return server;
}
