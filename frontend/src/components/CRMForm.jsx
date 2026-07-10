import React, { useState, useEffect, useRef } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { 
  updateFormField, 
  setFormState, 
  setSuggestedFollowUps, 
  setRecommendations,
  setHcpHistorySummary,
  addChatMessage,
  setLoading
} from '../store/crmSlice';
import { apiService } from '../services/api';
import { 
  User, Calendar, Users, FileText, Package, 
  Smile, Award, CheckCircle, ArrowRight, Mic, X, Search, Sparkles
} from 'lucide-react';

export default function CRMForm({ onInteractionLogged }) {
  const dispatch = useDispatch();
  const formState = useSelector((state) => state.crm.formState);
  const suggestedFollowUps = useSelector((state) => state.crm.suggestedFollowUps);
  const isLoading = useSelector((state) => state.crm.isLoading);
  
  // Autocomplete and search states
  const [hcpSearch, setHcpSearch] = useState('');
  const [hcpResults, setHcpResults] = useState([]);
  const [showHcpDropdown, setShowHcpDropdown] = useState(false);
  
  const [matSearch, setMatSearch] = useState('');
  const [matResults, setMatResults] = useState([]);
  const [showMatDropdown, setShowMatDropdown] = useState(false);
  
  const [sampSearch, setSampSearch] = useState('');
  const [sampResults, setSampResults] = useState([]);
  const [showSampDropdown, setShowSampDropdown] = useState(false);
  
  const [allMaterials, setAllMaterials] = useState([]);

  // Attendees local input state
  const [attendeeInput, setAttendeeInput] = useState('');
  
  // Voice note mock states
  const [isRecording, setIsRecording] = useState(false);

  // References for dropdown click-outs
  const hcpRef = useRef(null);
  const matRef = useRef(null);
  const sampRef = useRef(null);

  // Initial load: search default HCPs to show on focus
  useEffect(() => {
    apiService.searchHCPs('').then(setHcpResults).catch(console.error);
    apiService.searchMaterials('').then(res => {
      setAllMaterials(res);
      setMatResults(res.filter(m => m.type === 'Material'));
      setSampResults(res.filter(m => m.type === 'Sample'));
    }).catch(console.error);
  }, []);

  // Click outside to close dropdowns
  useEffect(() => {
    function handleClickOutside(event) {
      if (hcpRef.current && !hcpRef.current.contains(event.target)) setShowHcpDropdown(false);
      if (matRef.current && !matRef.current.contains(event.target)) setShowMatDropdown(false);
      if (sampRef.current && !sampRef.current.contains(event.target)) setShowSampDropdown(false);
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Sync HCP search text with formState name if set
  useEffect(() => {
    if (formState.hcp_name) {
      setHcpSearch(formState.hcp_name);
    } else {
      setHcpSearch('');
    }
  }, [formState.hcp_name]);

  // HCP autocomplete query
  const handleHcpSearchChange = async (e) => {
    const val = e.target.value;
    setHcpSearch(val);
    setShowHcpDropdown(true);
    try {
      const res = await apiService.searchHCPs(val);
      setHcpResults(res);
    } catch (err) {
      console.error(err);
    }
  };

  const selectHCP = async (hcp) => {
    dispatch(updateFormField({ field: 'hcp_id', value: hcp.id }));
    dispatch(updateFormField({ field: 'hcp_name', value: hcp.name }));
    setShowHcpDropdown(false);
    
    // Auto-fetch HCP History summary upon selection
    try {
      dispatch(setLoading(true));
      const res = await apiService.sendChatMessage(
        `Provide history context for Dr. ${hcp.name}`, 
        [], 
        { hcp_id: hcp.id }
      );
      if (res.reply) {
        dispatch(setHcpHistorySummary(res.reply));
        dispatch(addChatMessage({
          role: 'assistant',
          content: `Here is the history context for ${hcp.name}:\n\n${res.reply}`,
          toolCalls: res.tool_calls
        }));
      }
    } catch (e) {
      console.error(e);
    } finally {
      dispatch(setLoading(false));
    }
  };

  // Materials autocomplete query
  const handleMatSearchChange = async (e) => {
    const val = e.target.value;
    setMatSearch(val);
    setShowMatDropdown(true);
    try {
      const res = await apiService.searchMaterials(val);
      setMatResults(res.filter(m => m.type === 'Material'));
      setAllMaterials(prev => {
        const merged = [...prev];
        res.forEach(item => {
          if (!merged.some(m => m.id === item.id)) {
            merged.push(item);
          }
        });
        return merged;
      });
    } catch (err) {
      console.error(err);
    }
  };

  const addMaterial = (mat) => {
    const currentList = formState.shared_material_ids || [];
    if (!currentList.includes(mat.id)) {
      dispatch(updateFormField({
        field: 'shared_material_ids',
        value: [...currentList, mat.id]
      }));
    }
    setMatSearch('');
    setShowMatDropdown(false);
  };

  const removeMaterial = (id) => {
    const currentList = formState.shared_material_ids || [];
    dispatch(updateFormField({
      field: 'shared_material_ids',
      value: currentList.filter(mid => mid !== id)
    }));
  };

  // Samples autocomplete query
  const handleSampSearchChange = async (e) => {
    const val = e.target.value;
    setSampSearch(val);
    setShowSampDropdown(true);
    try {
      const res = await apiService.searchMaterials(val);
      setSampResults(res.filter(m => m.type === 'Sample'));
      setAllMaterials(prev => {
        const merged = [...prev];
        res.forEach(item => {
          if (!merged.some(m => m.id === item.id)) {
            merged.push(item);
          }
        });
        return merged;
      });
    } catch (err) {
      console.error(err);
    }
  };

  const addSample = (samp) => {
    const currentList = formState.distributed_sample_ids || [];
    if (!currentList.includes(samp.id)) {
      dispatch(updateFormField({
        field: 'distributed_sample_ids',
        value: [...currentList, samp.id]
      }));
    }
    setSampSearch('');
    setShowSampDropdown(false);
  };

  const removeSample = (id) => {
    const currentList = formState.distributed_sample_ids || [];
    dispatch(updateFormField({
      field: 'distributed_sample_ids',
      value: currentList.filter(sid => sid !== id)
    }));
  };

  // Attendees multi-entry tags
  const handleAttendeeAdd = (e) => {
    if (e.key === 'Enter' || e.type === 'click') {
      e.preventDefault();
      if (attendeeInput.trim()) {
        const currentList = formState.attendees || [];
        if (!currentList.includes(attendeeInput.trim())) {
          dispatch(updateFormField({
            field: 'attendees',
            value: [...currentList, attendeeInput.trim()]
          }));
        }
        setAttendeeInput('');
      }
    }
  };

  const removeAttendee = (name) => {
    const currentList = formState.attendees || [];
    dispatch(updateFormField({
      field: 'attendees',
      value: currentList.filter(n => n !== name)
    }));
  };

  // Clickable suggested follow-ups
  const handleSuggestedClick = (text) => {
    const current = formState.follow_ups || '';
    const updated = current ? `${current}\n- ${text}` : `- ${text}`;
    dispatch(updateFormField({ field: 'follow_ups', value: updated }));
    // Remove from suggestions list once clicked
    dispatch(setSuggestedFollowUps(suggestedFollowUps.filter(item => item !== text)));
  };

  // Voice recording mock
  const startVoiceRecording = () => {
    setIsRecording(true);
    setTimeout(() => {
      setIsRecording(false);
      // Insert mock transcription into Topics discussed
      const mockTranscription = "Met Dr. John Smith to discuss Cardioxa Phase III clinical outcomes. He was highly positive about the efficacy data and willing to trial it on newly diagnosed heart failure patients. Sent him the clinical study flyer and distributed 2 starter kits.";
      dispatch(updateFormField({ field: 'topics', value: mockTranscription }));
      
      // Notify user via assistant chat
      dispatch(addChatMessage({
        role: 'assistant',
        content: "Transcribed from Voice Note: 'Met Dr. John Smith to discuss Cardioxa...' I can process this transcription for you! Just type 'Process this transcription' in the chat, or edit the form manually.",
        toolCalls: ['Mock Voice Note Transcriber']
      }));
    }, 3000);
  };

  // Log submit handler
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formState.hcp_id) {
      alert("Please select a Healthcare Professional first.");
      return;
    }
    
    try {
      dispatch(setLoading(true));
      const payload = {
        hcp_id: parseInt(formState.hcp_id),
        type: formState.type,
        datetime: new Date(formState.datetime).toISOString(),
        attendees: formState.attendees,
        topics: formState.topics,
        sentiment: formState.sentiment,
        outcomes: formState.outcomes,
        follow_ups: formState.follow_ups,
        shared_material_ids: formState.shared_material_ids,
        distributed_sample_ids: formState.distributed_sample_ids
      };

      let result;
      if (formState.id) {
        result = await apiService.updateInteraction(formState.id, payload);
        alert(`Successfully updated Interaction (ID: ${result.id})!`);
      } else {
        result = await apiService.logInteraction(payload);
        alert(`Successfully logged new Interaction (ID: ${result.id})!`);
      }

      // Clear form
      dispatch(setFormState({ id: null })); // reset ID to switch back to log mode
      dispatch(updateFormField({ field: 'topics', value: '' }));
      dispatch(updateFormField({ field: 'outcomes', value: '' }));
      dispatch(updateFormField({ field: 'follow_ups', value: '' }));
      dispatch(updateFormField({ field: 'attendees', value: [] }));
      dispatch(updateFormField({ field: 'shared_material_ids', value: [] }));
      dispatch(updateFormField({ field: 'distributed_sample_ids', value: [] }));
      dispatch(setSuggestedFollowUps([]));
      
      if (onInteractionLogged) {
        onInteractionLogged();
      }
    } catch (err) {
      console.error(err);
      alert(err.message || "Failed to log interaction.");
    } finally {
      dispatch(setLoading(false));
    }
  };

  return (
    <form className="crm-form" onSubmit={handleSubmit}>
      <h2 className="panel-title flex items-center gap-2">
        <Sparkles size={20} className="text-indigo-400" />
        {formState.id ? `Edit Interaction (ID: ${formState.id})` : "Log HCP Interaction"}
      </h2>
      
      {/* HCP Search */}
      <div className="form-group" ref={hcpRef}>
        <label className="flex items-center gap-2">
          <User size={16} /> HCP Name <span className="required">*</span>
        </label>
        <div className="search-input-wrapper">
          <Search className="search-icon" size={16} />
          <input
            type="text"
            className="form-control pl-8"
            placeholder="Search doctors (e.g. Smith, Jenkins)..."
            value={hcpSearch}
            onChange={handleHcpSearchChange}
            onFocus={() => setShowHcpDropdown(true)}
            required
          />
        </div>
        {showHcpDropdown && hcpResults.length > 0 && (
          <ul className="autocomplete-dropdown">
            {hcpResults.map(h => (
              <li key={h.id} onClick={() => selectHCP(h)}>
                <strong>{h.name}</strong> - <span className="text-gray-400">{h.specialty}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Grid: Type & Datetime */}
      <div className="form-grid">
        <div className="form-group">
          <label className="flex items-center gap-2">
            <Award size={16} /> Interaction Type
          </label>
          <select
            className="form-control"
            value={formState.type}
            onChange={(e) => dispatch(updateFormField({ field: 'type', value: e.target.value }))}
          >
            <option value="Meeting">Meeting (Face-to-Face)</option>
            <option value="Call">Phone Call</option>
            <option value="Email">Email Correspondence</option>
            <option value="Conference">Medical Conference</option>
            <option value="Other">Other</option>
          </select>
        </div>

        <div className="form-group">
          <label className="flex items-center gap-2">
            <Calendar size={16} /> Date and Time
          </label>
          <input
            type="datetime-local"
            className="form-control"
            value={formState.datetime}
            onChange={(e) => dispatch(updateFormField({ field: 'datetime', value: e.target.value }))}
            required
          />
        </div>
      </div>

      {/* Attendees Multi-Entry */}
      <div className="form-group">
        <label className="flex items-center gap-2">
          <Users size={16} /> Attendees
        </label>
        <div className="tag-input-container">
          {formState.attendees?.map(name => (
            <span key={name} className="tag-chip">
              {name}
              <button type="button" onClick={() => removeAttendee(name)}>
                <X size={12} />
              </button>
            </span>
          ))}
          <input
            type="text"
            className="tag-input"
            placeholder="Add attendee & press Enter..."
            value={attendeeInput}
            onChange={(e) => setAttendeeInput(e.target.value)}
            onKeyDown={handleAttendeeAdd}
          />
        </div>
      </div>

      {/* Topics Discussed + Voice Note Mock */}
      <div className="form-group">
        <div className="flex justify-between items-center mb-1">
          <label className="flex items-center gap-2 m-0">
            <FileText size={16} /> Topics Discussed
          </label>
          <button
            type="button"
            className={`voice-note-btn ${isRecording ? 'recording' : ''}`}
            onClick={startVoiceRecording}
            disabled={isRecording}
          >
            <Mic size={14} />
            {isRecording ? "Listening..." : "Summarize from Voice Note"}
          </button>
        </div>
        <textarea
          rows={3}
          className="form-control"
          placeholder="Details of discussion topics..."
          value={formState.topics || ''}
          onChange={(e) => dispatch(updateFormField({ field: 'topics', value: e.target.value }))}
        />
      </div>

      {/* Grid: Shared Materials & Distributed Samples */}
      <div className="form-grid">
        <div className="form-group" ref={matRef}>
          <label className="flex items-center gap-2">
            <Package size={16} /> Materials Shared
          </label>
          <div className="search-input-wrapper">
            <Search className="search-icon" size={14} />
            <input
              type="text"
              className="form-control pl-8"
              placeholder="Search brochures..."
              value={matSearch}
              onChange={handleMatSearchChange}
              onFocus={() => setShowMatDropdown(true)}
            />
          </div>
          {showMatDropdown && matResults.length > 0 && (
            <ul className="autocomplete-dropdown small">
              {matResults.map(m => (
                <li key={m.id} onClick={() => addMaterial(m)}>
                  {m.name}
                </li>
              ))}
            </ul>
          )}
          <div className="selected-relations">
            {formState.shared_material_ids?.map(mid => {
              const name = allMaterials.find(m => m.id === mid)?.name || `Material (ID ${mid})`;
              return (
                <span key={mid} className="relation-chip">
                  {name}
                  <button type="button" onClick={() => removeMaterial(mid)}>
                    <X size={10} />
                  </button>
                </span>
              );
            })}
          </div>
        </div>

        <div className="form-group" ref={sampRef}>
          <label className="flex items-center gap-2">
            <Package size={16} /> Samples Distributed
          </label>
          <div className="search-input-wrapper">
            <Search className="search-icon" size={14} />
            <input
              type="text"
              className="form-control pl-8"
              placeholder="Search sample kits..."
              value={sampSearch}
              onChange={handleSampSearchChange}
              onFocus={() => setShowSampDropdown(true)}
            />
          </div>
          {showSampDropdown && sampResults.length > 0 && (
            <ul className="autocomplete-dropdown small">
              {sampResults.map(s => (
                <li key={s.id} onClick={() => addSample(s)}>
                  {s.name}
                </li>
              ))}
            </ul>
          )}
          <div className="selected-relations">
            {formState.distributed_sample_ids?.map(sid => {
              const name = allMaterials.find(s => s.id === sid)?.name || `Sample (ID ${sid})`;
              return (
                <span key={sid} className="relation-chip">
                  {name}
                  <button type="button" onClick={() => removeSample(sid)}>
                    <X size={10} />
                  </button>
                </span>
              );
            })}
          </div>
        </div>
      </div>

      {/* Observed Sentiment */}
      <div className="form-group">
        <label className="flex items-center gap-2">
          <Smile size={16} /> Observed Sentiment
        </label>
        <div className="sentiment-radio-group">
          {['Positive', 'Neutral', 'Negative'].map(val => (
            <label key={val} className={`sentiment-label ${formState.sentiment === val ? 'active' : ''}`}>
              <input
                type="radio"
                name="sentiment"
                value={val}
                checked={formState.sentiment === val}
                onChange={() => dispatch(updateFormField({ field: 'sentiment', value: val }))}
              />
              {val}
            </label>
          ))}
        </div>
      </div>

      {/* Outcomes */}
      <div className="form-group">
        <label className="flex items-center gap-2">
          <CheckCircle size={16} /> Key Outcomes
        </label>
        <textarea
          rows={2}
          className="form-control"
          placeholder="Agreements, prescriptions expected, feedback..."
          value={formState.outcomes || ''}
          onChange={(e) => dispatch(updateFormField({ field: 'outcomes', value: e.target.value }))}
        />
      </div>

      {/* Follow-up Actions */}
      <div className="form-group">
        <label className="flex items-center gap-2">
          <ArrowRight size={16} /> Follow-up Actions
        </label>
        <textarea
          rows={2}
          className="form-control"
          placeholder="Next steps, materials to send..."
          value={formState.follow_ups || ''}
          onChange={(e) => dispatch(updateFormField({ field: 'follow_ups', value: e.target.value }))}
        />

        {/* AI Suggested Follow-ups rendered directly below */}
        {suggestedFollowUps && suggestedFollowUps.length > 0 && (
          <div className="ai-suggestions-box">
            <div className="ai-suggestions-title flex items-center gap-1">
              <Sparkles size={12} className="text-indigo-400" />
              AI Suggested Follow-ups (click to add):
            </div>
            <ul className="ai-suggestions-list">
              {suggestedFollowUps.map((item, idx) => (
                <li key={idx} onClick={() => handleSuggestedClick(item)}>
                  + {item}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Submit Button */}
      <button 
        type="submit" 
        className="submit-btn flex items-center justify-center gap-2"
        disabled={isLoading}
      >
        {isLoading ? (
          <>
            <span className="spinner"></span>
            Syncing...
          </>
        ) : (
          <>
            {formState.id ? "Update Interaction" : "Log Interaction"}
          </>
        )}
      </button>
    </form>
  );
}
