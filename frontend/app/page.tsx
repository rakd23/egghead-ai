import { auth0 } from "@/lib/auth0";
import { redirect } from "next/navigation";
import Chat from "./chat";

export default async function Home() {
  const session = await auth0.getSession();
  if (!session) redirect("/login");
  if (!session.user.email?.endsWith("@ucdavis.edu")) redirect("/auth/logout");
  return <Chat />;
}