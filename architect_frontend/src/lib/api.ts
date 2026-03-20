// architect_frontend/src/lib/api.ts

/**
 * Typed wrapper around the Architect HTTP API.
 *
 * Goals:
 * - Default base URL targets /api/v1
 * - Prefer the canonical public HTTP contract
 * - Remain robust against a small set of migration-era endpoint/path variants
 * - Keep frontend/client convenience separate from the canonical transport shape
 *
 * Canonical generation response:
 * - text
 * - lang_code
 * - construction_id
 * - renderer_backend
 * - fallback_used
 * - tokens
 * - debug_info
 * - generation_time_ms
 */

const DEFAULT_API_BASE_URL =
  process.env.NODE_ENV === "production"
    ? "/api/v1"
    : "http://127.0.0.1:8000/api/v1";

const API_BASE_URL = (
  process.env.NEXT_PUBLIC_ARCHITECT_API_BASE_URL ?? DEFAULT_API_BASE_URL
).replace(/\/$/, "");

const DEV_API_KEY = process.env.NEXT_PUBLIC_ARCHITECT_API_KEY;

export class ApiError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

function joinUrl(base: string, path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${base}${p}`;
}

function extractErrorMessage(parsed: unknown, status: number): string {
  if (typeof parsed === "string" && parsed.trim()) return parsed;
  if (parsed && typeof parsed === "object") {
    const obj = parsed as Record<string, unknown>;
    if (typeof obj.detail === "string" && obj.detail.trim()) return obj.detail;
    if (typeof obj.message === "string" && obj.message.trim()) return obj.message;
    if (typeof obj.error === "string" && obj.error.trim()) return obj.error;
  }
  return `API request failed with status ${status}`;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const url = joinUrl(API_BASE_URL, path);

  const headers = new Headers(init.headers ?? {});
  if (!headers.has("Accept")) headers.set("Accept", "application/json");

  // Dev-only header injection (do not rely on this for production security).
  if (DEV_API_KEY && !headers.has("x-api-key")) headers.set("x-api-key", DEV_API_KEY);

  if (
    init.body != null &&
    typeof init.body !== "string" &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(url, { ...init, headers });

  let parsed: unknown = null;
  const contentType = response.headers.get("content-type") ?? "";

  if (contentType.includes("application/json")) {
    try {
      parsed = await response.json();
    } catch {
      parsed = null;
    }
  } else {
    try {
      parsed = await response.text();
    } catch {
      parsed = null;
    }
  }

  if (!response.ok) {
    console.error("API Request Failed:", url, response.status, parsed);
    throw new ApiError(
      extractErrorMessage(parsed, response.status),
      response.status,
      parsed,
    );
  }

  return parsed as T;
}

async function requestWithFallback<T>(
  paths: string[],
  init?: RequestInit,
): Promise<T> {
  let lastErr: unknown = null;

  for (const p of paths) {
    try {
      return await request<T>(p, init);
    } catch (e) {
      lastErr = e;
      if (e instanceof ApiError && e.status !== 404) break;
    }
  }

  throw lastErr;
}

/* -------------------------------------------------------------------------- */
/* Shared helpers                                                             */
/* -------------------------------------------------------------------------- */

type JsonObject = Record<string, unknown>;

function asObject(value: unknown): JsonObject | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as JsonObject)
    : null;
}

function firstNonEmptyString(...values: unknown[]): string | null {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return null;
}

function asBoolean(value: unknown): boolean | undefined {
  return typeof value === "boolean" ? value : undefined;
}

function asStringArray(value: unknown): string[] | null {
  if (!Array.isArray(value)) return null;
  return value.map((item) => String(item));
}

/**
 * Lightweight transport tokenization.
 *
 * This intentionally keeps punctuation attached when split by whitespace,
 * matching the public transport contract's lightweight semantics.
 */
function tokenizeTransportText(text: string): string[] {
  return text
    .split(/\s+/)
    .map((token) => token.trim())
    .filter(Boolean);
}

function requireStringField(
  value: string | null,
  fieldName: string,
): string {
  if (!value) {
    throw new Error(`Non-conformant generation response: missing ${fieldName}`);
  }
  return value;
}

function normalizeGenerationResult(
  raw: unknown,
  options: {
    requestedLangCode?: string;
    compatibilityRuntimePath?: string;
  } = {},
): GenerationResult {
  const root = asObject(raw);
  if (!root) {
    throw new Error("Non-conformant generation response: expected object.");
  }

  const rawDebugInfo = asObject(root.debug_info) ?? asObject(root.debug) ?? {};

  const text = requireStringField(
    firstNonEmptyString(root.text, root.surface_text),
    "text",
  );

  const langCode = requireStringField(
    firstNonEmptyString(
      root.lang_code,
      root.lang,
      root.language,
      rawDebugInfo.lang_code,
      options.requestedLangCode,
    ),
    "lang_code",
  );

  const constructionId = requireStringField(
    firstNonEmptyString(root.construction_id, rawDebugInfo.construction_id),
    "construction_id",
  );

  const rendererBackend = requireStringField(
    firstNonEmptyString(root.renderer_backend, rawDebugInfo.renderer_backend),
    "renderer_backend",
  );

  const fallbackUsed =
    asBoolean(root.fallback_used) ??
    asBoolean(rawDebugInfo.fallback_used) ??
    (options.compatibilityRuntimePath ? true : undefined);

  if (typeof fallbackUsed !== "boolean") {
    throw new Error(
      "Non-conformant generation response: missing fallback_used",
    );
  }

  const runtimePath =
    firstNonEmptyString(rawDebugInfo.runtime_path) ??
    options.compatibilityRuntimePath;

  if (!runtimePath) {
    throw new Error(
      "Non-conformant generation response: missing debug_info.runtime_path",
    );
  }

  const slotKeys = asStringArray(rawDebugInfo.slot_keys) ?? [];
  const tokens = asStringArray(root.tokens) ?? tokenizeTransportText(text);

  const generationTimeMs =
    typeof root.generation_time_ms === "number" ? root.generation_time_ms : 0.0;

  const debugInfo: GenerationDebugInfo = {
    ...rawDebugInfo,
    runtime_path: runtimePath,
    construction_id: constructionId,
    renderer_backend: rendererBackend,
    lang_code: langCode,
    fallback_used: fallbackUsed,
    slot_keys: slotKeys,
  };

  return {
    text,
    lang_code: langCode,
    construction_id: constructionId,
    renderer_backend: rendererBackend,
    fallback_used: fallbackUsed,
    tokens,
    debug_info: debugInfo,
    generation_time_ms: generationTimeMs,
  };
}

function resolveGenerateLangCode(req: GenerateRequest): string {
  const langCode = req.lang_code ?? req.lang;
  if (!langCode || !langCode.trim()) {
    throw new Error("GenerateRequest requires lang_code or lang.");
  }
  return langCode.trim();
}

/* -------------------------------------------------------------------------- */
/* Frame Registry Types                                                       */
/* -------------------------------------------------------------------------- */

export interface LocalizedLabel {
  text: string;
  translations?: Record<string, string>;
}

export interface FrameTypeMeta {
  frame_type: string; // e.g. "bio", "event.generic"
  family: string; // e.g. "entity", "event"
  title?: string | LocalizedLabel;
  description?: string | LocalizedLabel;
  status?: "implemented" | "experimental" | "planned";
}

/**
 * Helper to safely extract text from a label that might be a string or object.
 */
export function getLabelText(
  val: string | LocalizedLabel | undefined | null,
): string {
  if (!val) return "";
  if (typeof val === "string") return val;
  return val.text || "";
}

/* -------------------------------------------------------------------------- */
/* Language Types                                                             */
/* -------------------------------------------------------------------------- */

export interface Language {
  code: string; // public API language code, e.g. "en", "fr"
  name: string; // e.g. "English"
  z_id: string; // optional catalog / inventory ID
}

/* -------------------------------------------------------------------------- */
/* Domain Types (Entities)                                                    */
/* -------------------------------------------------------------------------- */

export interface Entity {
  id: number;
  name: string;
  slug?: string;
  lang: string;

  frame_type?: string;
  frame_payload?: Record<string, unknown>;

  short_description?: string;
  notes?: string;
  tags?: string[];
  metadata?: Record<string, unknown>;

  created_at: string;
  updated_at: string;
}

export interface EntityCreatePayload {
  name: string;
  slug?: string;
  lang?: string;
  frame_type?: string;
  frame_payload?: Record<string, unknown>;
  short_description?: string;
  tags?: string[];
}

export interface EntityUpdatePayload {
  name?: string;
  slug?: string;
  lang?: string;
  frame_type?: string;
  frame_payload?: Record<string, unknown>;
  short_description?: string;
  notes?: string;
  tags?: string[];
}

/* -------------------------------------------------------------------------- */
/* AI / Intelligence Types                                                    */
/* -------------------------------------------------------------------------- */

export interface AIMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface AIFramePatch {
  path: string;
  value: unknown;
  op?: "replace" | "add" | "remove";
}

export interface IntentRequest {
  message: string;
  lang?: string;
  workspace_slug?: string;

  context_frame?: {
    frame_type: string;
    payload: Record<string, unknown>;
  };

  debug?: boolean;
}

export interface IntentResponse {
  intent_label: string;
  assistant_messages: AIMessage[];
  patches: AIFramePatch[];
  debug?: Record<string, unknown>;
}

export interface SuggestionRequest {
  frame_type: string;
  current_payload?: Record<string, unknown>;
  field_name?: string;
  partial_input?: string;
}

export interface SuggestionResponse {
  suggestions: Array<{
    id: string;
    title: string;
    description: string;
    value?: unknown;
    score?: number;
  }>;
}

/* -------------------------------------------------------------------------- */
/* Generation Types (NLG / Public Transport)                                  */
/* -------------------------------------------------------------------------- */

export interface GenerateRequest {
  /**
   * Preferred spelling for new frontend code.
   */
  lang_code?: string;

  /**
   * Backward-compatible convenience alias.
   */
  lang?: string;

  frame_type: string;
  frame_payload: Record<string, unknown>;
  options?: Record<string, unknown>;
}

export interface GenerationDebugInfo {
  runtime_path: string;
  construction_id: string;
  renderer_backend: string;
  lang_code: string;
  fallback_used: boolean;
  slot_keys: string[];
  selected_backend?: string;
  attempted_backends?: string[];
  backend_trace?: string[];
  resolved_language?: string;
  [key: string]: unknown;
}

/**
 * Canonical public generation response shape.
 *
 * This mirrors the public HTTP transport contract rather than a frontend-only
 * convenience object.
 */
export interface GenerationResult {
  text: string;
  lang_code: string;
  construction_id: string;
  renderer_backend: string;
  fallback_used: boolean;
  tokens: string[];
  debug_info: GenerationDebugInfo;
  generation_time_ms: number;
}

/* -------------------------------------------------------------------------- */
/* Public API surface                                                         */
/* -------------------------------------------------------------------------- */

export interface ArchitectApi {
  health(): Promise<boolean>;

  listFrameTypes(): Promise<FrameTypeMeta[]>;
  getFrameSchema(frameType: string): Promise<Record<string, unknown>>;

  listLanguages(): Promise<Language[]>;

  listEntities(params?: { search?: string; frame_type?: string }): Promise<Entity[]>;
  getEntity(id: number | string): Promise<Entity>;
  createEntity(data: EntityCreatePayload): Promise<Entity>;
  updateEntity(id: number | string, data: EntityUpdatePayload): Promise<Entity>;
  deleteEntity(id: number | string): Promise<void>;

  processIntent(req: IntentRequest): Promise<IntentResponse>;
  getSuggestions(req: SuggestionRequest): Promise<SuggestionResponse>;

  generate(req: GenerateRequest): Promise<GenerationResult>;
}

/* -------------------------------------------------------------------------- */
/* Implementation                                                             */
/* -------------------------------------------------------------------------- */

function normalizeFrameTypes(raw: unknown): FrameTypeMeta[] {
  if (!Array.isArray(raw)) return [];

  return raw
    .map((item: unknown) => {
      const obj = asObject(item);

      // Preferred shape (target contract)
      if (obj && typeof obj.frame_type === "string") {
        return obj as unknown as FrameTypeMeta;
      }

      // Common fallback shape seen in placeholder registries:
      // { id, label, description, schema_ref, icon? }
      if (obj && typeof obj.id === "string") {
        const id = obj.id;
        const family =
          typeof obj.family === "string"
            ? obj.family
            : id.includes(".")
              ? id.split(".")[0]
              : "frame";

        return {
          frame_type: id,
          family,
          title: typeof obj.label === "string" ? obj.label : id,
          description:
            typeof obj.description === "string" ? obj.description : "",
          status: "implemented",
        } satisfies FrameTypeMeta;
      }

      return null;
    })
    .filter(Boolean) as FrameTypeMeta[];
}

function normalizeLanguages(raw: unknown): Language[] {
  if (!Array.isArray(raw)) return [];

  return raw
    .map((item: unknown) => {
      if (typeof item === "string") {
        return { code: item, name: item, z_id: "" };
      }

      const obj = asObject(item);
      if (obj && typeof obj.code === "string") {
        return {
          code: obj.code,
          name: typeof obj.name === "string" ? obj.name : obj.code,
          z_id: typeof obj.z_id === "string" ? obj.z_id : "",
        } satisfies Language;
      }

      return null;
    })
    .filter(Boolean) as Language[];
}

export const architectApi: ArchitectApi = {
  async health(): Promise<boolean> {
    try {
      // Prefer the newer liveness endpoint; fall back to older /health if present.
      const data = await requestWithFallback<Record<string, unknown>>([
        "/health/live",
        "/health",
      ]);
      return (data?.status ?? "") === "ok";
    } catch {
      return false;
    }
  },

  async listFrameTypes(): Promise<FrameTypeMeta[]> {
    const raw = await request<unknown>("/frames/types");
    return normalizeFrameTypes(raw);
  },

  getFrameSchema(frameType: string): Promise<Record<string, unknown>> {
    const ft = encodeURIComponent(frameType);
    return requestWithFallback<Record<string, unknown>>([
      `/schemas/frames/${ft}`,
      `/frames/schemas/${ft}`,
    ]);
  },

  async listLanguages(): Promise<Language[]> {
    const raw = await request<unknown>("/languages");
    return normalizeLanguages(raw);
  },

  listEntities(params): Promise<Entity[]> {
    const query = new URLSearchParams();
    if (params?.search) query.set("search", params.search);
    if (params?.frame_type) query.set("frame_type", params.frame_type);

    const qs = query.toString();
    return request<Entity[]>(`/entities/${qs ? `?${qs}` : ""}`);
  },

  getEntity(id: number | string): Promise<Entity> {
    return request<Entity>(`/entities/${encodeURIComponent(String(id))}`);
  },

  createEntity(data: EntityCreatePayload): Promise<Entity> {
    return request<Entity>("/entities/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  updateEntity(id: number | string, data: EntityUpdatePayload): Promise<Entity> {
    return request<Entity>(`/entities/${encodeURIComponent(String(id))}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  deleteEntity(id: number | string): Promise<void> {
    return request<void>(`/entities/${encodeURIComponent(String(id))}`, {
      method: "DELETE",
    });
  },

  processIntent(req: IntentRequest): Promise<IntentResponse> {
    return request<IntentResponse>("/ai/intent", {
      method: "POST",
      body: JSON.stringify(req),
    });
  },

  getSuggestions(req: SuggestionRequest): Promise<SuggestionResponse> {
    return request<SuggestionResponse>("/ai/suggest-fields", {
      method: "POST",
      body: JSON.stringify(req),
    });
  },

  async generate(req: GenerateRequest): Promise<GenerationResult> {
    const langCode = resolveGenerateLangCode(req);
    const encodedLangCode = encodeURIComponent(langCode);

    // Preferred path: POST /generate/{lang_code}
    try {
      const normalizedBody = {
        frame_type: req.frame_type,
        ...req.frame_payload,
        ...(req.options ?? {}),
      };

      const raw = await request<unknown>(`/generate/${encodedLangCode}`, {
        method: "POST",
        body: JSON.stringify(normalizedBody),
      });

      return normalizeGenerationResult(raw, {
        requestedLangCode: langCode,
      });
    } catch (e) {
      // Backward-compatible path fallback:
      // POST /generate with language in payload.
      //
      // We still normalize into the canonical public transport shape.
      if (e instanceof ApiError && e.status === 404) {
        const raw = await request<unknown>("/generate", {
          method: "POST",
          body: JSON.stringify({
            frame_type: req.frame_type,
            lang_code: langCode,
            ...req.frame_payload,
            ...(req.options ?? {}),
          }),
        });

        return normalizeGenerationResult(raw, {
          requestedLangCode: langCode,
          compatibilityRuntimePath: "legacy_direct_frame",
        });
      }

      throw e;
    }
  },
};

export { API_BASE_URL };
