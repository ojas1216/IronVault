import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { commandsApi } from '../api/client';

const actionColors: Record<string, string> = {
  admin_login: 'bg-blue-100 text-blue-700',
  command_issued: 'bg-purple-100 text-purple-700',
  command_completed: 'bg-green-100 text-green-700',
  command_failed: 'bg-red-100 text-red-700',
  otp_generated: 'bg-yellow-100 text-yellow-700',
  otp_verified: 'bg-green-100 text-green-700',
  otp_failed: 'bg-red-100 text-red-700',
  root_detected: 'bg-red-100 text-red-800',
  device_enrolled: 'bg-teal-100 text-teal-700',
  uninstall_blocked: 'bg-orange-100 text-orange-700',
};

export const AuditLogsPage: React.FC = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['audit-logs'],
    queryFn: () => commandsApi.auditLogs(undefined, 200),
    refetchInterval: 15_000,
  });

  const logs = data?.data || [];

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Audit Logs</h2>

      {isLoading ? (
        <div className="flex justify-center mt-12">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-800" />
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 text-xs uppercase">
              <tr>
                <th className="px-4 py-3 text-left">Time</th>
                <th className="px-4 py-3 text-left">Action</th>
                <th className="px-4 py-3 text-left">Device ID</th>
                <th className="px-4 py-3 text-left">Admin</th>
                <th className="px-4 py-3 text-left">IP</th>
                <th className="px-4 py-3 text-left">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {logs.map((log: any) => (
                <tr key={log.id} className="hover:bg-gray-50 transition">
                  <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                    {new Date(log.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                      actionColors[log.action] || 'bg-gray-100 text-gray-700'
                    }`}>
                      {log.action.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 font-mono text-xs">
                    {log.device_id?.slice(0, 8) || '—'}
                  </td>
                  <td className="px-4 py-3 text-gray-500 font-mono text-xs">
                    {log.admin_user_id?.slice(0, 8) || '—'}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{log.ip_address || '—'}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs max-w-xs truncate">
                    {log.description || JSON.stringify(log.metadata || {})}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!logs.length && (
            <div className="text-center py-12 text-gray-500">No audit logs yet.</div>
          )}
        </div>
      )}
    </div>
  );
};
