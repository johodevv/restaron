import React from 'react';
import { useWebSocket } from '../context/WebSocketContext';
import { X, Bell, CheckCircle2, AlertCircle } from 'lucide-react';

export const ToastContainer = () => {
  const { notifications, removeNotification } = useWebSocket();

  if (!notifications.length) return null;

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-3 max-w-sm w-full pointer-events-none">
      {notifications.map((n) => {
        let borderClass = 'border-theme-primary';
        let bgIcon = <Bell className="w-5 h-5 text-theme-primary shrink-0" />;

        if (n.type === 'urgent') {
          borderClass = 'border-red-500 shadow-lg shadow-red-500/20';
          bgIcon = <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />;
        } else if (n.type === 'success') {
          borderClass = 'border-emerald-500 shadow-lg shadow-emerald-500/20';
          bgIcon = <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />;
        }

        return (
          <div
            key={n.id}
            className={`pointer-events-auto flex items-start gap-3 p-4 rounded-xl glass-card border ${borderClass} bg-theme-surface/90 shadow-2xl backdrop-blur-md animate-slide-up text-theme-text`}
          >
            {bgIcon}
            <div className="flex-1 min-w-0">
              <h4 className="font-semibold text-sm leading-tight text-white mb-1">
                {n.title}
              </h4>
              <p className="text-xs text-theme-muted line-clamp-2">
                {n.message}
              </p>
            </div>
            <button
              onClick={() => removeNotification(n.id)}
              className="text-theme-muted hover:text-white transition-colors p-1"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
};

export default ToastContainer;
