import { createContext, useContext, useState, useCallback } from 'react';
import type { ReactNode } from 'react';

// ── Visual Mood types ────────────────────────────────────
export type VisualMood = 'idle' | 'authenticated' | 'processing';

interface VisualMoodContextType {
    mood: VisualMood;
    setMood: (mood: VisualMood) => void;
}

const VisualMoodContext = createContext<VisualMoodContextType>({
    mood: 'idle',
    setMood: () => { },
});

// ── Provider ─────────────────────────────────────────────
export const VisualMoodProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [mood, setMoodRaw] = useState<VisualMood>('idle');
    const setMood = useCallback((m: VisualMood) => setMoodRaw(m), []);

    return (
        <VisualMoodContext.Provider value={{ mood, setMood }}>
            {children}
        </VisualMoodContext.Provider>
    );
};

// ── Hook ─────────────────────────────────────────────────
export const useVisualMood = () => useContext(VisualMoodContext);
