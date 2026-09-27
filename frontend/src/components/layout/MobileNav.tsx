import React from 'react';
import { Logo } from '../ui/Logo';
import { Drawer } from '../ui/Drawer';
import { NavList, NavRow } from './NavList';
import { SETTINGS_NAV } from '../../config/navigation';
import { useUIStore } from '../../stores/uiStore';

export const MobileNav: React.FC = () => {
  const { mobileDrawerOpen, setMobileDrawerOpen } = useUIStore();
  const close = () => setMobileDrawerOpen(false);

  return (
    <Drawer isOpen={mobileDrawerOpen} onClose={close} title={<Logo size="sm" withText subtext="Personal workspace" />}>
      <div className="flex flex-col min-h-full">
        <NavList onNavigate={close} />
        <div className="mt-auto pt-4 border-t border-line">
          <NavRow item={SETTINGS_NAV} onNavigate={close} />
        </div>
      </div>
    </Drawer>
  );
};
