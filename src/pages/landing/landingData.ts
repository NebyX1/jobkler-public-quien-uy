import {
  Briefcase,
  Wrench,
  HeartPulse,
  Sparkles,
  Home,
  Laptop,
  GraduationCap,
  Flower2,
  PartyPopper,
  Tractor,
  ClipboardList,
  MapPin,
  ShieldCheck,
  Flag,
} from 'lucide-react';
import type { ComponentType } from 'react';

/**
 * UI-only data for the Quien.uy landing page.
 * Profile data now comes from the Flask API.
 */

export interface CategoryItem {
  id: string;
  icon: ComponentType<{ className?: string }>;
  name: string;
  description: string;
}

export interface StepItem {
  step: string;
  title: string;
  description: string;
}

export interface TrustItem {
  icon: ComponentType<{ className?: string }>;
  title: string;
  description: string;
}

export const QUICK_CHIPS = [
  'Electricista',
  'Sanitaria',
  'Belleza',
  'Psicología',
  'Jardinería',
  'Informática',
  'Limpieza',
  'Eventos',
];

export const CATEGORIES: CategoryItem[] = [
  { id: 'profesionales', icon: Briefcase, name: 'Profesionales', description: 'Profesionales independientes.' },
  { id: 'oficios', icon: Wrench, name: 'Oficios', description: 'Oficios y mantenimiento.' },
  { id: 'bienestar-y-salud', icon: HeartPulse, name: 'Bienestar y salud', description: 'Bienestar y salud.' },
  { id: 'belleza', icon: Sparkles, name: 'Belleza', description: 'Cuidado personal y belleza.' },
  { id: 'hogar', icon: Home, name: 'Hogar', description: 'Servicios para el hogar.' },
  { id: 'tecnologia', icon: Laptop, name: 'Tecnología', description: 'Tecnología y soporte.' },
  { id: 'educacion', icon: GraduationCap, name: 'Educación', description: 'Clases y apoyo educativo.' },
  { id: 'espiritualidad', icon: Flower2, name: 'Espiritualidad', description: 'Servicios de espiritualidad.' },
  { id: 'eventos', icon: PartyPopper, name: 'Eventos', description: 'Servicios para eventos.' },
  { id: 'servicios-rurales', icon: Tractor, name: 'Servicios rurales', description: 'Oficios y servicios rurales.' },
];

export const STEPS: StepItem[] = [
  { step: '1', title: 'Buscá lo que necesitás.', description: 'Escribí el servicio, profesión, oficio o necesidad.' },
  { step: '2', title: 'Elegí por zona y perfil.', description: 'Compará ubicación, rubro, datos disponibles y formas de contacto.' },
  { step: '3', title: 'Contactá directo.', description: 'Hablá por WhatsApp, teléfono o redes.' },
];

export const TRUST_ITEMS: TrustItem[] = [
  { icon: ClipboardList, title: 'Datos claros', description: 'Cada perfil muestra rubro, zona y formas de contacto.' },
  { icon: MapPin, title: 'Búsqueda por localidad', description: 'Filtrá por ciudad o departamento para encontrar cerca.' },
  { icon: ShieldCheck, title: 'Perfiles revisados', description: 'Moderamos perfiles para mantener la red ordenada.' },
  { icon: Flag, title: 'Reportes de información incorrecta', description: 'Podés reportar datos desactualizados o incorrectos.' },
];

export const PROVIDER_BENEFITS = [
  'Presencia digital simple.',
  'Contacto directo.',
  'Visibilidad local.',
  'Perfil compartible.',
];
