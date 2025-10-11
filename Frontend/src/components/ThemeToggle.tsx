import React from 'react';
import { Sun, Moon, Leaf } from 'lucide-react';
import { useTheme, Theme } from '../context/ThemeContext';

const ThemeToggle: React.FC = () => {
  const { theme, setTheme } = useTheme();

  const themes: { value: Theme; icon: React.ComponentType<any>; label: string; color: string }[] = [
    { value: 'light', icon: Sun, label: 'Light', color: 'text-yellow-500' },
    { value: 'dark', icon: Moon, label: 'Dark', color: 'text-blue-400' }
  ];

  return (
    <div className="flex items-center space-x-1 bg-theme-card border border-theme-border rounded-lg p-1">
      {themes.map(({ value, icon: Icon, label, color }) => (
        <button
          key={value}
          onClick={() => setTheme(value)}
          className={`flex items-center space-x-1 px-3 py-2 rounded-md text-sm font-medium transition-all duration-200 ${
            theme === value
              ? 'bg-theme-primary text-white shadow-sm'
              : 'text-theme-text-secondary hover:bg-theme-hover hover:text-theme-text-primary'
          }`}
          title={`Switch to ${label} mode`}
        >
          <Icon className={`h-4 w-4 ${theme === value ? 'text-white' : color}`} />
          <span className="hidden sm:inline">{label}</span>
        </button>
      ))}
    </div>
  );
};

export default ThemeToggle;