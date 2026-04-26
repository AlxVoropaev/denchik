import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { ThemeSelector, applyStoredTheme, THEMES } from "./ThemeSelector";

function reset() {
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
}

describe("ThemeSelector", () => {
  beforeEach(reset);
  afterEach(reset);

  it("offers four named themes and defaults to github-light", () => {
    applyStoredTheme();
    expect(document.documentElement.getAttribute("data-theme")).toBe("github-light");

    render(<ThemeSelector />);
    const select = screen.getByLabelText(/color theme/i) as HTMLSelectElement;
    expect(select.value).toBe("github-light");
    expect([...select.options].map((o) => o.value)).toEqual([
      "github-light",
      "github-dark",
      "monokai-pro-light",
      "monokai-pro-dark",
    ]);
    expect(THEMES.map((t) => t.label)).toEqual([
      "GitHub Light",
      "GitHub Dark",
      "Monokai Pro Light",
      "Monokai Pro Dark",
    ]);
  });

  it("restores stored theme on mount and persists user changes", () => {
    localStorage.setItem("theme", "monokai-pro-dark");
    applyStoredTheme();
    expect(document.documentElement.getAttribute("data-theme")).toBe("monokai-pro-dark");

    render(<ThemeSelector />);
    const select = screen.getByLabelText(/color theme/i) as HTMLSelectElement;
    expect(select.value).toBe("monokai-pro-dark");

    fireEvent.change(select, { target: { value: "github-dark" } });
    expect(document.documentElement.getAttribute("data-theme")).toBe("github-dark");
    expect(localStorage.getItem("theme")).toBe("github-dark");
  });

  it("falls back to default when stored value is invalid", () => {
    localStorage.setItem("theme", "totally-bogus");
    applyStoredTheme();
    expect(document.documentElement.getAttribute("data-theme")).toBe("github-light");
  });

  it("trusts a valid data-theme attribute set by the bootstrap script even with no localStorage entry", () => {
    document.documentElement.setAttribute("data-theme", "monokai-pro-light");
    render(<ThemeSelector />);
    const select = screen.getByLabelText(/color theme/i) as HTMLSelectElement;
    expect(select.value).toBe("monokai-pro-light");
  });

  it("ignores an invalid data-theme attribute and falls back to stored / default", () => {
    document.documentElement.setAttribute("data-theme", "nonsense");
    render(<ThemeSelector />);
    const select = screen.getByLabelText(/color theme/i) as HTMLSelectElement;
    expect(select.value).toBe("github-light");
  });

  it("does not write to localStorage on initial mount when the user has not chosen", () => {
    applyStoredTheme();
    render(<ThemeSelector />);
    expect(localStorage.getItem("theme")).toBeNull();
  });
});
