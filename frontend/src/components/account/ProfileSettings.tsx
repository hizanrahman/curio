import { useEffect, useState } from "react";
import { toast } from "sonner";
import { API_BASE_URL, authorizedFetch } from "@/lib/api";
import { ThemeCard } from "@/components/theme/ThemeCard";
import { PersonalityPicker, type TutorPersonality } from "@/components/account/PersonalityPicker";

export function ProfileSettings() {
  const [personality, setPersonality] = useState<TutorPersonality>("chill_senior");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    let active = true;
    void authorizedFetch(`${API_BASE_URL}/api/account/profile`)
      .then(async response => {
        const data = await response.json().catch(() => null);
        if (!response.ok) throw new Error(data?.detail || "Profile settings could not be loaded.");
        if (active && data?.tutor_personality) setPersonality(data.tutor_personality);
      })
      .catch(error => toast.error(error instanceof Error ? error.message : "Profile settings could not be loaded."))
      .finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, []);

  const savePersonality = async (nextPersonality: TutorPersonality) => {
    const previousPersonality = personality;
    setPersonality(nextPersonality);
    setIsSaving(true);
    try {
      const response = await authorizedFetch(`${API_BASE_URL}/api/account/profile`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tutor_personality: nextPersonality }),
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok) throw new Error(payload?.detail || "Tutor personality could not be saved.");
      toast.success("Tutor personality updated for new messages.");
    } catch (error) {
      setPersonality(previousPersonality);
      toast.error(error instanceof Error ? error.message : "Tutor personality could not be saved.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <ThemeCard variant="white" className="space-y-6 p-5 sm:p-7">
      <div><h2 className="font-display text-2xl font-extrabold">Tutor preferences</h2><p className="mt-1 text-sm text-muted-foreground">Choose the tone your tutor uses for new messages.</p></div>
      {isLoading ? <div className="h-20 animate-pulse rounded-xl bg-secondary" role="status">Loading your preferences…</div> : (
        <>
          <fieldset className="space-y-3"><legend className="text-sm font-bold">Tutor personality</legend>
            <PersonalityPicker value={personality} onChange={value => void savePersonality(value)} />
            {isSaving && <span role="status" className="text-xs text-muted-foreground">Updating tutor tone…</span>}
          </fieldset>
        </>
      )}
    </ThemeCard>
  );
}
