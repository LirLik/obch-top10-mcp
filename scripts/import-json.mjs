#!/usr/bin/env node
import '../src/loadEnv.js';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { replaceTop10 } from '../src/services/topScoresService.js';
import { prisma } from '../src/db.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const filePath = process.argv[2] || path.resolve(__dirname, '../data/top10.json');

const raw = await readFile(filePath, 'utf8');
const payload = JSON.parse(raw);
const document = await replaceTop10({
  source: payload.source || `import:${path.basename(filePath)}`,
  scores: payload.scores || [],
});

console.log(`Импортировано ${document.scores.length} записей из ${filePath}`);
await prisma.$disconnect();
