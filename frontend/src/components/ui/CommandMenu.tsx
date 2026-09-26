import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  LayoutDashboard,
  MessageSquare,
  CheckSquare,
  CalendarDays,
  BookOpen,
  Bell,
  FileText,
  Activity,
  ShieldCheck,
  User,
  Plus,
  Sparkles,
  Receipt,
  Wallet,
  Target,
} from 'lucide-react';
import { useUIStore } from '../../stores/uiStore';

export const CommandMenu: React.FC = () => {
  const { commandMenuOpen, setCommandMenuOpen } = useUIStore();
  const [query, setQuery] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCommandMenuOpen(!commandMenuOpen);
      }
      if (e.key === 'Escape' && commandMenuOpen) {
        setCommandMenuOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [commandMenuOpen, setCommandMenuOpen]);

  if (!commandMenuOpen) return null;

  const actions = [
    { id: 'nav-dashboard', label: 'Go to Dashboard', category: 'Navigation', icon: <LayoutDashboard className="w-4 h-4" />, path: '/dashboard' },
    { id: 'nav-chat', label: 'Go to AI Assistant', category: 'Navigation', icon: <MessageSquare className="w-4 h-4" />, path: '/chat' },
    { id: 'nav-tasks', label: 'Go to Tasks', category: 'Navigation', icon: <CheckSquare className="w-4 h-4" />, path: '/tasks' },
    { id: 'nav-calendar', label: 'Go to Calendar', category: 'Navigation', icon: <CalendarDays className="w-4 h-4" />, path: '/calendar' },
    { id: 'nav-plan', label: 'Go to Study Plan', category: 'Navigation', icon: <BookOpen className="w-4 h-4" />, path: '/study-plan' },
    { id: 'nav-reminders', label: 'Go to Reminders', category: 'Navigation', icon: <Bell className="w-4 h-4" />, path: '/reminders' },
    { id: 'nav-docs', label: 'Go to Documents', category: 'Navigation', icon: <FileText className="w-4 h-4" />, path: '/documents' },
    { id: 'nav-bills', label: 'Go to Bills & Payments', category: 'Navigation', icon: <Receipt className="w-4 h-4" />, path: '/bills' },
    { id: 'nav-expenses', label: 'Go to Expenses', category: 'Navigation', icon: <Wallet className="w-4 h-4" />, path: '/expenses' },
    { id: 'nav-goals', label: 'Go to Goals', category: 'Navigation', icon: <Target className="w-4 h-4" />, path: '/goals' },
    { id: 'nav-agent-runs', label: 'Go to Agent Runs', category: 'Navigation', icon: <Activity className="w-4 h-4" />, path: '/agent-runs' },
    { id: 'nav-approvals', label: 'Go to Approvals', category: 'Navigation', icon: <ShieldCheck className="w-4 h-4" />, path: '/approvals' },
    { id: 'nav-settings', label: 'Go to Profile Settings', category: 'Navigation', icon: <User className="w-4 h-4" />, path: '/settings/profile' },
    { id: 'action-ask-ai', label: 'Ask AI Assistant...', category: 'Quick Action', icon: <Sparkles className="w-4 h-4 text-emerald-600" />, path: '/chat' },
    { id: 'action-add-task', label: 'Create New Task', category: 'Quick Action', icon: <Plus className="w-4 h-4" />, path: '/tasks' },
    { id: 'action-add-reminder', label: 'Create New Reminder', category: 'Quick Action', icon: <Plus className="w-4 h-4" />, path: '/reminders' },
    { id: 'action-add-expense', label: 'Add Expense', category: 'Quick Action', icon: <Plus className="w-4 h-4" />, path: '/expenses' },
  ];

  const filtered = actions.filter((a) =>
    a.label.toLowerCase().includes(query.toLowerCase()) || a.category.toLowerCase().includes(query.toLowerCase())
  );

  const handleSelect = (path: string) => {
    navigate(path);
    setCommandMenuOpen(false);
    setQuery('');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-black/40 backdrop-blur-xs">
      <div className="fixed inset-0" onClick={() => setCommandMenuOpen(false)} />
      <div className="relative w-full max-w-lg rounded-lg border border-[#EAEAEA] bg-white shadow-xl overflow-hidden z-10 text-left">
        <div className="flex items-center px-3.5 border-b border-[#EAEAEA]">
          <Search className="w-4 h-4 text-[#8A8A8A] shrink-0 mr-2" />
          <input
            type="text"
            autoFocus
            placeholder="Type a command or search page..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full h-11 bg-transparent text-xs sm:text-sm text-[#111111] placeholder:text-[#8A8A8A] focus:outline-none"
          />
          <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono text-[#8A8A8A] bg-[#F7F7F7] border border-[#EAEAEA] rounded">
            ESC
          </kbd>
        </div>

        <div className="max-h-72 overflow-y-auto p-1.5 space-y-1">
          {filtered.length === 0 ? (
            <div className="p-4 text-center text-xs text-[#8A8A8A]">No matching commands found.</div>
          ) : (
            filtered.map((item) => (
              <button
                key={item.id}
                onClick={() => handleSelect(item.path)}
                className="w-full flex items-center justify-between px-3 py-2 text-xs rounded-md hover:bg-[#F7F7F7] transition-colors text-left"
              >
                <div className="flex items-center gap-2.5 text-[#111111]">
                  <span className="text-[#8A8A8A]">{item.icon}</span>
                  <span className="font-medium">{item.label}</span>
                </div>
                <span className="text-[10px] text-[#8A8A8A] bg-[#F7F7F7] px-1.5 py-0.5 rounded border border-[#EAEAEA]">
                  {item.category}
                </span>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
