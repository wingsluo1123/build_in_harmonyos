export interface KeyView { label: string; action: number; shift: boolean; capsLock: boolean; }
export interface KeyEvent { action: number; text: string; shift: boolean; capsLock: boolean; }
export const rowCount: () => number;
export const keyCount: (row: number) => number;
export const keyAt: (row: number, column: number) => KeyView;
export const activate: (row: number, column: number) => KeyEvent;
export const setCapsLock: (enabled: boolean) => void;
export const resetSession: () => void;
export const dismiss: () => void;
