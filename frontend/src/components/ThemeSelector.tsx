import { useEffect, useState } from "react";

export const THEMES = [
  { value: "github-light", label: "GitHub Light" },
  { value: "github-dark", label: "GitHub Dark" },
  { value: "monokai-pro-light", label: "Monokai Pro Light" },
  { value: "monokai-pro-dark", label: "Monokai Pro Dark" },
] as const;

export type ThemeId = (typeof THEMES)[number]["value"];

const VALID = new Set<string>(THEMES.map((t) => t.value));
const DEFAULT: ThemeId = "github-light";
const STORAGE_KEY = "theme";

function readStored(): ThemeId {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v && VALID.has(v)) return v as ThemeId;
  } catch {
    // ignore — private mode, etc.
  }
  return DEFAULT;
}

export function applyStoredTheme(): void {
  document.documentElement.setAttribute("data-theme", readStored());
}

export function ThemeSelector() {
  const [theme, setTheme] = useState<ThemeId>(() => {
    const current = document.documentElement.getAttribute("data-theme");
    return current && VALID.has(current) ? (current as ThemeId) : readStored();
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // ignore
    }
  }, [theme]);

  return (
    <select
      id="theme-select"
      aria-label="Theme"
      value={theme}
      onChange={(e) => setTheme(e.target.value as ThemeId)}
    >
      {THEMES.map((t) => (
        <option key={t.value} value={t.value}>
          {t.label}
        </option>
      ))}
    </select>
  );
}
