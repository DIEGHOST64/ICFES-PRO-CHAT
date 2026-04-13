import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import type { Theme } from '../types';

interface ThemeContextType {
    theme: Theme;
    toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType>({
    theme: 'light',
    toggleTheme: () => { },
});

type ThemeScope = 'public' | 'student' | 'coordinator';

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const location = useLocation();

    // Determine current scope
    const currentScope: ThemeScope = useMemo(() => {
        const path = location.pathname;
        if (path.startsWith('/chat') || path.startsWith('/practica')) return 'student';
        if (path.startsWith('/coordinador/dashboard')) return 'coordinator';
        return 'public';
    }, [location.pathname]);

    // Independent theme states
    const [themes, setThemes] = useState<Record<ThemeScope, Theme>>(() => {
        return {
            public: (localStorage.getItem('saberpro-theme-public') as Theme) ?? 'light',
            student: (localStorage.getItem('saberpro-theme-student') as Theme) ?? 'light',
            coordinator: (localStorage.getItem('saberpro-theme-coordinator') as Theme) ?? 'light',
        };
    });

    const activeTheme = themes[currentScope];

    // Apply active theme to DOM and save to localStorage
    useEffect(() => {
        document.documentElement.setAttribute('data-theme', activeTheme);
        localStorage.setItem(`saberpro-theme-${currentScope}`, activeTheme);
    }, [activeTheme, currentScope]);

    const toggleTheme = () => {
        setThemes(prev => ({
            ...prev,
            [currentScope]: prev[currentScope] === 'dark' ? 'light' : 'dark'
        }));
    };

    return (
        <ThemeContext.Provider value={{ theme: activeTheme, toggleTheme }}>
            {children}
        </ThemeContext.Provider>
    );
};

export const useTheme = () => useContext(ThemeContext);
