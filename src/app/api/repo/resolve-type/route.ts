import { NextRequest, NextResponse } from 'next/server';

// Thin proxy to the backend repo-type resolver. On-prem host overrides live in
// the backend env (ONPREM_*_HOSTS) and are applied there; this route just
// forwards and returns { type }. On failure the client falls back to its local
// public-host heuristic (see fetchRepoType in src/utils/repoType.ts).
const TARGET_SERVER_BASE_URL = process.env.SERVER_BASE_URL || 'http://localhost:8001';

export async function GET(req: NextRequest) {
  const url = req.nextUrl.searchParams.get('url') || '';
  try {
    const res = await fetch(
      `${TARGET_SERVER_BASE_URL}/repo/resolve-type?url=${encodeURIComponent(url)}`,
    );
    return new NextResponse(await res.text(), {
      status: res.status,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Error in /api/repo/resolve-type proxy:', error);
    return new NextResponse(JSON.stringify({ error: 'Failed to resolve repo type' }), {
      status: 502,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
