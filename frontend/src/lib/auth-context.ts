import { createContext, useContext } from "react";
import type { Session } from "@supabase/supabase-js";

export interface AuthContextValue {
  session: Session | null;
  isLoading: boolean;
  isPasswordRecovery: boolean;
}

export const AuthContext = createContext<AuthContextValue>({
  session: null,
  isLoading: true,
  isPasswordRecovery: false,
});

export function useAuth() {
  return useContext(AuthContext);
}
