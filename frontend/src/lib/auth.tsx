import { useEffect, useMemo, useState, type ReactNode } from "react";
import { supabase } from "@/lib/supabase";
import { AuthContext } from "@/lib/auth-context";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<import("@supabase/supabase-js").Session | null>(null);
  const [isLoading, setIsLoading] = useState(Boolean(supabase));
  const [isPasswordRecovery, setIsPasswordRecovery] = useState(false);

  useEffect(() => {
    if (!supabase) return;
    let active = true;
    let authEventReceived = false;
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, nextSession) => {
      authEventReceived = true;
      setSession(nextSession);
      if (event === "PASSWORD_RECOVERY") setIsPasswordRecovery(true);
      if (event === "SIGNED_IN" || event === "SIGNED_OUT" || event === "USER_UPDATED") {
        setIsPasswordRecovery(false);
      }
      setIsLoading(false);
    });
    void supabase.auth.getSession().then(({ data, error }) => {
      if (error) console.error("Unable to restore sign-in session:", error.message);
      if (active) {
        if (!authEventReceived) setSession(data.session);
        setIsLoading(false);
      }
    });
    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, []);

  const value = useMemo(
    () => ({ session, isLoading, isPasswordRecovery }),
    [session, isLoading, isPasswordRecovery],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
