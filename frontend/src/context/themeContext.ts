import { createContext } from "react";

export type ThemeType = "light" | "dark";

export const light = {
  background: "#EEF0F4",
  foreground: "#F4F6F8",
};

export const dark = {
  background: "#2A3141",
  foreground: "#394153",
};

export const ThemeContext = createContext<ThemeType>("light");
