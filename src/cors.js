const DEFAULT_ORIGINS = [
  'https://chatgpt.com',
  'https://chat.openai.com',
  'https://platform.openai.com',
];

function allowedOrigins() {
  const fromEnv = (process.env.CORS_ORIGINS || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
  return fromEnv.length ? fromEnv : DEFAULT_ORIGINS;
}

export function corsMiddleware(req, res, next) {
  const origin = req.headers.origin;
  const allowed = allowedOrigins();

  if (origin && (allowed.includes('*') || allowed.includes(origin))) {
    res.setHeader('Access-Control-Allow-Origin', origin);
    res.setHeader('Vary', 'Origin');
  } else if (!origin) {
    // server-to-server / curl
  } else if (allowed.includes('*')) {
    res.setHeader('Access-Control-Allow-Origin', '*');
  }

  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,DELETE,OPTIONS');
  res.setHeader(
    'Access-Control-Allow-Headers',
    'Content-Type, Authorization, Accept, MCP-Session-Id, Last-Event-ID',
  );
  res.setHeader('Access-Control-Expose-Headers', 'MCP-Session-Id');

  if (req.method === 'OPTIONS') {
    return res.status(204).end();
  }

  return next();
}
