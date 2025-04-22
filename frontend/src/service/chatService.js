import axios from 'axios';

const API_BASE_URL = 'https://10.0.32.122:8005/chat';

const getAuthHeaders = () => {
  try {
    const token = JSON.parse(localStorage.getItem('accessToken')).value;
    return { Authorization: `Bearer ${token}` };
  } catch (error) {
    console.error('Authentication error. Please login again.');
    return {};
  }
};

const chatService = {
  async sendMessage(message) {
    try {
      const response = await axios.post(`${API_BASE_URL}/`, message, {
        headers: getAuthHeaders(),
      });
      return response.data;
    } catch (error) {
      console.error('Error sending message:', error);
      throw error;
    }
  },

  async getChatHistory(sessionId) {
    try {
      const response = await axios.get(`${API_BASE_URL}/history/${sessionId}`, {
        headers: getAuthHeaders(),
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching chat history:', error);
      throw error;
    }
  },

  async listChatSessions(skip = 0, limit = 100, activeOnly = true) {
    try {
      const response = await axios.get(`${API_BASE_URL}/sessions`, {
        headers: getAuthHeaders(),
        params: { skip, limit, active_only: activeOnly },
      });
      return response.data;
    } catch (error) {
      console.error('Error listing chat sessions:', error);
      throw error;
    }
  },

  async createChatSession(sessionData) {
    try {
      const response = await axios.post(`${API_BASE_URL}/sessions`, sessionData, {
        headers: getAuthHeaders(),
      });
      return response.data;
    } catch (error) {
      console.error('Error creating chat session:', error);
      throw error;
    }
  },

  async updateChatSession(sessionId, sessionData) {
    try {
      const response = await axios.patch(`${API_BASE_URL}/sessions/${sessionId}`, sessionData, {
        headers: getAuthHeaders(),
      });
      return response.data;
    } catch (error) {
      console.error('Error updating chat session:', error);
      throw error;
    }
  },

  async deleteChatSession(sessionId, permanent = false) {
    try {
      const response = await axios.delete(`${API_BASE_URL}/sessions/${sessionId}`, {
        headers: getAuthHeaders(),
        params: { permanent },
      });
      return response.data;
    } catch (error) {
      console.error('Error deleting chat session:', error);
      throw error;
    }
  },

  async generateSessionTitle(sessionId) {
    try {
      const response = await axios.post(`${API_BASE_URL}/sessions/${sessionId}/title`, {}, {
        headers: getAuthHeaders(),
      });
      return response.data;
    } catch (error) {
      console.error('Error generating session title:', error);
      throw error;
    }
  },

  async getAnalysis() {
    try {
      const response = await axios.get(`${API_BASE_URL}/analysis`, {
        headers: getAuthHeaders(),
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching analysis:', error);
      throw error;
    }
  },

  async getSessionInfo(sessionId) {
    try {
      const response = await axios.get(`${API_BASE_URL}/sessions/${sessionId}`, {
        headers: getAuthHeaders(),
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching session info:', error);
      throw error;
    }
  },
};

export const useChatService = () => chatService;