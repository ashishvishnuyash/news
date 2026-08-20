export type Role = "READER" | "JOURNALIST" | "EDITOR" | "ADMIN" | "SUPER_ADMIN";
export type ArticleStatus = "DRAFT" | "FACT_CHECK" | "EDITOR_REVIEW" | "APPROVED" | "SCHEDULED" | "SUBMITTED" | "PUBLISHED" | "REJECTED";
export type ArticleType = "NEWS" | "OPINION" | "INVESTIGATION" | "FACT_CHECK" | "LIVE";
export type FactCheckRating = "TRUE" | "FALSE" | "PARTLY_TRUE" | "MISLEADING" | "UNVERIFIED";

export interface User {
  id: number;
  username: string;
  role: Role;
  email?: string | null;
  bio?: string | null;
  slug?: string | null;
  profile_image_url?: string | null;
  job_title?: string | null;
  coverage_areas?: string | null;
  social_links?: string | null;
  is_active?: boolean;
  created_at: string;
}

export interface Article {
  id: number;
  slug?: string | null;
  title: string;
  subtitle?: string | null;
  content: string;
  summary?: string | null;
  category: string;
  image_url?: string | null;
  image_caption?: string | null;
  tags?: string | null;
  sources?: string | null;
  seo_title?: string | null;
  seo_description?: string | null;
  og_image_url?: string | null;
  article_type: ArticleType;
  fact_check_rating?: FactCheckRating | null;
  scheduled_at?: string | null;
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

export type ArticleIndex = Omit<Article, "content" | "sources" | "seo_title" | "seo_description" | "og_image_url" | "scheduled_at" | "status" | "editor"> & {
  content?: string;
};

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
  contact?: Partial<Record<"general" | "tips" | "corrections" | "advertising" | "press", string>>;
  publication?: {
    legal_name?: string;
    owner?: string;
    address?: string;
    editor_in_chief?: string;
  };
  advertising?: {
    enabled?: boolean;
    slots?: Partial<Record<"header" | "homepage" | "in_feed" | "article" | "sidebar" | "footer", string>>;
  };
  analytics?: { provider?: string; measurement_id?: string };
  newsletter?: { enabled?: boolean; name?: string; description?: string };
}

export interface ArticleSearchResponse {
  items: Article[];
  total: number;
  limit: number;
  offset: number;
  suggestions: string[];
}

export interface AuthorProfile {
  author: User;
  articles: Article[];
  total_articles: number;
  total_views: number;
  coverage_areas: string[];
}

export interface Correction {
  id: number;
  article_id: number;
  summary: string;
  details?: string | null;
  created_at: string;
  article_title: string;
  article_slug?: string | null;
  recorded_by: string;
}

export interface LiveUpdate {
  id: number;
  article_id: number;
  content: string;
  created_at: string;
  updated_at: string;
  author: User;
}

export interface ApiErrorBody {
  detail?: string | Array<{ msg?: string }>;
}
