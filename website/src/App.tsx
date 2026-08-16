import logoUrl from "../ChatGPT Image Aug 16, 2026, 10_57_58 PM.png";
import "./App.css";

export function App() {
  return (
    <main className="loading-page" aria-busy="true">
      <section className="loading-shell" aria-label="Subify website loading">
        <img className="loading-logo" src={logoUrl} alt="" aria-hidden="true" />
        <h1 className="loading-wordmark">Subify</h1>
        <div className="loading-state" role="status" aria-live="polite">
          <span>Loading</span>
          <span className="loading-dots" aria-hidden="true">
            <span />
            <span />
            <span />
          </span>
        </div>
      </section>
    </main>
  );
}
