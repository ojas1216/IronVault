import React from 'react';
import { useNavigate } from 'react-router-dom';

interface Device {
  id: string;
  device_name: string;
  employee_name: string;
  employee_email: string;
  platform: string;
  status: string;
  is_online: boolean;
  is_rooted: boolean;
  last_seen: string | null;
  department: string;
}

export const DeviceCard: React.FC<{ device: Device }> = ({ device }) => {
  const navigate = useNavigate();

  const platformIcon: Record<string, string> = {
    android: '🤖', ios: '', windows: '🪟', macos: '',
  };

  return (
    <div
      className="bg-white rounded-xl shadow hover:shadow-md transition cursor-pointer p-5 border border-gray-100"
      onClick={() => navigate(`/devices/${device.id}`)}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{platformIcon[device.platform] || '💻'}</span>
          <div>
            <p className="font-semibold text-gray-800">{device.device_name}</p>
            <p className="text-sm text-gray-500">{device.employee_name}</p>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className={`w-2.5 h-2.5 rounded-full ${device.is_online ? 'bg-green-500' : 'bg-gray-300'}`} />
          {device.is_rooted && (
            <span className="text-xs bg-red-100 text-red-600 px-1.5 py-0.5 rounded font-semibold">
              ROOT ALERT
            </span>
          )}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-2 text-xs text-gray-500">
        <span className="bg-gray-100 px-2 py-0.5 rounded capitalize">{device.platform}</span>
        <span className="bg-gray-100 px-2 py-0.5 rounded">{device.department || 'No dept'}</span>
        <span className="bg-gray-100 px-2 py-0.5 rounded capitalize">{device.status}</span>
      </div>

      <p className="mt-2 text-xs text-gray-400">
        {device.last_seen
          ? `Last seen: ${new Date(device.last_seen).toLocaleString()}`
          : 'Never connected'}
      </p>
    </div>
  );
};
