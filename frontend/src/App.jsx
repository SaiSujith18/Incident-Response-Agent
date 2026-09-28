import { useState } from "react";
import { Activity, Brain, Database, Search, ShieldCheck } from "lucide-react";
import { analyzeIncident, detectPatterns } from "./services/api";
import "./App.css";

function App() {
  const [incident, setIncident] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [pattern, setPattern] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleAnalyze = async () => {
    if (!incident.trim()) {
      setError("Please describe the incident first.");
      return;
    }

    try {
      setLoading(true);
      setError("");

      const [analysisResult, patternResult] = await Promise.all([
        analyzeIncident(incident),
        detectPatterns(incident),
      ]);

      setAnalysis(analysisResult);
      setPattern(patternResult);
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to analyze the incident.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      {/* HEADER */}
      <header className="navbar">
        <div className="brand">
          <div className="brand-icon">
            <Brain size={24} />
          </div>

          <div>
            <h1>MemoryOps</h1>
            <p>AI Incident Response</p>
          </div>
        </div>

        <div className="system-status">
          <span className="status-dot"></span>
          System Online
        </div>
      </header>

      <main className="container">
        {/* HERO */}
        <section className="hero">
          <div>
            <span className="eyebrow">INTELLIGENT INCIDENT RESPONSE</span>

            <h2>
              Turn past incidents into
              <span> operational intelligence.</span>
            </h2>

            <p>
              MemoryOps analyzes the current incident against historical
              organizational memory to identify patterns, successful
              approaches, failed approaches, and recommended investigations.
            </p>
          </div>
        </section>

        {/* INCIDENT INPUT */}
        <section className="incident-panel">
          <div className="section-heading">
            <div className="heading-icon">
              <Activity size={20} />
            </div>

            <div>
              <h3>Current Incident</h3>
              <p>Describe the production or security incident.</p>
            </div>
          </div>

          <textarea
            value={incident}
            onChange={(e) => setIncident(e.target.value)}
            placeholder="Example: The production database is rejecting connections because the database connection pool is exhausted."
          />

          {error && <div className="error">{error}</div>}

          <button
            className="analyze-button"
            onClick={handleAnalyze}
            disabled={loading}
          >
            {loading ? (
              "Analyzing..."
            ) : (
              <>
                <Search size={18} />
                Analyze Incident
              </>
            )}
          </button>
        </section>

        {/* LOADING */}
        {loading && (
          <div className="loading-card">
            <div className="spinner"></div>
            <div>
              <strong>MemoryOps is investigating...</strong>
              <p>
                Searching organizational memory and detecting historical
                patterns.
              </p>
            </div>
          </div>
        )}

        {/* RESULTS */}
        {!loading && (analysis || pattern) && (
          <>
            {/* SUMMARY CARDS */}
            <section className="stats-grid">
              <div className="stat-card">
                <Database size={22} />
                <div>
                  <span>Historical Memories</span>
                  <strong>
                    {analysis?.evidence_count ??
                      pattern?.evidence_count ??
                      0}
                  </strong>
                </div>
              </div>

              <div className="stat-card">
                <Brain size={22} />
                <div>
                  <span>Pattern Detection</span>
                  <strong>Active</strong>
                </div>
              </div>

              <div className="stat-card">
                <ShieldCheck size={22} />
                <div>
                  <span>Human Approval</span>
                  <strong>Required</strong>
                </div>
              </div>
            </section>

            {/* ANALYSIS */}
            {analysis?.analysis && (
              <section className="result-card">
                <div className="result-header">
                  <div className="heading-icon">
                    <Brain size={20} />
                  </div>

                  <div>
                    <h3>Incident Analysis</h3>
                    <p>AI-assisted investigation using historical memory</p>
                  </div>
                </div>

                <div className="result-content">
                  <pre>{analysis.analysis}</pre>
                </div>
              </section>
            )}

            {/* PATTERN */}
            {pattern?.pattern && (
              <section className="result-card">
                <div className="result-header">
                  <div className="heading-icon">
                    <Activity size={20} />
                  </div>

                  <div>
                    <h3>Multi-Incident Pattern</h3>
                    <p>Recurring organizational patterns</p>
                  </div>
                </div>

                <div className="result-content">
                  <pre>{pattern.pattern}</pre>
                </div>
              </section>
            )}

            {/* MEMORY */}
            {analysis?.memories?.length > 0 && (
              <section className="result-card">
                <div className="result-header">
                  <div className="heading-icon">
                    <Database size={20} />
                  </div>

                  <div>
                    <h3>Historical Evidence</h3>
                    <p>
                      Memories retrieved from organizational experience
                    </p>
                  </div>
                </div>

                <div className="memory-list">
                  {analysis.memories.map((memory, index) => (
                    <div className="memory-item" key={index}>
                      <span>{index + 1}</span>
                      <p>{memory}</p>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </main>

      <footer>
        <span>MemoryOps</span>
        <span>Human-in-the-loop incident response</span>
      </footer>
    </div>
  );
}

export default App;