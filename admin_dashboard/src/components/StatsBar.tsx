import React from 'react';

interface Stat {
  label: string;
  value: number;
  color: 'blue' | 'green' | 'gray' | 'red' | 'yellow';
}

const colorMap: Record<string, string> = {
  blue: 'bg-blue-50 text-blue-800',
  green: 'bg-green-50 text-green-800',
  gray: 'bg-gray-50 text-gray-700',
  red: 'bg-red-50 text-red-800',
  yellow: 'bg-yellow-50 text-yellow-800',
};

export const StatsBar: React.FC<{ stats: Stat[] }> = ({ stats }) => (
  <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
    {stats.map((s) => (
      <div key={s.label} className={`rounded-xl p-4 ${colorMap[s.color]}`}>
        <p className="text-3xl font-bold">{s.value}</p>
        <p className="text-sm mt-1 font-medium opacity-80">{s.label}</p>
      </div>
    ))}
  </div>
);
