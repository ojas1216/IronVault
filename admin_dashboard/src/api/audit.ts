import { api } from './client';

export interface AuditLog {
  id: string;
  admin_id: string;
  admin_email: string;
  device_id: string | null;
  device_name: string | null;
  action: string;
  details: Record<string, unknown>;
  ip_address: string;
  created_at: string;
}

export interface AuditFilters {
  device_id?: string;
  admin_id?: string;
  action?: string;
  from_date?: string;
  to_date?: string;
  limit?: number;
  offset?: number;
}

export const auditApi = {
  list: (filters?: AuditFilters) =>
    api.get<{ logs: AuditLog[]; total: number }>('/commands/audit-logs', { params: filters }),

  exportCsv: (filters?: AuditFilters) =>
    api.get('/commands/audit-logs/export', {
      params: { ...filters, format: 'csv' },
      responseType: 'blob',
    }),
};

// Helper: trigger CSV download in browser
export function downloadCsv(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
