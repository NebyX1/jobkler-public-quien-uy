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
 * Profile data now comes from JSON Server.
 */

export interface CategoryItem {
  icon: ComponentType<{ className?: string }>;
  name: string;
  description: string;
  count: string;
}

export interface LocalityItem {
  name: string;
  status: string;
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

export const TRUST_METRICS = [
  { value: '500+', label: 'Perfiles activos' },
  { value: '5', label: 'Departamentos' },
  { value: '100%', label: 'Contacto directo' },
];

export const CATEGORIES: CategoryItem[] = [
  { icon: Briefcase, name: 'Profesionales', description: 'Contadores, abogados, arquitectos y más.', count: '128 perfiles' },
  { icon: Wrench, name: 'Oficios', description: 'Electricistas, plomeros, albañiles, pintores.', count: '214 perfiles' },
  { icon: HeartPulse, name: 'Bienestar y salud', description: 'Psicólogos, fisioterapeutas, terapeutas.', count: '86 perfiles' },
  { icon: Sparkles, name: 'Belleza', description: 'Peluquería, maquillaje, uñas, estética.', count: '64 perfiles' },
  { icon: Home, name: 'Hogar', description: 'Limpieza, jardinería, mantenimiento, mudanzas.', count: '152 perfiles' },
  { icon: Laptop, name: 'Tecnología', description: 'Soporte, redes, desarrollo, reparación de PC.', count: '47 perfiles' },
  { icon: GraduationCap, name: 'Educación', description: 'Tutores, profesores, capacitaciones, idiomas.', count: '73 perfiles' },
  { icon: Flower2, name: 'Espiritualidad', description: 'Reiki, astrología, terapias alternativas.', count: '29 perfiles' },
  { icon: PartyPopper, name: 'Eventos', description: 'Catering, animación, sonido, fotografía.', count: '58 perfiles' },
  { icon: Tractor, name: 'Servicios rurales', description: 'Tractoristas, agronomía, ganadería, rurales.', count: '41 perfiles' },
];

export const LOCALITIES: LocalityItem[] = [
  { name: 'Minas', status: 'Activo' },
  { name: 'Lavalleja', status: 'Activo' },
  { name: 'Montevideo', status: 'Activo' },
  { name: 'Canelones', status: 'Activo' },
  { name: 'Maldonado', status: 'Activo' },
  { name: 'Todo Uruguay', status: 'Próximamente' },
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
  'Sin comisiones en esta primera etapa.',
];
