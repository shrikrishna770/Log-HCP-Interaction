import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { clearForm, setFormState } from './store/crmSlice';
import CRMForm from './components/CRMForm';
import ChatPanel from './components/ChatPanel';
import { Sparkles, Trash2, Cpu, FileText, CheckCircle, Database, RefreshCw } from 'lucide-react';
import { apiService } from './services/api';

export default function App() {
  const dispatch = useDispatch();
  const formState = useSelector((state) => state.crm.formState);
  const [interactions, setInteractions] = useState([]);

  // Fetch recent interactions on mount
  const fetchRecent = async () => {
    try {
      const data = await apiService.getInteractions();
      setInteractions(data);
    } catch (e) {
      console.error("Failed to load interactions:", e);
    }
  };

  useEffect(() => {
    fetchRecent();
  }, [formState.id]); // re-fetch when form mode edits

  const handleReset = () => {
    if (window.confirm("Are you sure you want to clear the form?")) {
      dispatch(clearForm());
    }
  };

  return (
    <div className="app-container">
      {/* Premium Header */}
      <header className="app-header">
        <div className="header-branding">
          <div className="logo-icon">
            <Cpu size={24} className="text-indigo-400 animate-pulse" />
          </div>
          <div>
            <h1>MedCRM AI</h1>
            <p>Intelligent HCP Engagement & Interaction Logger</p>
          </div>
        </div>
        <div className="header-actions">
          <button 
            type="button" 
            className="reset-btn flex items-center gap-1"
            onClick={handleReset}
          >
            <Trash2 size={16} />
            Reset Form
          </button>
        </div>
      </header>

      {/* Main Grid Workspace */}
      <main className="app-workspace">
        <div className="left-panel">
          <CRMForm onInteractionLogged={fetchRecent} />
        </div>
        <div className="right-panel">
          <ChatPanel />
        </div>
      </main>

      {/* Database/Recent Activity Feed */}
      <section className="activity-feed">
        <h3 className="activity-feed-title">
          <Database size={18} />
          Logged Database Interactions ({interactions.length})
          <button 
            type="button" 
            className="refresh-btn"
            onClick={fetchRecent}
          >
            <RefreshCw size={12} />
            Refresh
          </button>
        </h3>
        {interactions.length === 0 ? (
          <p className="text-gray-400 text-sm">No interactions logged in database yet.</p>
        ) : (
          <div className="interactions-grid">
            {interactions.map(item => (
              <div 
                key={item.id} 
                className="interaction-card"
                onClick={() => {
                  // Load interaction into form for editing
                  dispatch(clearForm());
                  dispatch(setFormState({
                    id: item.id,
                    hcp_id: item.hcp_id,
                    hcp_name: item.hcp.name,
                    type: item.type,
                    datetime: item.datetime.substring(0, 16),
                    attendees: item.attendees,
                    topics: item.topics,
                    sentiment: item.sentiment,
                    outcomes: item.outcomes,
                    follow_ups: item.follow_ups,
                    shared_material_ids: item.shared_materials.map(m => m.id),
                    distributed_sample_ids: item.distributed_samples.map(s => s.id)
                  }));
                }}
              >
                <div className="card-header flex justify-between">
                  <strong>{item.hcp.name}</strong>
                  <span className={`sentiment-badge ${item.sentiment.toLowerCase()}`}>
                    {item.sentiment}
                  </span>
                </div>
                <div className="card-meta">
                  <span>Type: {item.type}</span> | <span>{new Date(item.datetime).toLocaleDateString()}</span>
                </div>
                <div className="card-body">
                  <p className="truncate-2-lines"><strong>Topics:</strong> {item.topics || 'N/A'}</p>
                </div>
                <div className="card-relations flex gap-2 mt-2 flex-wrap">
                  {item.shared_materials.map(m => (
                    <span key={m.id} className="small-chip shared">{m.name}</span>
                  ))}
                  {item.distributed_samples.map(s => (
                    <span key={s.id} className="small-chip sample">{s.name}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Footer / Architecture Summary */}
      <footer className="app-footer">
        <div className="footer-details">
          <p>
            Powered by <strong>LangGraph Orchestration</strong> &amp; <strong>Groq Cloud API (gemma2-9b-it)</strong>.
          </p>
          <p className="text-gray-500 text-xs">
            Completed as a high-fidelity pharmaceutical CRM prototype. Auto-syncs chat-extracted items and manual forms.
          </p>
        </div>
      </footer>
    </div>
  );
}
