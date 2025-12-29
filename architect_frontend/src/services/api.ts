// architect_frontend/src/services/api.ts
import { Language } from '../types/language';

// Base URL handling: Uses env var for production, defaults to localhost for dev
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Generic wrapper for fetch requests with error handling
 */
async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  // Ensure endpoint starts with /
  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = `${API_BASE_URL}${path}`;
  
  // Default headers (can be overridden)
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  const config = {
    ...options,
    headers,
  };

  try {
    const response = await fetch(url, config);

    if (!response.ok) {
      // Try to parse error message from JSON, fallback to status text
      let errorMessage = `API Error ${response.status}: ${response.statusText}`;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
            errorMessage = typeof errorData.detail === 'string' 
                ? errorData.detail 
                : JSON.stringify(errorData.detail);
        }
      } catch (e) {
        // Response wasn't JSON, ignore
      }
      throw new Error(errorMessage);
    }

    return await response.json();
  } catch (error) {
    console.error(`API Request Failed: ${endpoint}`, error);
    throw error;
  }
}

// ============================================================================
// 1. LANGUAGE SERVICES
// ============================================================================

/**
 * Fetches the complete list of supported languages (RGL + Factory).
 */
export async function getLanguages(): Promise<Language[]> {
  return request<Language[]>('/api/v1/languages');
}

// ============================================================================
// 2. TOOLING & MAINTENANCE SERVICES
// ============================================================================

export interface ToolResponse {
    success: boolean;
    output: string;
    error?: string;
}

/**
 * Triggers a backend maintenance script via the Secure Router.
 * @param toolId The ID registered in the backend Allowlist (e.g., 'audit_languages')
 * @param args Optional dictionary of arguments (e.g. { lang_code: 'fra' })
 */
export async function runTool(toolId: string, args?: Record<string, any>): Promise<ToolResponse> {
    return request<ToolResponse>('/api/v1/tools/run', {
        method: 'POST',
        body: JSON.stringify({ 
            tool_id: toolId,
            ...args 
        })
    });
}

// ============================================================================
// 3. SYSTEM HEALTH SERVICES
// ============================================================================

export interface SystemHealth {
    broker: "up" | "down";
    storage: "up" | "down";
    engine: "up" | "down";
}

/**
 * Basic liveness check.
 */
export async function getHealth(): Promise<{ status: string }> {
  return request<{ status: string }>('/api/v1/health');
}

/**
 * Deep diagnostic check for the Dev Dashboard.
 */
export async function getDetailedHealth(): Promise<SystemHealth> {
    return request<SystemHealth>('/api/v1/health/ready');
}

// ============================================================================
// 4. GENERATION SERVICES
// ============================================================================

export interface GenerationRequest {
    frame_slug: string; // e.g., "bio"
    language: string;   // e.g., "en"
    parameters: Record<string, any>;
}

export interface GenerationResponse {
    id: string;
    text: string;
    // ... other fields
}

/**
 * Sends a generation request to the API.
 * Used by the Smoke Test Bench.
 */
export async function generateText(payload: GenerationRequest): Promise<GenerationResponse> {
   return request<GenerationResponse>('/api/v1/generate', {
     method: 'POST',
     body: JSON.stringify(payload),
   });
}