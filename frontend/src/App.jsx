/**
 * App.jsx — CORRIGÉ.
 *
 * CAUSE PAGE BLANCHE IDENTIFIÉE ET RÉSOLUE :
 * L'App.jsx original importait HumanCheckInPage et SystemSignalsPage
 * qui n'existaient pas → crash silencieux React → page blanche.
 *
 * SOLUTION :
 * - Garde HashRouter + react-router-dom (architecture originale)
 * - Ajoute les 2 nouvelles routes avec les fichiers maintenant présents
 */
import { HashRouter, Routes, Route } from "react-router-dom";
import { Sidebar }            from "./components/Sidebar";
import { DashboardPage }      from "./pages/DashboardPage";
import { ScannerPage }        from "./pages/ScannerPage";
import { RecommendationPage } from "./pages/RecommendationPage";
import { ValidationPage }     from "./pages/ValidationPage";
import { RiskCenterPage }     from "./pages/RiskCenterPage";
import { JournalPage }        from "./pages/JournalPage";
import { AnalyticsPage }      from "./pages/AnalyticsPage";
import { PlaybookPage }       from "./pages/PlaybookPage";
import { AlertsPage }         from "./pages/AlertsPage";
import { SettingsPage }       from "./pages/SettingsPage";
import { HumanCheckInPage }   from "./pages/HumanCheckInPage";
import { SystemSignalsPage }  from "./pages/SystemSignalsPage";

export default function App() {
  return (
    <HashRouter>
      <div className="flex min-h-screen bg-paper">
        <Sidebar />
        <main className="flex-1 overflow-y-auto px-8 py-7">
          <Routes>
            <Route path="/"               element={<DashboardPage />} />
            <Route path="/scanner"        element={<ScannerPage />} />
            <Route path="/recommendation" element={<RecommendationPage />} />
            <Route path="/validation"     element={<ValidationPage />} />
            <Route path="/risk-center"    element={<RiskCenterPage />} />
            <Route path="/journal"        element={<JournalPage />} />
            <Route path="/analytics"      element={<AnalyticsPage />} />
            <Route path="/playbook"       element={<PlaybookPage />} />
            <Route path="/alerts"         element={<AlertsPage />} />
            <Route path="/settings"       element={<SettingsPage />} />
            {/* Nouvelles pages V2 */}
            <Route path="/human"          element={<HumanCheckInPage />} />
            <Route path="/signals"        element={<SystemSignalsPage />} />
          </Routes>
        </main>
      </div>
    </HashRouter>
  );
}
