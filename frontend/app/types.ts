/** Mirrors backend QueryIntent enum */
export type QueryIntent =
  | "professor"
  | "course"
  | "housing"
  | "dining"
  | "campus_resource"
  | "location"
  | "general";

/** Mirrors backend SourceType enum */
export type SourceType =
  | "vector_db"
  | "rate_my_professor"
  | "reddit"
  | "web"
  | "google_maps"
  | "curated";

/** One ranked source with attribution */
export interface SourceAttribution {
  title: string;
  source_type: SourceType;
  url?: string;
  relevance_score: number;
  snippet: string;
}

/** Structured professor data card */
export interface ProfessorCard {
  name: string;
  department: string;
  overall_rating: number | null;
  difficulty: number | null;
  would_take_again: number | null;
  num_ratings: number;
  profile_url: string | null;
}

/** Curated UC Davis resource link */
export interface CampusResource {
  name: string;
  category: string;
  url?: string;
  description: string;
}

/** Contact info from UC Davis Directory API */
export interface DirectoryContact {
  full_name: string;
  email: string | null;
  department: string | null;
  title: string | null;
  phone: string | null;
  address: string | null;
}

/** Full structured API response */
export interface ChatAPIResponse {
  intent: QueryIntent;
  summary: string;
  sources: SourceAttribution[];
  professor_card: ProfessorCard | null;
  directory_contacts: DirectoryContact[];
  campus_resources: CampusResource[];
  cached: boolean;
  query_time_ms: number;
}

/** Frontend message representation */
export interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: SourceAttribution[];
  professorCard?: ProfessorCard;
  directoryContacts?: DirectoryContact[];
  campusResources?: CampusResource[];
  intent?: QueryIntent;
  cached?: boolean;
  queryTimeMs?: number;
  imagePreview?: string;
}

/** Conversation for sidebar */
export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  timestamp: number;
}
