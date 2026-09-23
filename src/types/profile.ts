/**
 * Type definitions for the Quien.uy profile model.
 *
 * Profile records returned by the local Flask API.
 */

export interface Profile {
  id: string;
  slug: string;
  name: string;
  displayName: string;
  category: string;
  categoryId: string;
  profession: string;
  professionNormalized: string;
  department: string;
  departmentId: string;
  locality: string;
  localityId: string;
  shortDescription: string;
  description: string;
  photoUrl: string;
  avatarFallback: string;
  phone: string;
  whatsapp: string;
  email: string;
  website: string;
  instagram: string;
  address: string;
  serviceArea: string[];
  tags: string[];
  availability: string;
  verified: boolean;
  rating: number;
  reviewsCount: number;
  yearsExperience: number;
  featured: boolean;
  ownerUserId?: string;
  status: 'active' | 'inactive';
  isOwner?: boolean;
  isFictionalDemo?: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface Category {
  id: string;
  name: string;
  slug: string;
  description: string;
  icon: string;
  featured: boolean;
  sortOrder: number;
}

export interface Department {
  id: string;
  name: string;
  slug: string;
  featured: boolean;
  sortOrder: number;
}

export interface Locality {
  id: string;
  name: string;
  slug: string;
  department: string;
  departmentId: string;
  featured: boolean;
  sortOrder: number;
}

export interface ProfileFilters {
  q?: string;
  department?: string;
  departmentId?: string;
  locality?: string;
  localityId?: string;
  category?: string;
  categoryId?: string;
  profession?: string;
  featured?: boolean;
  limit?: number;
  page?: number;
}

export interface PredictedLocation {
  department: string;
  locality: string;
  departmentId?: string;
  localityId?: string;
}

export interface Review {
  id: string;
  profileId: string;
  profileSlug: string;
  authorUserId?: string;
  authorName: string;
  authorPicture: string;
  rating: number;
  comment: string;
  status: 'published' | 'hidden';
  editable: boolean;
  acceptedNoEditPolicy: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface QuienUser {
  id: string;
  email: string;
  displayName: string;
  picture: string;
  provider: string;
  roles: string[];
  createdAt: string;
  updatedAt: string;
}
