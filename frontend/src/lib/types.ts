export type Role = "READER" | "JOURNALIST" | "EDITOR" | "ADMIN" | "SUPER_ADMIN";
export type ArticleStatus = "DRAFT" | "SUBMITTED" | "PUBLISHED" | "REJECTED";

export interface User {
  id: number;
  username: string;
  role: Role;
  email?: string | null;
  bio?: string | null;
  is_active?: boolean;
  created_at: string;
}

export interface Article {
  id: number;
  slug?: string | null;
  title: string;
  content: string;
  summary?: string | null;
  category: string;
  image_url?: string | null;
  image_caption?: string | null;
  tags?: string | null;
  status: ArticleStatus;
  view_count: number;
  is_pinned: boolean;
  is_breaking: boolean;
  created_at: string;
  updated_at: string;
  published_at?: string | null;
  author: User;
  editor?: User | null;
}

export interface SiteSettings {
  site_name: string;
  site_motto: string;
  est_year?: string;
  edition_number?: string;
  breaking_news: string;
  breaking_active: boolean;
  categories: string[];

  features?: {
    comments_enabled?: boolean;
    registration_open?: boolean;
    maintenance_mode?: boolean;
  };
}

export interface ApiErrorBody {
  detail?: string | Array<{ msg?: string }>;
}
