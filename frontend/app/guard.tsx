import { auth0 } from "@/lib/auth0";
import { redirect } from "next/navigation";

export async function requireAuth() {
  const session = await auth0.getSession();
  if (!session) {
    redirect("/login");
  }
  return session;
}