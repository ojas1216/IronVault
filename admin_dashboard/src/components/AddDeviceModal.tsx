import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import { api } from '../api/client';
import toast from 'react-hot-toast';

interface Props {
  onClose: () => void;
  onAdded: () => void;
}

interface EnrollResult {
  device_id: string;
  enrollment_code: string;
  enrollment_token: string;
  message: string;
}

export const AddDeviceModal: React.FC<Props> = ({ onClose, onAdded }) => {
  const [form, setForm] = useState({
    device_name: '',
    employee_name: '',
    employee_email: '',
    department: '',
    platform: 'android',
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<EnrollResult | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.device_name || !form.employee_name || !form.employee_email) {
      toast.error('Device name, employee name and email are required');
      return;
    }
    setLoading(true);
    try {
      const res = await api.post('/devices/admin-register', form);
      setResult(res.data);
      onAdded();
      toast.success('Device slot created');
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to register device');
    } finally {
      setLoading(false);
    }
  };

  const modal = (
    <div className="fixed inset-0 bg-black/50 z-[9999] overflow-y-auto">
      <div className="flex min-h-full items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6">
        {!result ? (
          <>
            <div className="flex justify-between items-center mb-5">
              <h2 className="text-lg font-bold text-gray-800">Add New Device</h2>
              <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl font-bold">×</button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <Field label="Device Name *" placeholder="Rahul's Work Phone">
                <input
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={form.device_name}
                  onChange={e => setForm(f => ({ ...f, device_name: e.target.value }))}
                  placeholder="e.g. Rahul's Android Phone"
                />
              </Field>

              <Field label="Employee Name *" placeholder="">
                <input
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={form.employee_name}
                  onChange={e => setForm(f => ({ ...f, employee_name: e.target.value }))}
                  placeholder="e.g. Rahul Shukla"
                />
              </Field>

              <Field label="Employee Email *" placeholder="">
                <input
                  type="email"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={form.employee_email}
                  onChange={e => setForm(f => ({ ...f, employee_email: e.target.value }))}
                  placeholder="e.g. rahul@company.com"
                />
              </Field>

              <div className="grid grid-cols-2 gap-4">
                <Field label="Department">
                  <input
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={form.department}
                    onChange={e => setForm(f => ({ ...f, department: e.target.value }))}
                    placeholder="e.g. Engineering"
                  />
                </Field>
                <Field label="Platform">
                  <select
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={form.platform}
                    onChange={e => setForm(f => ({ ...f, platform: e.target.value }))}
                  >
                    <option value="android">Android</option>
                    <option value="ios">iOS</option>
                    <option value="windows">Windows</option>
                    <option value="macos">macOS</option>
                  </select>
                </Field>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="flex-1 px-4 py-2 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 px-4 py-2 bg-blue-700 text-white rounded-lg text-sm font-medium hover:bg-blue-800 disabled:opacity-50"
                >
                  {loading ? 'Creating...' : 'Create Device Slot'}
                </button>
              </div>
            </form>
          </>
        ) : (
          <>
            <div className="flex justify-between items-center mb-5">
              <h2 className="text-lg font-bold text-gray-800">Device Slot Created</h2>
              <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl font-bold">×</button>
            </div>

            <div className="space-y-4">
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <p className="text-sm font-semibold text-green-800 mb-1">Device ID</p>
                <p className="font-mono text-xs text-green-700 break-all">{result.device_id}</p>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="text-sm font-semibold text-blue-800 mb-2">Enrollment Code</p>
                <p className="font-mono text-lg font-bold text-blue-900 tracking-widest">
                  {result.enrollment_code}
                </p>
                <p className="text-xs text-blue-600 mt-2">
                  Share this code with the employee. They enter it when installing the MDM agent.
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4 text-xs text-gray-600 space-y-1">
                <p className="font-semibold text-gray-700 mb-2">Agent Installation Steps:</p>
                <p>1. Install the IronVault MDM Agent on the device</p>
                <p>2. Open the app and enter the enrollment code above</p>
                <p>3. The device will appear in this dashboard automatically</p>
              </div>

              <button
                onClick={onClose}
                className="w-full px-4 py-2 bg-blue-700 text-white rounded-lg text-sm font-medium hover:bg-blue-800"
              >
                Done
              </button>
            </div>
          </>
        )}
      </div>
      </div>
    </div>
  );

  return createPortal(modal, document.body);
};

const Field: React.FC<{ label: string; placeholder?: string; children: React.ReactNode }> = ({ label, children }) => (
  <div>
    <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
    {children}
  </div>
);
