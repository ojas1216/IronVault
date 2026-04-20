import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { devicesApi } from '../api/client';
import { DeviceCard } from '../components/DeviceCard';
import { StatsBar } from '../components/StatsBar';
import { AddDeviceModal } from '../components/AddDeviceModal';

export const DashboardPage: React.FC = () => {
  const [showAddDevice, setShowAddDevice] = useState(false);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['devices'],
    queryFn: () => devicesApi.list(),
    refetchInterval: 30_000,
  });

  const devices = data?.data || [];
  const online = devices.filter((d: any) => d.is_online).length;
  const rooted = devices.filter((d: any) => d.is_rooted).length;
  const inactive = devices.filter((d: any) => d.status === 'inactive').length;

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Device Overview</h2>
        <button
          onClick={() => setShowAddDevice(true)}
          className="px-4 py-2 bg-blue-700 text-white rounded-lg text-sm font-medium hover:bg-blue-800 flex items-center gap-2"
        >
          <span className="text-lg leading-none">+</span> Add Device
        </button>
      </div>

      {showAddDevice && (
        <AddDeviceModal
          onClose={() => setShowAddDevice(false)}
          onAdded={() => queryClient.invalidateQueries({ queryKey: ['devices'] })}
        />
      )}

      <StatsBar
        stats={[
          { label: 'Total Devices', value: devices.length, color: 'blue' },
          { label: 'Online Now', value: online, color: 'green' },
          { label: 'Offline', value: devices.length - online, color: 'gray' },
          { label: 'Security Alerts', value: rooted, color: 'red' },
          { label: 'Inactive', value: inactive, color: 'yellow' },
        ]}
      />

      {isLoading ? (
        <div className="flex justify-center mt-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-800" />
        </div>
      ) : (
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {devices.map((device: any) => (
            <DeviceCard key={device.id} device={device} />
          ))}
        </div>
      )}
    </div>
  );
};
