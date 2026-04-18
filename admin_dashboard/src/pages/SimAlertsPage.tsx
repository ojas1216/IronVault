import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { api } from '../api/client';

interface SimEvent {
  id: string;
  device_id: string;
  event_type: 'inserted' | 'removed' | 'swapped' | 'changed';
  slot_index: number;
  iccid: string | null;
  carrier_name: string | null;
  country_iso: string | null;
  phone_number: string | null;
  is_roaming: boolean;
  security_photo_url: string | null;
  is_resolved: boolean;
  recorded_at: string;
}

const eventColors: Record<string, string> = {
  swapped: 'bg-red-100 text-red-800 border-red-200',
  removed: 'bg-orange-100 text-orange-800 border-orange-200',
  inserted: 'bg-blue-100 text-blue-800 border-blue-200',
  changed: 'bg-yellow-100 text-yellow-800 border-yellow-200',
};

const BASE_URL = import.meta.env.VITE_API_URL?.replace('/api/v1', '') || '';

export const SimAlertsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [showResolved, setShowResolved] = useState(false);
  const [notesModal, setNotesModal] = useState<{ open: boolean; eventId: string }>({
    open: false, eventId: ''
  });
  const [notes, setNotes] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['sim-events', showResolved],
    queryFn: () => api.get('/sim-events/', {
      params: { unresolved_only: !showResolved, limit: 200 }
    }),
    refetchInterval: 15_000,
  });

  const resolveMutation = useMutation({
    mutationFn: ({ id, notes }: { id: string; notes: string }) =>
      api.patch(`/sim-events/${id}/resolve`, null, { params: { notes } }),
    onSuccess: () => {
      toast.success('Incident resolved');
      queryClient.invalidateQueries({ queryKey: ['sim-events'] });
      setNotesModal({ open: false, eventId: '' });
      setNotes('');
    },
  });

  const events: SimEvent[] = data?.data || [];
  const unresolvedCount = events.filter((e) => !e.is_resolved).length;

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">SIM Alerts</h2>
          <p className="text-gray-500 text-sm mt-1">
            Section 5 — SIM Intelligence Layer
          </p>
        </div>
        {unresolvedCount > 0 && (
          <span className="bg-red-100 text-red-800 text-sm font-semibold px-3 py-1 rounded-full">
            {unresolvedCount} unresolved
          </span>
        )}
      </div>

      {/* Filter toggle */}
      <div className="flex gap-3 mb-4">
        <button
          onClick={() => setShowResolved(false)}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
            !showResolved ? 'bg-red-600 text-white' : 'bg-gray-100 text-gray-600'
          }`}
        >
          Active Alerts
        </button>
        <button
          onClick={() => setShowResolved(true)}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
            showResolved ? 'bg-gray-700 text-white' : 'bg-gray-100 text-gray-600'
          }`}
        >
          All Events
        </button>
      </div>

      {isLoading ? (
        <div className="flex justify-center mt-12">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-red-600" />
        </div>
      ) : events.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <div className="text-5xl mb-3">✅</div>
          <p className="font-medium">No SIM alerts</p>
        </div>
      ) : (
        <div className="space-y-4">
          {events.map((event) => (
            <div
              key={event.id}
              className={`rounded-xl border p-5 ${
                event.is_resolved ? 'opacity-60 bg-gray-50' : 'bg-white shadow'
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                  <span className={`px-3 py-1 rounded-full text-xs font-bold border capitalize ${
                    eventColors[event.event_type] || 'bg-gray-100 text-gray-700'
                  }`}>
                    SIM {event.event_type.toUpperCase()}
                  </span>
                  <span className="text-xs text-gray-500">
                    Slot {event.slot_index + 1}
                  </span>
                  {event.is_resolved && (
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">
                      Resolved
                    </span>
                  )}
                </div>
                <span className="text-xs text-gray-400">
                  {new Date(event.recorded_at).toLocaleString()}
                </span>
              </div>

              <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                <div>
                  <p className="text-xs text-gray-400">Device ID</p>
                  <p className="font-mono text-gray-700">{event.device_id.slice(0, 8)}...</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">ICCID</p>
                  <p className="font-mono text-gray-700">{event.iccid || '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Carrier</p>
                  <p className="text-gray-700">{event.carrier_name || '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Country / Roaming</p>
                  <p className="text-gray-700">
                    {event.country_iso?.toUpperCase() || '—'}
                    {event.is_roaming && (
                      <span className="ml-1 text-orange-600 font-semibold">[ROAMING]</span>
                    )}
                  </p>
                </div>
              </div>

              {/* Security photo */}
              {event.security_photo_url && (
                <div className="mt-3">
                  <p className="text-xs text-gray-400 mb-1">Security Photo</p>
                  <img
                    src={`${BASE_URL}${event.security_photo_url}`}
                    alt="Security capture"
                    className="h-24 w-24 object-cover rounded-lg border"
                  />
                </div>
              )}

              {!event.is_resolved && (
                <div className="mt-3 flex gap-2">
                  <button
                    onClick={() => setNotesModal({ open: true, eventId: event.id })}
                    className="px-3 py-1.5 bg-green-100 text-green-700 rounded-lg text-xs font-semibold hover:bg-green-200 transition"
                  >
                    Mark Resolved
                  </button>
                  <a
                    href={`/devices/${event.device_id}`}
                    className="px-3 py-1.5 bg-blue-100 text-blue-700 rounded-lg text-xs font-semibold hover:bg-blue-200 transition"
                  >
                    View Device
                  </a>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Resolve modal */}
      {notesModal.open && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-sm w-full mx-4 shadow-2xl">
            <h3 className="font-bold text-gray-800 mb-3">Resolve SIM Alert</h3>
            <textarea
              className="w-full border rounded-lg p-3 text-sm resize-none"
              rows={3}
              placeholder="Add resolution notes (e.g. Employee confirmed, authorized SIM change)..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
            <div className="flex gap-3 mt-4">
              <button
                onClick={() => setNotesModal({ open: false, eventId: '' })}
                className="flex-1 border border-gray-300 py-2 rounded-lg text-sm"
              >
                Cancel
              </button>
              <button
                onClick={() => resolveMutation.mutate({ id: notesModal.eventId, notes })}
                className="flex-1 bg-green-600 text-white py-2 rounded-lg text-sm font-semibold"
              >
                Resolve
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
