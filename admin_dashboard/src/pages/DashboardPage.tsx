import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { devicesApi } from '../api/client';
import { DeviceCard } from '../components/DeviceCard';
import { StatsBar } from '../components/StatsBar';

export const DashboardPage: React.FC = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['devices'],
    queryFn: () => devicesApi.list(),
    refetchInterval: 30_000, // auto-refresh every 30s
  });

  const devices = data?.data || [];
  const online = devices.filter((d: any) => d.is_online).length;
  const rooted = devices.filter((d: any) => d.is_rooted).length;
  const inactive = devices.filter((d: any) => d.status === 'inactive').length;

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Device Overview</h2>

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
