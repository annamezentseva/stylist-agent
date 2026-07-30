// Типы зеркалят контракт бэкенда (app/schemas.py). Держим их в одном месте.

// Что решил агент: собрал образ / ответил советом / не хватает данных.
export type StylistAction = "look" | "advice" | "need_info";

export interface Item {
  id: string;
  title: string;
  brand: string;
  category: string;
  color: string;
  price: number;
  sizes: string[];
  style_tags: string[];
  in_stock: boolean;
  moscow_available: boolean;
  store: string;
  url: string;
  image_url: string;
}

export interface LookOut {
  id: number | null;
  action: StylistAction;
  answer: string;
  items: Item[];
  rationale: string;
  sources: string[];
  missing: string[];
  total_price: number;
}

export interface LookSummary {
  id: number;
  request_text: string;
  action: StylistAction;
  created_at: string;
}

export interface Appearance {
  color_type: string | null;
  undertone: string | null;
  contrast: string | null;
  body_shape: string | null;
  face_shape: string | null;
}

export interface StyleProfile {
  styles: string[];
  palette: string[];
  silhouettes: string[];
  likes: string[];
  dislikes: string[];
}

export interface Constraints {
  occasion: string | null;
  budget_rub: number | null;
  season: string | null;
  sizes: Record<string, string>;
  avoid: string[];
}

export interface Profile {
  user_id: string;
  appearance: Partial<Appearance>;
  style_profile: Partial<StyleProfile>;
  constraints: Partial<Constraints>;
}

// Человекочитаемые подписи действий агента.
export const ACTION_LABELS: Record<StylistAction, string> = {
  look: "Образ собран",
  advice: "Совет стилиста",
  need_info: "Нужны данные",
};

// Порядок слотов в карточке образа — как надевают, сверху вниз.
export const SLOT_ORDER = [
  "верхняя одежда",
  "верх",
  "низ",
  "обувь",
  "аксессуар",
];
