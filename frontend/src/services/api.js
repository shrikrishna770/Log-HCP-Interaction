const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiService = {
  async searchHCPs(query) {
    const res = await fetch(`${API_BASE_URL}/api/hcps/search?q=${encodeURIComponent(query)}`);
    if (!res.ok) throw new Error('Failed to search HCPs');
    return res.json();
  },

  async searchMaterials(query) {
    const res = await fetch(`${API_BASE_URL}/api/materials/search?q=${encodeURIComponent(query)}`);
    if (!res.ok) throw new Error('Failed to search materials');
    return res.json();
  },

  async getInteractions() {
    const res = await fetch(`${API_BASE_URL}/api/interactions`);
    if (!res.ok) throw new Error('Failed to fetch interactions');
    return res.json();
  },

  async logInteraction(payload) {
    const res = await fetch(`${API_BASE_URL}/api/interactions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to log interaction');
    }
    return res.json();
  },

  async updateInteraction(id, payload) {
    const res = await fetch(`${API_BASE_URL}/api/interactions/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to update interaction');
    }
    return res.json();
  },

  async sendChatMessage(message, history, currentFormState) {
    const res = await fetch(`${API_BASE_URL}/api/agent/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        history,
        current_form_state: currentFormState
      })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Agent communication failed');
    }
    return res.json();
  }
};
