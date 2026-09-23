import { useMemo, useState } from 'react';

interface ProfileAvatarProps {
  src?: string;
  fallbackSrc?: string;
  name: string;
  size?: number;
  className?: string;
}

function getInitials(name: string) {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('');
}

export function ProfileAvatar({ src, fallbackSrc, name, size = 72, className = '' }: ProfileAvatarProps) {
  const sourceKey = JSON.stringify([src || '', fallbackSrc || '']);
  const [failedState, setFailedState] = useState<{ key: string; urls: string[] } | null>(null);
  const failedUrls = failedState?.key === sourceKey ? failedState.urls : [];
  const currentSrc = [src, fallbackSrc].find((candidate) => candidate && !failedUrls.includes(candidate)) || '';
  const initials = useMemo(() => getInitials(name), [name]);

  return (
    <div
      className={`relative inline-flex shrink-0 overflow-hidden rounded-full bg-base-200 ${className}`}
      style={{ width: size, height: size }}
    >
      {currentSrc ? (
        <img
          src={currentSrc}
          alt={name}
          className="h-full w-full object-cover"
          loading="lazy"
          onError={() => {
            setFailedState((previous) => ({
              key: sourceKey,
              urls: [...(previous?.key === sourceKey ? previous.urls : []), currentSrc],
            }));
          }}
        />
      ) : (
        <span className="flex h-full w-full items-center justify-center bg-primary/10 text-sm font-bold text-primary">
          {initials}
        </span>
      )}
    </div>
  );
}
