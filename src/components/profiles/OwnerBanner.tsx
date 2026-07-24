import { Link } from 'react-router-dom';
import { Pencil, Crown } from 'lucide-react';

interface OwnerBannerProps {
  profileSlug: string;
}

/**
 * Subtle banner shown on the public profile page when the logged-in
 * user owns this profile.
 */
export function OwnerBanner(props: OwnerBannerProps) {
  void props.profileSlug;
  return (
    <div className="rounded-2xl border border-primary/20 bg-primary/5 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10">
            <Crown className="h-5 w-5 text-primary" />
          </div>
          <div>
            <p className="font-semibold text-base-content">Este es tu perfil público</p>
            <p className="text-xs text-base-content/60">
              Otros usuarios ven este perfil cuando te buscan.
            </p>
          </div>
        </div>
        <Link
          to="/mi-perfil/editar"
          className="btn btn-primary btn-sm rounded-full"
        >
          <Pencil className="h-4 w-4" />
          Editar perfil
        </Link>
      </div>
    </div>
  );
}
