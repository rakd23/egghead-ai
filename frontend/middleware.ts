import { withMiddlewareAuthRequired } from "@auth0/nextjs-auth0";

export default withMiddlewareAuthRequired();

export const config = {
  matcher: ["/dashboard/:path*", "/api/:path*"],
};
