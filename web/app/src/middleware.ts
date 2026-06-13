import { NextResponse, type NextRequest } from "next/server";

function isMutatingAppApiRoute(req: NextRequest): boolean {
  return req.nextUrl.pathname.startsWith("/app/api/") && ["POST", "PUT", "PATCH", "DELETE"].includes(req.method);
}

function authModeIsLocal(): boolean {
  const rawAuthMode = (process.env.AUTH_MODE ?? process.env.NEXT_PUBLIC_AUTH_MODE ?? "local").trim().toLowerCase();
  return rawAuthMode === "local";
}

function localWriteIsSameOrigin(req: NextRequest): boolean {
  const rawOrigin = req.headers.get("origin");
  if (rawOrigin) {
    try {
      return new URL(rawOrigin).origin === req.nextUrl.origin;
    } catch {
      return false;
    }
  }

  const rawReferer = req.headers.get("referer");
  if (!rawReferer) return false;
  try {
    return new URL(rawReferer).origin === req.nextUrl.origin;
  } catch {
    return false;
  }
}

export default function middleware(req: NextRequest) {
  if (!authModeIsLocal()) {
    return NextResponse.json({ detail: "Invalid AUTH_MODE. Expected 'local'." }, { status: 500 });
  }

  if (isMutatingAppApiRoute(req) && !localWriteIsSameOrigin(req)) {
    return NextResponse.json({ detail: "Cross-origin local write request rejected." }, { status: 403 });
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next|.*\\..*).*)", "/(api|trpc)(.*)"],
};
