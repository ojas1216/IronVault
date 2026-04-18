import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';

interface Props {
  deviceId: string;
}

export const DeviceIdentityPanel: React.FC<Props> = ({ deviceId }) => {
  const { data, isLoading } = useQuery({
    queryKey: ['device-identity', deviceId],
    queryFn: () => api.get(`/sim-events/device-identity/${deviceId}`),
    retry: false,
  });

  if (isLoading) return <div className="text-xs text-gray-400 p-4">Loading identity...</div>;
  if (!data) return (
    <div className="text-xs text-gray-400 p-4">
      No identity recorded yet. Agent will sync on next heartbeat.
    </div>
  );

  const identity = data.data;

  return (
    <div className="bg-white rounded-xl shadow p-5">
      <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
        <span>🔍</span> Device Identity (Section 4)
      </h3>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <IdentityField label="IMEI (Slot 1)" value={identity.imei_slot1} secret />
        <IdentityField label="IMEI (Slot 2)" value={identity.imei_slot2} secret />
        <IdentityField label="Serial Number" value={identity.serial_number} secret />
        <IdentityField label="Android ID" value={identity.android_id} />
        <IdentityField label="Manufacturer" value={identity.manufacturer} />
        <IdentityField label="Model" value={identity.model} />
        <IdentityField label="Brand" value={identity.brand} />
        <IdentityField label="Android SDK" value={identity.sdk_int?.toString()} />
        <div className="col-span-2">
          <p className="text-xs text-gray-400 mb-1">Hardware Fingerprint</p>
          <p className="font-mono text-xs bg-gray-50 p-2 rounded break-all text-gray-600">
            {identity.hardware_fingerprint || '—'}
          </p>
        </div>
      </div>
      <p className="text-xs text-gray-400 mt-3">
        Last updated: {identity.updated_at
          ? new Date(identity.updated_at).toLocaleString() : 'Never'}
      </p>
    </div>
  );
};

const IdentityField: React.FC<{
  label: string;
  value?: string | null;
  secret?: boolean;
}> = ({ label, value, secret = false }) => {
  const [revealed, setRevealed] = React.useState(!secret);
  const displayValue = value || '—';

  return (
    <div className="bg-gray-50 rounded-lg p-3">
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <div className="flex items-center gap-2">
        <p className="font-mono text-sm text-gray-800 truncate flex-1">
          {revealed ? displayValue : '••••••••••••'}
        </p>
        {secret && value && (
          <button
            onClick={() => setRevealed((r) => !r)}
            className="text-xs text-blue-500 hover:text-blue-700"
          >
            {revealed ? 'Hide' : 'Show'}
          </button>
        )}
      </div>
    </div>
  );
};
