import { NextRequest, NextResponse } from 'next/server';

import { parseHosts, resolveRepoTypeFromDomain } from '@/utils/repoType';

// Resolve a repository URL to a provider type, applying self-hosted (on-prem)
// host overrides from SERVER-ONLY env vars. These host lists are intentionally
// not `NEXT_PUBLIC_*`, so they are never inlined into the client bundle:
//   ONPREM_GITHUB_HOSTS=github.company.com
//   ONPREM_GITLAB_HOSTS=git.company.com,gitlab.corp.net
//   ONPREM_BITBUCKET_HOSTS=stash.company.com
// Read at request time, so changing them needs no rebuild.
export async function GET(req: NextRequest) {
  const url = req.nextUrl.searchParams.get('url') || '';
  const type = resolveRepoTypeFromDomain(url, {
    github: parseHosts(process.env.ONPREM_GITHUB_HOSTS),
    gitlab: parseHosts(process.env.ONPREM_GITLAB_HOSTS),
    bitbucket: parseHosts(process.env.ONPREM_BITBUCKET_HOSTS),
  });
  return NextResponse.json({ type });
}
