"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

/**
 * "Active farm" scopes which farm subsequent actions (dashboard, predictions)
 * apply to. There is no backend field for it — DATABASE_SPECIFICATION.md's
 * farms table has no is_active/active_farm_id column — so it is tracked
 * purely client-side and persisted to localStorage for convenience.
 */
const ACTIVE_FARM_KEY = "greenguard_active_farm_id";

interface ActiveFarmContextValue {
  activeFarmId: string | null;
  setActiveFarmId: (farmId: string | null) => void;
}

const ActiveFarmContext = createContext<ActiveFarmContextValue | undefined>(undefined);

export function ActiveFarmProvider({ children }: { children: React.ReactNode }) {
  const [activeFarmId, setActiveFarmIdState] = useState<string | null>(null);

  useEffect(() => {
    setActiveFarmIdState(window.localStorage.getItem(ACTIVE_FARM_KEY));
  }, []);

  const setActiveFarmId = useCallback((farmId: string | null) => {
    setActiveFarmIdState(farmId);
    if (farmId) {
      window.localStorage.setItem(ACTIVE_FARM_KEY, farmId);
    } else {
      window.localStorage.removeItem(ACTIVE_FARM_KEY);
    }
  }, []);

  const value = useMemo(
    () => ({ activeFarmId, setActiveFarmId }),
    [activeFarmId, setActiveFarmId]
  );

  return <ActiveFarmContext.Provider value={value}>{children}</ActiveFarmContext.Provider>;
}

export function useActiveFarm(): ActiveFarmContextValue {
  const context = useContext(ActiveFarmContext);
  if (!context) {
    throw new Error("useActiveFarm must be used within an ActiveFarmProvider.");
  }
  return context;
}
