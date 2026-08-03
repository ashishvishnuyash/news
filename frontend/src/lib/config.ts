export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL || ""
).replace(/\/+$/, "");

const API_INTERNAL_URL = (
  process.env.API_INTERNAL_URL || ""
).replace(/\/+$/, "");

export const SITE_BASE_URL = (
  process.env.NEXT_PUBLIC_SITE_BASE_URL || ""
).replace(/\/+$/, "");

export function apiUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  // In browser client components, always use relative path so Next.js proxy rewrites handle backend requests without CORS errors
  if (typeof window !== "undefined") {
    return normalizedPath;
  }

  const serverBaseUrl = API_INTERNAL_URL || API_BASE_URL;
  if (serverBaseUrl.endsWith("/api") && normalizedPath.startsWith("/api/")) {
    return `${serverBaseUrl.slice(0, -4)}${normalizedPath}`;
  }
  return serverBaseUrl ? `${serverBaseUrl}${normalizedPath}` : normalizedPath;
}




export function siteUrl(path: string = "/"): string {
  return `${SITE_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

export function panelPathForRole(role: string): string {
  if (role === "READER") return "/panels/user";
  return `/panels/${role.toLowerCase().replace("_", "")}`;
}

export function panelUrlForRole(role: string): string {
  return siteUrl(panelPathForRole(role));
}
