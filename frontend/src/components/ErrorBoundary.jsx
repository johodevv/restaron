import React from 'react';
import { AlertTriangle, RefreshCw, LogOut } from 'lucide-react';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary ushlagan xatolik:', error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReload = () => {
    window.location.reload();
  };

  handleResetAndLogin = () => {
    try {
      localStorage.removeItem('restaron_token');
      localStorage.removeItem('token');
      sessionStorage.clear();
    } catch (e) {
      // Ignore
    }
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-950 text-white flex items-center justify-center p-4 font-sans select-none">
          <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 text-center shadow-2xl space-y-5">
            <div className="w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center mx-auto text-amber-400">
              <AlertTriangle className="w-8 h-8" />
            </div>

            <div className="space-y-2">
              <h2 className="text-xl font-extrabold text-white">Kutilmagan xatolik yuz berdi</h2>
              <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
                Tizimda vaqtinchalik xatolik yuz berdi. Iltimos, sahifani yangilang yoki tizimga qayta kiring.
              </p>
            </div>

            {/* Error Message Details (collapsible) */}
            {this.state.error && (
              <details className="text-left bg-slate-950/80 rounded-xl p-3 border border-slate-800 text-xs font-mono text-red-400">
                <summary className="cursor-pointer text-slate-400 font-sans hover:text-slate-300 font-bold select-none">
                  Xatolik tafsilotini ko'rish
                </summary>
                <div className="mt-2 overflow-x-auto whitespace-pre-wrap max-h-36 overflow-y-auto text-[11px] text-red-300">
                  {this.state.error?.toString()}
                  {this.state.errorInfo?.componentStack}
                </div>
              </details>
            )}

            {/* Action buttons */}
            <div className="space-y-2 pt-2">
              <button
                type="button"
                onClick={this.handleReload}
                className="w-full min-h-[46px] py-2.5 px-4 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-extrabold text-sm shadow-lg shadow-emerald-900/40 active:scale-95 transition-all flex items-center justify-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Sahifani yangilash</span>
              </button>

              <button
                type="button"
                onClick={this.handleResetAndLogin}
                className="w-full min-h-[42px] py-2 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white font-bold text-xs active:scale-95 transition-all flex items-center justify-center gap-2"
              >
                <LogOut className="w-4 h-4" />
                <span>Qayta tizimga kirish</span>
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
