import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export default function proxy(request: NextRequest) {
  const url = request.nextUrl.clone();
  const host = request.headers.get("host") || "";

  // Prevent rewriting static files, images, next-internals or API requests
  if (
    url.pathname.startsWith("/_next") ||
    url.pathname.startsWith("/api") ||
    url.pathname.includes(".")
  ) {
    return NextResponse.next();
  }

  const hostname = host.split(":")[0];
  const parts = hostname.split(".");

  let subdomain = "";
  
  if (hostname.endsWith("localhost")) {
    // E.g., journalist.localhost -> parts: ["journalist", "localhost"]
    // E.g., editor.localhost -> parts: ["editor", "localhost"]
    if (parts.length > 1 && parts[parts.length - 2] !== "localhost") {
      subdomain = parts.slice(0, -1).join(".");
    }
  } else {
    // E.g., journalist.newspaper.com -> parts: ["journalist", "newspaper", "com"]
    if (parts.length > 2) {
      subdomain = parts.slice(0, -2).join(".");
    }
  }

  if (subdomain) {
    const allowedSubdomains = ["superadmin", "admin", "editor", "journalist", "user"];
    if (allowedSubdomains.includes(subdomain)) {
      if (!url.pathname.startsWith(`/panels/${subdomain}`)) {
        url.pathname = `/panels/${subdomain}${url.pathname === "/" ? "" : url.pathname}`;
        return NextResponse.rewrite(url);
      }
    }
  }

  return NextResponse.next();
}


export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    "/((?!api|_next/static|_next/image|favicon.ico|favicon.png|icon.png).*)",
  ],
};

