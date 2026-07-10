import { createSlice } from '@reduxjs/toolkit';

const formatDateTimeLocal = (dateVal) => {
  if (!dateVal) return '';
  try {
    const d = new Date(dateVal);
    if (isNaN(d.getTime())) return '';
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day}T${hours}:${minutes}`;
  } catch (e) {
    return '';
  }
};

const initialFormState = {
  id: null,
  hcp_id: '',
  hcp_name: '',
  type: 'Meeting',
  datetime: formatDateTimeLocal(new Date()), // YYYY-MM-DDTHH:mm local time
  attendees: [],
  topics: '',
  sentiment: 'Neutral',
  outcomes: '',
  follow_ups: '',
  shared_material_ids: [],
  distributed_sample_ids: []
};

const initialState = {
  formState: { ...initialFormState },
  chatHistory: [
    {
      role: 'assistant',
      content: "Hello! I am your AI CRM Assistant. You can describe your interaction in plain text here (e.g., 'Met Dr. John Smith to discuss Cardioxa efficacy, positive sentiment, shared brochure'), and I will extract the details and fill out the form for you. Or, you can ask me for history or recommendations!",
      toolCalls: []
    }
  ],
  suggestedFollowUps: [],
  recommendedMaterials: [],
  recommendedSamples: [],
  hcpHistorySummary: '',
  isLoading: false,
  error: null
};

export const crmSlice = createSlice({
  name: 'crm',
  initialState,
  reducers: {
    updateFormField: (state, action) => {
      const { field, value } = action.payload;
      if (field === 'datetime') {
        state.formState[field] = formatDateTimeLocal(value);
      } else {
        state.formState[field] = value;
      }
    },
    setFormState: (state, action) => {
      const updated = { ...action.payload };
      if (updated.datetime) {
        updated.datetime = formatDateTimeLocal(updated.datetime);
      }
      state.formState = { ...state.formState, ...updated };
    },
    addChatMessage: (state, action) => {
      state.chatHistory.push(action.payload);
    },
    clearForm: (state) => {
      state.formState = {
        ...initialFormState,
        datetime: formatDateTimeLocal(new Date())
      };
      state.suggestedFollowUps = [];
      state.recommendedMaterials = [];
      state.recommendedSamples = [];
      state.hcpHistorySummary = '';
    },
    setSuggestedFollowUps: (state, action) => {
      state.suggestedFollowUps = action.payload;
    },
    setRecommendations: (state, action) => {
      const { materials, samples } = action.payload;
      state.recommendedMaterials = materials || [];
      state.recommendedSamples = samples || [];
    },
    setHcpHistorySummary: (state, action) => {
      state.hcpHistorySummary = action.payload;
    },
    setLoading: (state, action) => {
      state.isLoading = action.payload;
    },
    setError: (state, action) => {
      state.error = action.payload;
    }
  }
});

export const {
  updateFormField,
  setFormState,
  addChatMessage,
  clearForm,
  setSuggestedFollowUps,
  setRecommendations,
  setHcpHistorySummary,
  setLoading,
  setError
} = crmSlice.actions;

export default crmSlice.reducer;
