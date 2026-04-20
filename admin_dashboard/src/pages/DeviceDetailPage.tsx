import React, { useState, Component, ReactNode, useCallback } from 'react';

class ErrorBoundary extends Component<{ children: ReactNode; label: string }, { error: boolean }> {
  state = { error: false };
  static getDerivedStateFromError() { return { error: true }; }
  render() {
    if (this.state.error)
      return <div className="p-4 bg-red-50 text-red-600 rounded-lg text-sm">Failed to load {this.props.label}</div>;
    return this.props.children;
  }
}
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { devicesApi, commandsApi } from '../api/client';
import { LocationMap } from '../components/LocationMap';
import { AppUsageChart } from '../components/AppUsageChart';
import { OTPModal } from '../components/OTPModal';
import { DeviceIdentityPanel } from '../components/DeviceIdentityPanel';
import { UWBTracker } from '../components/UWBTracker';

export const DeviceDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [otpModal, setOtpModal] = useState<{
    open: boolean;
    commandType: string;
    otpData?: { otp_id: string; otp: string; expires_in_seconds: number };
  }>({ open: false, commandType: '' });

  const { data: deviceRes } = useQuery({
    queryKey: ['device', id],
    queryFn: () => devicesApi.get(id!),
    refetchInterval: 15_000,
  });
  const { data: locationRes } = useQuery({
    queryKey: ['location', id],
    queryFn: () => devicesApi.locationHistory(id!),
  });
  const { data: usageRes } = useQuery({
    queryKey: ['usage', id],
    queryFn: () => devicesApi.appUsage(id!),
  });

  const device = deviceRes?.data;
  const locations = locationRes?.data || [];
  const usage = usageRes?.data || [];

  const handleCommand = async (commandType: string) => {
    const destructive = ['remote_uninstall', 'wipe_device'].includes(commandType);
    if (destructive) {
      // Generate OTP first
      try {
        const res = await commandsApi.generateOtp(id!, commandType);
        setOtpModal({ open: true, commandType, otpData: res.data });
      } catch {
        toast.error('Failed to generate OTP');
      }
    } else {
      // Non-destructive — issue directly
      try {
        await commandsApi.issueCommand({ device_id: id!, command_type: commandType });
        toast.success(`Command "${commandType}" sent`);
      } catch {
        toast.error('Command failed');
      }
    }
  };

  const handleDelete = async () => {
    try {
      await devicesApi.delete(id!);
      toast.success('Device removed from system');
      navigate('/dashboard');
    } catch {
      toast.error('Failed to remove device');
    }
  };

  const handleOtpConfirm = async (otpId: string) => {
    try {
      await commandsApi.issueCommand({
        device_id: id!,
        command_type: otpModal.commandType,
        otp_id: otpId,
      });
      toast.success('Command authorized and sent to device');
      setOtpModal({ open: false, commandType: '' });
    } catch {
      toast.error('Command failed');
    }
  };

  if (!device) return <div className="p-6">Loading...</div>;

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">{device.device_name}</h2>
          <p className="text-gray-500">{device.employee_name} · {device.employee_email}</p>
          <div className="flex gap-2 mt-2">
            <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
              device.is_online ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
            }`}>
              {device.is_online ? 'Online' : 'Offline'}
            </span>
            <span className="px-2 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-700 capitalize">
              {device.platform}
            </span>
            {device.is_rooted && (
              <span className="px-2 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-700">
                Security Alert: Rooted
              </span>
            )}
          </div>
        </div>
        <div className="flex gap-2 flex-wrap justify-end">
          <CommandButton label="Lock Device" onClick={() => handleCommand('lock_device')} color="yellow" />
          <CommandButton label="Trigger Alarm" onClick={() => handleCommand('trigger_alarm')} color="orange" />
          <CommandButton label="Request Location" onClick={() => handleCommand('location_request')} color="blue" />
          <CommandButton label="Front Camera" onClick={() => handleCommand('capture_front_camera')} color="purple" />
          <CommandButton label="Extract SIM Info" onClick={() => handleCommand('extract_sim_metadata')} color="teal" />
          <CommandButton label="Get Device ID" onClick={() => handleCommand('extract_device_identity')} color="indigo" />
          <CommandButton label="Lost Mode" onClick={() => handleCommand('enable_lost_mode')} color="orange" />
          <CommandButton label="Remote Uninstall" onClick={() => handleCommand('remote_uninstall')} color="red" />
          <CommandButton label="Wipe Device" onClick={() => handleCommand('wipe_device')} color="red" />
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="px-3 py-2 rounded-lg text-sm font-medium bg-gray-800 text-white hover:bg-black transition"
          >
            Remove Device
          </button>
        </div>
      </div>

      {/* Device Info Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <InfoCard label="OS Version" value={device.os_version || 'N/A'} />
        <InfoCard label="Agent Version" value={device.agent_version || 'N/A'} />
        <InfoCard label="Department" value={device.department || 'N/A'} />
        <InfoCard label="Last Seen" value={device.last_seen
          ? new Date(device.last_seen).toLocaleString() : 'Never'} />
      </div>

      {/* Location Map */}
      <div className="bg-white rounded-xl shadow p-4 mb-6">
        <h3 className="font-semibold text-gray-800 mb-3">Location History</h3>
        <ErrorBoundary label="Location Map">
          <LocationMap locations={locations} />
        </ErrorBoundary>
      </div>

      {/* App Usage Chart */}
      <div className="bg-white rounded-xl shadow p-4 mb-6">
        <h3 className="font-semibold text-gray-800 mb-3">App Usage (Last 24h)</h3>
        <ErrorBoundary label="App Usage Chart">
          <AppUsageChart data={usage} />
        </ErrorBoundary>
      </div>

      {/* UWB Precision Tracker */}
      {id && (
        <div className="mb-6">
          <ErrorBoundary label="UWB Tracker">
            <UWBTracker deviceId={id} />
          </ErrorBoundary>
        </div>
      )}

      {/* Device Identity Panel */}
      {id && (
        <ErrorBoundary label="Device Identity">
          <DeviceIdentityPanel deviceId={id} />
        </ErrorBoundary>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 z-[9999] overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6 text-center">
            <div className="text-4xl mb-3">⚠️</div>
            <h3 className="text-lg font-bold text-gray-800 mb-2">Remove Device?</h3>
            <p className="text-sm text-gray-500 mb-6">
              This will permanently delete <strong>{device.device_name}</strong> and all its data
              (location history, app usage, commands) from the system. This cannot be undone.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="flex-1 px-4 py-2 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-semibold hover:bg-red-700"
              >
                Yes, Remove
              </button>
            </div>
          </div>
          </div>
        </div>
      )}

      {/* OTP Modal */}
      {otpModal.open && otpModal.otpData && (
        <OTPModal
          otp={otpModal.otpData.otp}
          otpId={otpModal.otpData.otp_id}
          expiresIn={otpModal.otpData.expires_in_seconds}
          commandType={otpModal.commandType}
          onConfirm={handleOtpConfirm}
          onClose={() => setOtpModal({ open: false, commandType: '' })}
        />
      )}
    </div>
  );
};

const CommandButton: React.FC<{
  label: string; onClick: () => void; color: string;
}> = ({ label, onClick, color }) => (
  <button
    onClick={onClick}
    className={`px-3 py-2 rounded-lg text-sm font-medium transition
      bg-${color}-100 text-${color}-800 hover:bg-${color}-200`}
  >
    {label}
  </button>
);

const InfoCard: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="bg-gray-50 rounded-lg p-3">
    <p className="text-xs text-gray-500 mb-1">{label}</p>
    <p className="text-sm font-semibold text-gray-800 truncate">{value}</p>
  </div>
);
