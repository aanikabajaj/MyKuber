import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Toaster } from "sonner";
import App from "./App";
import { AuthProvider } from "./context/AuthContext";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
        <Toaster
          position="top-right"
          theme="dark"
          richColors
          toastOptions={{ style: { background: "hsl(224 40% 9%)", border: "1px solid hsl(223 30% 20%)" } }}
        />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
);
