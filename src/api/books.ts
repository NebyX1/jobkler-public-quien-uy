import { apiClient } from './client';
import type { Book, BookFormData, BooksListResponse } from '../types';

export interface BooksQueryParams {
  page?: number;
  per_page?: number;
  search?: string;
  genre?: string;
  availability?: 'all' | 'available' | 'unavailable';
}

export const booksApi = {
  list: async (params: BooksQueryParams = {}): Promise<BooksListResponse> => {
    const res = await apiClient.get<BooksListResponse>('/api/books', { params });
    return res.data;
  },

  get: async (id: number): Promise<Book> => {
    const res = await apiClient.get<{ book: Book }>(`/api/books/${id}`);
    return res.data.book;
  },

  checkAvailability: async (id: number) => {
    const res = await apiClient.get(`/api/books/${id}/availability`);
    return res.data;
  },

  create: async (data: BookFormData): Promise<Book> => {
    const res = await apiClient.post<{ book: Book }>('/api/books', data);
    return res.data.book;
  },

  update: async (id: number, data: Partial<BookFormData>): Promise<Book> => {
    const res = await apiClient.put<{ book: Book }>(`/api/books/${id}`, data);
    return res.data.book;
  },

  delete: async (id: number): Promise<{ message: string }> => {
    const res = await apiClient.delete<{ message: string }>(`/api/books/${id}`);
    return res.data;
  },

  genres: async (): Promise<string[]> => {
    const res = await apiClient.get<{ genres: string[] }>('/api/books/genres');
    return res.data.genres;
  },
};
