// Repository provider-type detection.
//
// The pure resolver (`resolveRepoTypeFromDomain`) knows only the built-in public
// hosts + a vendor-name heuristic. Self-hosted (on-prem) host overrides are NOT
// baked into the client bundle: they live in server-only env vars and are applied
// by the `/api/repo/resolve-type` route. Clients call `fetchRepoType()` to get an
// on-prem-aware answer without ever seeing the configured host lists.

export type RepoType = 'github' | 'gitlab' | 'bitbucket' | 'web';

export interface OnPremHostLists {
  github?: string[];
  gitlab?: string[];
  bitbucket?: string[];
}

// Parse a comma / whitespace separated host list (from a server-only env var).
export const parseHosts = (value?: string): string[] =>
  (value ?? '')
    .split(/[\s,]+/)
    .map(h => h.trim().toLowerCase())
    .filter(Boolean);

// Reduce an input that may be a bare hostname, or `proto://host:port`, or a full
// URL, down to a lowercase hostname (no scheme, no port, no path).
const toHostname = (input: string): string => {
  let host = input.trim().toLowerCase();
  host = host.replace(/^[a-z][a-z0-9+.-]*:\/\//, ''); // strip scheme
  host = host.split('/')[0]; // strip path
  host = host.split('@').pop() as string; // strip userinfo
  host = host.split(':')[0]; // strip port
  return host;
};

const hostMatches = (host: string, configured: string): boolean =>
  host === configured || host.endsWith(`.${configured}`);

// Resolve a provider type from a URL/host. Optional on-prem host lists (supplied
// server-side) take precedence over the built-in public-host heuristics.
export function resolveRepoTypeFromDomain(
  domainOrHost: string | null | undefined,
  hosts: OnPremHostLists = {},
): RepoType {
  if (!domainOrHost) return 'web';
  const host = toHostname(domainOrHost);
  if (!host) return 'web';

  if ((hosts.github ?? []).some(h => hostMatches(host, h))) return 'github';
  if ((hosts.gitlab ?? []).some(h => hostMatches(host, h))) return 'gitlab';
  if ((hosts.bitbucket ?? []).some(h => hostMatches(host, h))) return 'bitbucket';

  if (host === 'github.com' || host.includes('github')) return 'github';
  if (host === 'gitlab.com' || host.includes('gitlab')) return 'gitlab';
  if (host === 'bitbucket.org' || host.includes('bitbucket')) return 'bitbucket';

  return 'web';
}

// True for the three providers the backend can clone (i.e. not 'web'/'local').
export function isKnownProvider(
  type: string,
): type is 'github' | 'gitlab' | 'bitbucket' {
  return type === 'github' || type === 'gitlab' || type === 'bitbucket';
}

// Client helper: ask the server to resolve the provider type (applies on-prem
// host overrides that are never shipped to the browser). Falls back to the pure
// public-host heuristic if the request fails (offline / server error).
export async function fetchRepoType(url: string): Promise<RepoType> {
  try {
    const res = await fetch(`/api/repo/resolve-type?url=${encodeURIComponent(url)}`);
    if (res.ok) {
      const data = await res.json();
      const t = data?.type;
      if (t === 'github' || t === 'gitlab' || t === 'bitbucket' || t === 'web') {
        return t;
      }
    }
  } catch {
    // fall through to the local heuristic
  }
  return resolveRepoTypeFromDomain(url);
}
