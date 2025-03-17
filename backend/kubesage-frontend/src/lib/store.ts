"use client";

import { useEffect } from 'react';
import { create } from 'zustand';
// Now you can safely use browser APIs

// Check if we're running in the browser environment
const isBrowser = typeof window !== 'undefined';

// Safe way to access localStorage
const getInitialDarkMode = () => {
  if (!isBrowser) return false; // Default to light mode on the server
  
  // Check localStorage for saved preference
  if (localStorage.theme === 'dark') return true;
  
  // Otherwise, check system preference
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return true;
  }
  
  return false; // Default to light mode
};

// Type definitions
type State = {
  // UI State
  darkMode: boolean;
  toggleDarkMode: () => void;
  setDarkMode: (value: boolean) => void;
  
  // Selected cluster
  selectedKubeconfig: any | null;
  setSelectedKubeconfig: (kubeconfig: any | null) => void;
};

// Create the store
const useStore = create<State>((set) => ({
  // UI State
  darkMode: getInitialDarkMode(),
  toggleDarkMode: () => set((state) => {
    const newDarkMode = !state.darkMode;
    if (isBrowser) {
      localStorage.theme = newDarkMode ? 'dark' : 'light';
    }
    return { darkMode: newDarkMode };
  }),
  setDarkMode: (value: boolean) => {
    if (isBrowser) {
      localStorage.theme = value ? 'dark' : 'light';
    }
    set({ darkMode: value });
  },
  
  // Selected cluster
  selectedKubeconfig: null,
  setSelectedKubeconfig: (kubeconfig) => set({ selectedKubeconfig: kubeconfig }),
}));

// For example, with chart libraries:
import dynamic from 'next/dynamic';

const Chart = dynamic(() => import('react-apexcharts'), { ssr: false });

export default useStore;