import "./styles.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { configProblems } from "./lib/env";
import { ConfigError } from "./pages/ConfigError";

const root = document.getElementById("root");
if (!root) throw new Error("Missing #root element");

createRoot(root).render(
  <StrictMode>
    {configProblems.length > 0 ? <ConfigError problems={configProblems} /> : <App />}
  </StrictMode>,
);
