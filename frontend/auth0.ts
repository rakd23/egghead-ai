import { Auth0Client } from "@auth0/nextjs-auth0/server";

export const auth0 = new Auth0Client();

export const handlers = auth0.handlers;
