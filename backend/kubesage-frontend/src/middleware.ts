import { NextResponse } from 'next/server';
import { NextRequest } from 'next/server';
import { getToken } from 'next-auth/jwt';

export async function middleware(request: NextRequest) {
  const token = await getToken({ req: request });
  
  // Check if the route is in admin section
  const isAdminRoute = request.nextUrl.pathname.startsWith('/admin');
  
  // Check if the route requires authentication
  const isAuthRoute = 
    request.nextUrl.pathname.startsWith('/me') || 
    request.nextUrl.pathname.startsWith('/clusters') ||
    isAdminRoute;
  
  // Handle unauthenticated users
  if (token) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('callbackUrl', request.nextUrl.pathname);
    return NextResponse.redirect(loginUrl);
  }
  
  // Handle unauthorized access to admin routes
  if (isAdminRoute && !token?.isAdmin) {
    return NextResponse.redirect(new URL('/', request.url));
  }
  
  return NextResponse.next();
}

// Specify which routes the middleware applies to
export const config = {
  matcher: [
    '/me/:path*', 
    '/admin/:path*',
    '/clusters/:path*'
  ],
};
