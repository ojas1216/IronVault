import React, { useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';

interface Props {
  deviceId: string;
}

interface RangingData {
  distance_meters: number | null;
  azimuth_degrees: number | null;
  elevation_degrees: number | null;
  mode: string;
  recorded_at: string | null;
}

export const UWBTracker: React.FC<Props> = ({ deviceId }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const { data } = useQuery({
    queryKey: ['uwb-live', deviceId],
    queryFn: () => api.get(`/uwb/${deviceId}/live`),
    refetchInterval: 1000, // 1Hz update
  });

  const ranging: RangingData = data?.data || {
    distance_meters: null, azimuth_degrees: null,
    elevation_degrees: null, mode: 'no_data', recorded_at: null,
  };

  useEffect(() => {
    drawRadar(canvasRef.current, ranging);
  }, [ranging]);

  const modeColor: Record<string, string> = {
    uwb: 'text-green-600',
    ble_fallback: 'text-yellow-600',
    ios_nearby: 'text-blue-600',
    no_data: 'text-gray-400',
  };

  const modeLabel: Record<string, string> = {
    uwb: 'UWB (±10 cm)',
    ble_fallback: 'BLE Fallback (±2 m)',
    ios_nearby: 'iOS Nearby (±10 cm)',
    no_data: 'No data',
  };

  const directionHint = getDirectionHint(ranging);

  return (
    <div className="bg-white rounded-xl shadow p-5">
      <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
        <span>📡</span> UWB Precision Tracker
        <span className={`text-xs font-normal ml-2 ${modeColor[ranging.mode] || 'text-gray-400'}`}>
          {modeLabel[ranging.mode] || ranging.mode}
        </span>
      </h3>

      <div className="flex gap-6 items-center">
        {/* Radar canvas */}
        <canvas
          ref={canvasRef}
          width={200}
          height={200}
          className="rounded-full border border-gray-200"
        />

        {/* Stats */}
        <div className="flex-1 space-y-3">
          <div className="bg-blue-50 rounded-xl p-4 text-center">
            <p className="text-xs text-blue-500 mb-1">Distance</p>
            <p className="text-3xl font-bold text-blue-800">
              {ranging.distance_meters !== null
                ? ranging.distance_meters < 1
                  ? `${(ranging.distance_meters * 100).toFixed(0)} cm`
                  : `${ranging.distance_meters.toFixed(2)} m`
                : '—'}
            </p>
          </div>

          <div className="bg-gray-50 rounded-xl p-3 text-center">
            <p className="text-xs text-gray-400 mb-1">Direction</p>
            <p className="text-sm font-semibold text-gray-700">{directionHint}</p>
          </div>

          {ranging.azimuth_degrees !== null && (
            <div className="bg-gray-50 rounded-xl p-3 text-center">
              <p className="text-xs text-gray-400 mb-1">Azimuth</p>
              <p className="text-lg font-bold text-gray-700">
                {ranging.azimuth_degrees.toFixed(1)}°
              </p>
            </div>
          )}

          {ranging.recorded_at && (
            <p className="text-xs text-gray-400 text-center">
              Updated: {new Date(ranging.recorded_at).toLocaleTimeString()}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

function drawRadar(canvas: HTMLCanvasElement | null, ranging: RangingData) {
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const cx = 100, cy = 100, r = 90;
  ctx.clearRect(0, 0, 200, 200);

  // Background
  ctx.fillStyle = '#0f172a';
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.fill();

  // Radar rings
  for (let i = 1; i <= 3; i++) {
    ctx.strokeStyle = 'rgba(59,130,246,0.3)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(cx, cy, (r / 3) * i, 0, Math.PI * 2);
    ctx.stroke();
  }

  // Crosshairs
  ctx.strokeStyle = 'rgba(59,130,246,0.2)';
  ctx.beginPath();
  ctx.moveTo(cx, cy - r); ctx.lineTo(cx, cy + r);
  ctx.moveTo(cx - r, cy); ctx.lineTo(cx + r, cy);
  ctx.stroke();

  // Device dot (center = admin/tracker device)
  ctx.fillStyle = '#3b82f6';
  ctx.beginPath();
  ctx.arc(cx, cy, 5, 0, Math.PI * 2);
  ctx.fill();

  if (ranging.distance_meters === null) {
    ctx.fillStyle = 'rgba(156,163,175,0.8)';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('No signal', cx, cy + 20);
    return;
  }

  // Normalize distance to radar radius (max 10m maps to edge)
  const maxMeters = 10;
  const normalized = Math.min(ranging.distance_meters / maxMeters, 1);
  const dotR = normalized * r;

  // Azimuth angle (0° = up, clockwise)
  const azimuth = ranging.azimuth_degrees ?? 0;
  const angleRad = (azimuth - 90) * (Math.PI / 180);

  const dotX = cx + dotR * Math.cos(angleRad);
  const dotY = cy + dotR * Math.sin(angleRad);

  // Sweep line toward dot
  ctx.strokeStyle = 'rgba(34,197,94,0.4)';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(cx, cy);
  ctx.lineTo(dotX, dotY);
  ctx.stroke();

  // Target dot (pulsing green)
  const pulse = Math.sin(Date.now() / 300) * 0.5 + 0.5;
  ctx.fillStyle = `rgba(34,197,94,${0.6 + pulse * 0.4})`;
  ctx.beginPath();
  ctx.arc(dotX, dotY, 7, 0, Math.PI * 2);
  ctx.fill();

  // Distance label near dot
  ctx.fillStyle = '#fff';
  ctx.font = 'bold 10px sans-serif';
  ctx.textAlign = 'center';
  const label = ranging.distance_meters < 1
    ? `${(ranging.distance_meters * 100).toFixed(0)}cm`
    : `${ranging.distance_meters.toFixed(1)}m`;
  ctx.fillText(label, dotX, dotY - 11);
}

function getDirectionHint(ranging: RangingData): string {
  if (ranging.distance_meters === null) return 'Waiting for signal...';
  if (ranging.distance_meters < 0.3) return '📍 Right here!';
  if (ranging.azimuth_degrees === null) return `${ranging.distance_meters.toFixed(1)} m away`;

  const a = ranging.azimuth_degrees;
  const dist = ranging.distance_meters < 1
    ? `${(ranging.distance_meters * 100).toFixed(0)} cm`
    : `${ranging.distance_meters.toFixed(1)} m`;

  if (a >= -22.5 && a < 22.5) return `↑ Straight ahead — ${dist}`;
  if (a >= 22.5 && a < 67.5) return `↗ Turn right 45° — ${dist}`;
  if (a >= 67.5 && a < 112.5) return `→ Turn right — ${dist}`;
  if (a >= 112.5 && a < 157.5) return `↘ Behind right — ${dist}`;
  if (a >= 157.5 || a < -157.5) return `↓ Turn around — ${dist}`;
  if (a >= -157.5 && a < -112.5) return `↙ Behind left — ${dist}`;
  if (a >= -112.5 && a < -67.5) return `← Turn left — ${dist}`;
  return `↖ Turn left 45° — ${dist}`;
}
