import { UrgencyLevel } from '../types';

const styles: Record<UrgencyLevel, string> = {
  Critical: 'bg-red-100 text-red-800 border border-red-200',
  High: 'bg-amber-100 text-amber-800 border border-amber-200',
  Medium: 'bg-blue-100 text-blue-800 border border-blue-200',
  Low: 'bg-gray-100 text-gray-700 border border-gray-200',
};

export function UrgencyBadge({ level }: { level: UrgencyLevel }) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${styles[level]}`}>
      {level}
    </span>
  );
}
