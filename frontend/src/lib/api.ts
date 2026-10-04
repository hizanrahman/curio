import { supabase } from "@/lib/supabase";

const configuredApiUrl = import.meta.env.VITE_API_URL?.trim();

export const API_BASE_URL = (configuredApiUrl || "http://localhost:8000").replace(/\/+$/, "");

export async function authorizedFetch(input: RequestInfo | URL, init: RequestInit = {}) {
  if (!configuredApiUrl && import.meta.env.PROD) {
    throw new Error("The production API URL has not been configured.");
  }
  if (!supabase) {
    throw new Error("Sign-in is not configured. Set the Supabase frontend environment variables.");
  }
  const { data, error } = await supabase.auth.getSession();
  if (error) throw new Error("Unable to verify your sign-in. Please sign in again.");
  const accessToken = data.session?.access_token;
  if (!accessToken) throw new Error("Please sign in to continue.");

  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${accessToken}`);
  return fetch(input, { ...init, headers });
}
