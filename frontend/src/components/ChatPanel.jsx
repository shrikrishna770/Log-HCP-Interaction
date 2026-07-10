import React, { useState, useRef, useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { 
  addChatMessage, 
  setFormState, 
  setSuggestedFollowUps, 
  setLoading 
} from '../store/crmSlice';
import { apiService } from '../services/api';
import { Send, Bot, User, Cpu, Sparkles, History, HelpCircle } from 'lucide-react';

export default function ChatPanel() {
  const dispatch = useDispatch();
  const chatHistory = useSelector((state) => state.crm.chatHistory);
  const formState = useSelector((state) => state.crm.formState);
  const isLoading = useSelector((state) => state.crm.isLoading);
  
  const [input, setInput] = useState('');
  const chatEndRef = useRef(null);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, isLoading]);

  const handleSend = async (textToSend) => {
    const text = textToSend || input;
    if (!text.trim()) return;

    if (!textToSend) {
      setInput('');
    }

    // Add user message to Redux store
    dispatch(addChatMessage({ role: 'user', content: text }));
    dispatch(setLoading(true));

    try {
      // Build history for backend (limit to last 10 messages to save context space)
      const apiHistory = chatHistory.slice(-10).map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      // Call API
      const res = await apiService.sendChatMessage(text, apiHistory, formState);

      // Add assistant response to history
      dispatch(addChatMessage({
        role: 'assistant',
        content: res.reply,
        toolCalls: res.tool_calls || []
      }));

      // Sync form if the agent parsed any new structured values
      if (res.parsed_form_data && Object.keys(res.parsed_form_data).length > 0) {
        dispatch(setFormState(res.parsed_form_data));
      }

      // Sync suggested follow-ups
      if (res.suggested_follow_ups && res.suggested_follow_ups.length > 0) {
        dispatch(setSuggestedFollowUps(res.suggested_follow_ups));
      }
    } catch (err) {
      console.error(err);
      dispatch(addChatMessage({
        role: 'assistant',
        content: `Sorry, I encountered an error: ${err.message}. Make sure the backend server is running and the GROQ_API_KEY is configured.`,
        toolCalls: []
      }));
    } finally {
      dispatch(setLoading(false));
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Quick Action Pills
  const quickPrompts = [
    { label: "Log Visit", text: "Log a meeting with Dr. John Smith. We discussed Cardioxa clinical results, positive sentiment, and I gave him the Efficacy Brochure and starter sample." },
    { label: "Check Dr. Smith's History", text: "Retrieve Dr. John Smith's past interaction history and summarize the trends." },
    { label: "Recommend Materials", text: "Recommend materials and samples for Dr. Sarah Jenkins based on oncology topics." },
    { label: "Update Sentiment", text: "Change the sentiment to neutral and add attendee 'Dr. Collins'." }
  ];

  return (
    <div className="chat-panel">
      <h2 className="panel-title flex items-center gap-2">
        <Bot size={20} className="text-indigo-400" />
        AI Sales Copilot
      </h2>

      {/* Quick Actions Bar */}
      <div className="quick-actions">
        <div className="quick-actions-title flex items-center gap-1">
          <Sparkles size={12} className="text-indigo-300" /> Quick Commands:
        </div>
        <div className="quick-actions-pills">
          {quickPrompts.map((p, idx) => (
            <button 
              key={idx} 
              type="button" 
              className="quick-action-pill"
              onClick={() => handleSend(p.text)}
              disabled={isLoading}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Chat Messages Log */}
      <div className="chat-messages-container">
        {chatHistory.map((msg, idx) => (
          <div key={idx} className={`chat-message ${msg.role}`}>
            <div className="message-icon">
              {msg.role === 'user' ? <User size={14} /> : <Bot size={14} />}
            </div>
            <div className="message-bubble">
              <div className="message-content">{msg.content}</div>
              
              {/* Render Tool Calls pill if available */}
              {msg.toolCalls && msg.toolCalls.length > 0 && (
                <div className="tool-calls-tag flex items-center gap-1">
                  <Cpu size={10} />
                  <span>Agent Tools Run: {msg.toolCalls.join(', ')}</span>
                </div>
              )}
            </div>
          </div>
        ))}
        
        {/* Thinking State */}
        {isLoading && (
          <div className="chat-message assistant thinking">
            <div className="message-icon">
              <Bot size={14} />
            </div>
            <div className="message-bubble">
              <div className="agent-thinking flex items-center gap-2">
                <span className="thinking-spinner"></span>
                <span>Copilot is thinking (LangGraph agent executing)...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Chat Input form */}
      <div className="chat-input-container">
        <textarea
          className="chat-input"
          placeholder="Ask copilot to log, update, recommend materials, or fetch doctor trends..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyPress}
          disabled={isLoading}
          rows={2}
        />
        <button
          type="button"
          className="chat-send-btn"
          onClick={() => handleSend()}
          disabled={isLoading || !input.trim()}
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}
