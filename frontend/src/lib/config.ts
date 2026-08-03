export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export const SITE_BASE_URL =
  process.env.NEXT_PUBLIC_SITE_BASE_URL || "http://localhost:3000";

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
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
