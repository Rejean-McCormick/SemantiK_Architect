// architect_frontend/src/services/api.ts

/**
 * ⛔ DEPRECATED: This module is being replaced by the canonical client in `src/lib/api.ts`.
 * * This file is now a Compatibility Adapter. 
 * - It shares the same Base URL configuration as the main app.
 * - It delegates standard calls to `architectApi`.
 * - It preserves legacy function signatures for tools/dashboards not yet refactored.
 * * @deprecated Import `architectApi` from '@/lib/api' instead.
 */

import { architectApi, API_BASE_URL } from '../lib/api';
import type { Language } from '../lib/api'; 

// Re-export shared types to prevent breakage in components importing from here
export type { Language };

/**
 * Legacy request helper (Internal Use Only)
 * Uses the Canonical API_BASE_URL to ensure no "Split-Brain" config.
 */
async function legacyRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  try {
    const response = await fetch(url, { ...options, headers });

    if (!response.ok) {
      let errorMessage = `API Error ${response.status}: ${response.statusText}`;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
            errorMessage = typeof errorData.detail === 'string' 
                ? errorData.detail 
                : JSON.stringify(errorData.detail);
        }
      } catch { /* ignore non-json errors */ }
      throw new Error(errorMessage);
    }

    return await response.json();
  } catch (error) {
    console.error(`Legacy API Request Failed: ${endpoint}`, error);
    throw error;
  }
}

// ============================================================================
// 1. LANGUAGE SERVICES
// ============================================================================

/**
 * @deprecated Use `architectApi.listLanguages()`
 */
export async function getLanguages(): Promise<Language[]> {
  // Delegate to the canonical client
  return architectApi.listLanguages();
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
 * Triggers a backend maintenance script.
 * Maintained for the Dev Dashboard.
 */
export async function runTool(toolId: string, args?: Record<string, any>): Promise<ToolResponse> {
    // Note: 'tools' router is mounted at /api/v1/tools
    return legacyRequest<ToolResponse>('/tools/run', {
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
 * @deprecated Use `architectApi.health()`
 */
export async function getHealth(): Promise<{ status: string }> {
  const isUp = await architectApi.health();
  return { status: isUp ? "ok" : "error" };
}

/**
 * Deep diagnostic check for the Dev Dashboard.
 */
export async function getDetailedHealth(): Promise<SystemHealth> {
    // Note: Assuming health router has a /ready endpoint mounted under /api/v1
    return legacyRequest<SystemHealth>('/health/ready');
}

// ============================================================================
// 4. GENERATION SERVICES
// ============================================================================

export interface GenerationRequest {
    frame_slug: string; 
    language: string;   
    parameters: Record<string, any>;
}

export interface GenerationResponse {
    id: string;
    text: string;
}

/**
 * Sends a generation request.
 * Adapts the old 'Smoke Test' payload to the new `architectApi` contract.
 */
export async function generateText(payload: GenerationRequest): Promise<GenerationResponse> {
   // Map Legacy Payload -> New Canonical Payload
   const result = await architectApi.generate({
       lang: payload.language,
       frame_type: payload.frame_slug,
       frame_payload: payload.parameters
   });

   return {
       id: "gen_" + Date.now(), // Mock ID if backend doesn't return one in the new simple schema
       text: result.text
   };
}