import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { Project } from "../api/types";

const STORAGE_KEY = "sa_current_project";

interface ProjectValue {
  currentProjectId: string | null;
  setCurrentProject: (project: Project | null) => void;
}

const CurrentProjectContext = createContext<ProjectValue | null>(null);

export function CurrentProjectProvider({ children }: { children: ReactNode }) {
  const [currentProjectId, setCurrentProjectId] = useState<string | null>(
    () => localStorage.getItem(STORAGE_KEY),
  );

  useEffect(() => {
    if (currentProjectId) localStorage.setItem(STORAGE_KEY, currentProjectId);
    else localStorage.removeItem(STORAGE_KEY);
  }, [currentProjectId]);

  const value = useMemo(
    () => ({
      currentProjectId,
      setCurrentProject: (project: Project | null) => setCurrentProjectId(project?.id ?? null),
    }),
    [currentProjectId],
  );

  return (
    <CurrentProjectContext.Provider value={value}>{children}</CurrentProjectContext.Provider>
  );
}

export function useCurrentProject(): ProjectValue {
  const context = useContext(CurrentProjectContext);
  if (!context) throw new Error("useCurrentProject must be used within CurrentProjectProvider");
  return context;
}
