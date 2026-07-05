import { create } from 'zustand';
import type { AvailabilityFilter } from '../types';

interface BooksFilterState {
  searchQuery: string;
  genreFilter: string;
  availabilityFilter: AvailabilityFilter;
  page: number;
  setSearchQuery: (q: string) => void;
  setGenreFilter: (g: string) => void;
  setAvailabilityFilter: (f: AvailabilityFilter) => void;
  setPage: (p: number) => void;
  resetFilters: () => void;
}

export const useBooksStore = create<BooksFilterState>((set) => ({
  searchQuery: '',
  genreFilter: '',
  availabilityFilter: 'all',
  page: 1,

  setSearchQuery: (q) => set({ searchQuery: q, page: 1 }),
  setGenreFilter: (g) => set({ genreFilter: g, page: 1 }),
  setAvailabilityFilter: (f) => set({ availabilityFilter: f, page: 1 }),
  setPage: (p) => set({ page: p }),
  resetFilters: () =>
    set({ searchQuery: '', genreFilter: '', availabilityFilter: 'all', page: 1 }),
}));
