import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { Modal } from './Modal';
import { Button } from './Button';

export interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  isDestructive?: boolean;
  isLoading?: boolean;
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = 'Delete',
  cancelText = 'Cancel',
  isDestructive = true,
  isLoading = false,
}) => (
  <Modal
    isOpen={isOpen}
    onClose={onClose}
    maxWidth="sm"
    footer={
      <>
        <Button variant="secondary" size="sm" onClick={onClose} disabled={isLoading}>
          {cancelText}
        </Button>
        <Button variant={isDestructive ? 'destructive' : 'primary'} size="sm" onClick={onConfirm} isLoading={isLoading}>
          {confirmText}
        </Button>
      </>
    }
  >
    <div className="flex items-start gap-4 -mt-2">
      {isDestructive && (
        <span className="flex items-center justify-center size-10 shrink-0 rounded-full bg-danger-subtle">
          <AlertTriangle className="size-5 text-danger" />
        </span>
      )}
      <div>
        <h2 className="text-base font-semibold text-fg">{title}</h2>
        <p className="text-sm text-fg-subtle mt-1">{message}</p>
      </div>
    </div>
  </Modal>
);
