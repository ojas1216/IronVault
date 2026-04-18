import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface UsageEntry {
  app: string;
  duration_minutes: number;
  is_work_app: boolean;
}

export const AppUsageChart: React.FC<{ data: UsageEntry[] }> = ({ data }) => {
  if (!data.length) {
    return (
      <div className="h-48 bg-gray-50 rounded-lg flex items-center justify-center text-gray-500">
        No app usage data
      </div>
    );
  }

  const sorted = [...data]
    .sort((a, b) => b.duration_minutes - a.duration_minutes)
    .slice(0, 15);

  return (
    <div>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={sorted} layout="vertical" margin={{ left: 100 }}>
          <XAxis type="number" unit="min" tick={{ fontSize: 11 }} />
          <YAxis type="category" dataKey="app" tick={{ fontSize: 11 }} width={100} />
          <Tooltip formatter={(val) => [`${val} min`, 'Usage']} />
          <Bar dataKey="duration_minutes" radius={[0, 4, 4, 0]}>
            {sorted.map((entry, i) => (
              <Cell
                key={i}
                fill={entry.is_work_app ? '#1565C0' : '#ef4444'}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="flex gap-4 mt-2 text-xs text-gray-600">
        <span><span className="inline-block w-3 h-3 bg-blue-800 rounded mr-1" />Work apps</span>
        <span><span className="inline-block w-3 h-3 bg-red-500 rounded mr-1" />Non-work apps</span>
      </div>
    </div>
  );
};
