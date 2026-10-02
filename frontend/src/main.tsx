import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./App";
import { AuthProvider } from "./auth/AuthContext";
import { CurrentProjectProvider } from "./project/CurrentProjectContext";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <CurrentProjectProvider>
          <App />
        </CurrentProjectProvider>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
