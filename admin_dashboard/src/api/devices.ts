import { api } from './client';

export interface Device {
  id: string;
  device_name: string;
  employee_name: string;
  employee_email: string;
  department: string;
  platform: 'android' | 'ios' | 'windows' | 'macos';
  os_version: string;
  agent_version: string;
  status: 'active' | 'inactive' | 'lost' | 'wiped' | 'decommissioned';
  is_online: boolean;
  is_rooted: boolean;
  is_uninstall_blocked: boolean;
  last_latitude: number | null;
  last_longitude: number | null;
  last_seen: string | null;
  enrolled_at: string;
  push_token: string | null;
}

export interface LocationPoint {
  latitude: number;
  longitude: number;
  accuracy: number;
  recorded_at: string;
}

export interface AppUsageEntry {
  app_name: string;
  package_name: string;
  duration_minutes: number;
  recorded_at: string;
}

export interface CommandPayload {
  device_id: string;
  command_type: string;
  payload?: Record<string, unknown>;
  otp_id?: string;
}

export interface OtpResponse {
  otp_id: string;
  otp: string;
  expires_in_seconds: number;
}

export const devicesApi = {
  list: (params?: { status?: string; platform?: string; search?: string }) =>
    api.get<Device[]>('/devices/', { params }),

  get: (id: string) =>
    api.get<Device>(`/devices/${id}`),

  locationHistory: (id: string, limit = 100) =>
    api.get<LocationPoint[]>(`/devices/${id}/location-history`, { params: { limit } }),

  appUsage: (id: string) =>
    api.get<AppUsageEntry[]>(`/devices/${id}/app-usage`),

  issueCommand: (body: CommandPayload) =>
    api.post('/commands/issue', body),

  generateOtp: (deviceId: string, commandType: string) =>
    api.post<OtpResponse>('/commands/generate-otp', null, {
      params: { device_id: deviceId, command_type: commandType },
    }),

  silentUninstall: (deviceId: string) =>
    api.post('/commands/admin-silent-uninstall', null, {
      params: { device_id: deviceId },
    }),

  exportCsv: () =>
    api.get('/devices/export', { responseType: 'blob' }),
};
