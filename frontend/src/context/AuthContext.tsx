import React, { createContext, useContext, useState } from 'react';
import type { Student, Coordinator } from '../types';

interface AuthContextType {
    student: Student | null;
    coordinator: Coordinator | null;
    token: string | null;
    role: 'student' | 'coordinator' | null;
    loginStudent: (token: string, student: Student) => void;
    loginCoordinator: (token: string, coordinator: Coordinator) => void;
    logout: () => void;
    isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType>({} as AuthContextType);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [token, setToken] = useState<string | null>(() => localStorage.getItem('sp_token'));
    const [role, setRole] = useState<'student' | 'coordinator' | null>(
        () => localStorage.getItem('sp_role') as 'student' | 'coordinator' | null
    );
    const [student, setStudent] = useState<Student | null>(() => {
        const s = localStorage.getItem('sp_student');
        return s ? JSON.parse(s) : null;
    });
    const [coordinator, setCoordinator] = useState<Coordinator | null>(() => {
        const c = localStorage.getItem('sp_coordinator');
        return c ? JSON.parse(c) : null;
    });

    const loginStudent = (tkn: string, s: Student) => {
        setToken(tkn); setRole('student'); setStudent(s);
        localStorage.setItem('sp_token', tkn);
        localStorage.setItem('sp_role', 'student');
        localStorage.setItem('sp_student', JSON.stringify(s));
    };

    const loginCoordinator = (tkn: string, c: Coordinator) => {
        setToken(tkn); setRole('coordinator'); setCoordinator(c);
        localStorage.setItem('sp_token', tkn);
        localStorage.setItem('sp_role', 'coordinator');
        localStorage.setItem('sp_coordinator', JSON.stringify(c));
    };

    const logout = () => {
        setToken(null); setRole(null); setStudent(null); setCoordinator(null);
        ['sp_token', 'sp_role', 'sp_student', 'sp_coordinator'].forEach(k => localStorage.removeItem(k));
    };

    return (
        <AuthContext.Provider value={{
            student, coordinator, token, role,
            loginStudent, loginCoordinator, logout,
            isAuthenticated: !!token,
        }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext);
