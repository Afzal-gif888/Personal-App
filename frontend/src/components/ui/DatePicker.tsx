import React from 'react';
import { Calendar as CalendarIcon, Clock } from 'lucide-react';
import { Input } from './Input';
import type { InputProps } from './Input';

export const DatePicker = React.forwardRef<HTMLInputElement, Omit<InputProps, 'type'>>(
  (props, ref) => {
    return (
      <Input
        ref={ref}
        type="date"
        leftIcon={<CalendarIcon className="w-4 h-4" />}
        {...props}
      />
    );
  }
);
DatePicker.displayName = 'DatePicker';

export const TimePicker = React.forwardRef<HTMLInputElement, Omit<InputProps, 'type'>>(
  (props, ref) => {
    return (
      <Input
        ref={ref}
        type="time"
        leftIcon={<Clock className="w-4 h-4" />}
        {...props}
      />
    );
  }
);
TimePicker.displayName = 'TimePicker';
