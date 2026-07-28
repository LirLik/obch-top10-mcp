export function getAuthToken() {
  return process.env.MCP_AUTH_TOKEN || process.env.OBCH_TOP10_TOKEN || '';
}

export function extractRequestToken(req) {
  const header = req.get?.('authorization') || req.headers?.authorization || '';
  if (typeof header === 'string' && header.toLowerCase().startsWith('bearer ')) {
    return header.slice(7).trim();
  }

  const url = req.originalUrl || req.url || '';
  try {
    const parsed = new URL(url, 'http://localhost');
    return parsed.searchParams.get('token') || '';
  } catch {
    return '';
  }
}

export function requireAuthIfConfigured(req, res, next) {
  const expected = getAuthToken();
  if (!expected) {
    return next();
  }

  if (extractRequestToken(req) === expected) {
    return next();
  }

  return res.status(401).json({
    error: 'Unauthorized',
    message: 'Нужен токен: Authorization: Bearer <MCP_AUTH_TOKEN> или ?token=',
  });
}
