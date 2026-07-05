import { useEffect, useMemo, useState } from 'react';

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
  const [currentSrc, setCurrentSrc] = useState(src || fallbackSrc || '');
  const [hasError, setHasError] = useState(false);
  const initials = useMemo(() => getInitials(name), [name]);

  useEffect(() => {
    setHasError(false);
    setCurrentSrc(src || fallbackSrc || '');
  }, [src, fallbackSrc]);

  return (
    <div
      className={`relative inline-flex shrink-0 overflow-hidden rounded-full bg-base-200 ${className}`}
      style={{ width: size, height: size }}
    >
      {currentSrc && !hasError ? (
        <img
          src={currentSrc}
          alt={name}
          className="h-full w-full object-cover"
          loading="lazy"
          onError={() => {
            if (fallbackSrc && currentSrc !== fallbackSrc) {
              setCurrentSrc(fallbackSrc);
              return;
            }

            setHasError(true);
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
