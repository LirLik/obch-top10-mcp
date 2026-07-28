#!/usr/bin/env node
import './loadEnv.js';
import { createApp } from './app.js';

const host = process.env.HOST || process.env.OBCH_TOP10_WEB_HOST || '0.0.0.0';
const port = Number(process.env.PORT || process.env.OBCH_TOP10_WEB_PORT || 3920);

const app = createApp();

app.listen(port, host, (error) => {
  if (error) {
    console.error('Не удалось запустить сервер:', error);
    process.exit(1);
  }

  const displayHost = host === '0.0.0.0' ? '127.0.0.1' : host;
  console.log(`obch-top10-mcp`);
  console.log(`  сайт:  http://${displayHost}:${port}/`);
  console.log(`  API:   http://${displayHost}:${port}/api/top10`);
  console.log(`  MCP:   http://${displayHost}:${port}/mcp`);
});
