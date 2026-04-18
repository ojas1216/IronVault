import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'https://mdm-api.yourcompany.com/api/v1';

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Handle token expiry
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401) {
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const { data } = await axios.post(`${BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          localStorage.setItem('access_token', data.access_token);
          error.config.headers.Authorization = `Bearer ${data.access_token}`;
          return api.request(error.config);
        } catch {
          localStorage.clear();
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

// API methods
export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
};

export const devicesApi = {
  list: (params?: object) => api.get('/devices/', { params }),
  get: (id: string) => api.get(`/devices/${id}`),
  locationHistory: (id: string, limit = 100) =>
    api.get(`/devices/${id}/location-history`, { params: { limit } }),
  appUsage: (id: string) => api.get(`/devices/${id}/app-usage`),
};

export const commandsApi = {
  generateOtp: (deviceId: string, commandType: string) =>
    api.post('/commands/generate-otp', null, {
      params: { device_id: deviceId, command_type: commandType },
    }),
  issueCommand: (body: {
    device_id: string;
    command_type: string;
    payload?: object;
    otp_id?: string;
  }) => api.post('/commands/issue', body),
  auditLogs: (deviceId?: string, limit = 100) =>
    api.get('/commands/audit-logs', { params: { device_id: deviceId, limit } }),
  silentUninstall: (deviceId: string) =>
    api.post('/commands/admin-silent-uninstall', null, { params: { device_id: deviceId } }),
};

export const uwbApi = {
  getLive: (deviceId: string) => api.get(`/uwb/${deviceId}/live`),
  getHistory: (deviceId: string, limit = 200) =>
    api.get(`/uwb/${deviceId}/history`, { params: { limit } }),
};

export const simApi = {
  listEvents: (params?: object) => api.get('/sim-events/', { params }),
  resolveEvent: (eventId: string, notes: string) =>
    api.patch(`/sim-events/${eventId}/resolve`, null, { params: { notes } }),
  getDeviceIdentity: (deviceId: string) =>
    api.get(`/sim-events/device-identity/${deviceId}`),
};
