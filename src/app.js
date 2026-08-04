import express from 'express';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { createMcpExpressApp } from '@modelcontextprotocol/sdk/server/express.js';
import { requireAuthIfConfigured } from './auth.js';
import { corsMiddleware } from './cors.js';
import { createMcpServer } from './createMcpServer.js';
import { checkDatabase } from './db.js';
import { getTop10, replaceTop10 } from './services/topScoresService.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const publicDir = path.resolve(__dirname, '../public');

async function handleMcp(req, res) {
  const server = createMcpServer();
  try {
    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: undefined,
    });
    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
    res.on('close', () => {
      transport.close();
      server.close();
    });
  } catch (error) {
    console.error('MCP request error:', error);
    if (!res.headersSent) {
      res.status(500).json({
        jsonrpc: '2.0',
        error: { code: -32603, message: 'Internal server error' },
        id: null,
      });
    }
  }
}

export function createApp() {
  const host = process.env.HOST || process.env.OBCH_TOP10_WEB_HOST || '0.0.0.0';
  const allowedHosts = (process.env.MCP_ALLOWED_HOSTS || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);

  const app = createMcpExpressApp({
    host,
    ...(allowedHosts.length ? { allowedHosts } : {}),
  });

  app.use(corsMiddleware);

  app.get('/health', async (_req, res) => {
    try {
      await checkDatabase();
      res.json({ ok: true, service: 'obch-top10-mcp', database: 'up' });
    } catch (error) {
      res.status(503).json({
        ok: false,
        service: 'obch-top10-mcp',
        database: 'down',
        error: error.message,
      });
    }
  });

  app.get('/api/top10', async (_req, res) => {
    try {
      const document = await getTop10();
      return res.json(document);
    } catch (error) {
      console.error(error);
      return res.status(500).json({ error: 'Не удалось прочитать Топ-10 из БД' });
    }
  });

  app.post('/api/top10', requireAuthIfConfigured, async (req, res) => {
    const scores = Array.isArray(req.body?.scores)
      ? req.body.scores
      : Array.isArray(req.body?.top_scores)
        ? req.body.top_scores
        : null;

    if (!scores) {
      return res.status(422).json({
        error: 'Ожидается JSON с полем scores (или top_scores)',
      });
    }

    try {
      const document = await replaceTop10({
        source: req.body?.source || 'api:post',
        scores,
      });
      return res.status(201).json(document);
    } catch (error) {
      console.error(error);
      return res.status(500).json({ error: 'Не удалось сохранить Топ-10 в БД' });
    }
  });

  app.post('/mcp', requireAuthIfConfigured, handleMcp);
  app.get('/mcp', requireAuthIfConfigured, handleMcp);
  app.delete('/mcp', requireAuthIfConfigured, handleMcp);

  app.use(express.static(publicDir, {
    index: 'index.html',
    fallthrough: true,
  }));

  app.use((req, res, next) => {
    if (req.method !== 'GET' && req.method !== 'HEAD') {
      return next();
    }
    if (req.path.startsWith('/api') || req.path.startsWith('/mcp') || req.path === '/health') {
      return next();
    }
    return res.sendFile(path.join(publicDir, 'index.html'));
  });

  return app;
}
