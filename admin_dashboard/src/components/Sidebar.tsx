import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

const navItems = [
  { to: '/dashboard', label: 'Devices', icon: '💻' },
  { to: '/sim-alerts', label: 'SIM Alerts', icon: '🔴' },
  { to: '/audit-logs', label: 'Audit Logs', icon: '📋' },
];

export const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();

  return (
    <div className="w-56 bg-blue-900 text-white flex flex-col h-screen">
      <div className="p-5 border-b border-blue-800">
        <p className="text-lg font-bold">MDM Admin</p>
        <p className="text-xs text-blue-300 mt-0.5">Device Management</p>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                isActive
                  ? 'bg-blue-800 text-white'
                  : 'text-blue-200 hover:bg-blue-800/50 hover:text-white'
              }`
            }
          >
            <span>{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-blue-800">
        <p className="text-xs text-blue-300 truncate mb-1">{user?.email}</p>
        <p className="text-xs text-blue-400 capitalize mb-3">{user?.role}</p>
        <button
          onClick={() => { logout(); navigate('/login'); }}
          className="w-full text-xs text-blue-300 hover:text-white transition py-1"
        >
          Sign Out
        </button>
      </div>
    </div>
  );
};
