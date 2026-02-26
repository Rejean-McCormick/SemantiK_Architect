// architect_frontend/src/components/CreateWorkspaceGrid.tsx
"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { architectApi, getLabelText } from "@/lib/api";
import type { FrameTypeMeta } from "@/lib/api";

type Props = {
  frameTypes: FrameTypeMeta[];
  /**
   * Preferred: ISO-639-1 (e.g. "en", "fr").
   * We also tolerate common ISO-639-2/3 inputs (e.g. "eng") and normalize.
   */
  defaultLanguage?: string;
};

const ISO3_TO_ISO2: Record<string, string> = {
  eng: "en",
  fra: "fr",
  fre: "fr",
  deu: "de",
  ger: "de",
  spa: "es",
  ita: "it",
  nld: "nl",
  dut: "nl",
  por: "pt",
  rus: "ru",
  swe: "sv",
  zho: "zh",
  chi: "zh",
  jpn: "ja",
  ara: "ar",
  hin: "hi",
};

function normalizeLangCode(code: string | undefined, fallback = "en") {
  const c = (code || "").trim().toLowerCase();
  if (!c) return fallback;
  if (c.length === 2) return c;
  if (ISO3_TO_ISO2[c]) return ISO3_TO_ISO2[c];
  return c.slice(0, 2);
}

export default function CreateWorkspaceGrid({
  frameTypes,
  defaultLanguage = "en",
}: Props) {
  const router = useRouter();
  const [isCreating, setIsCreating] = useState<string | null>(null);

  const handleQuickCreate = async (frameSlug: string) => {
    try {
      setIsCreating(frameSlug);

      const lang = normalizeLangCode(defaultLanguage, "en");

      // 1. Create a new entity based on the selected frame template
      const entity = await architectApi.createEntity({
        name: `Untitled ${frameSlug}`, // Temporary name
        frame_type: frameSlug, // Use the slug as the frame_type
        frame_payload: {}, // Empty payload to start
        lang, // Use selected/default language
      });

      // 2. Redirect to the simplified editor path
      router.push(`/editor/entities/${entity.id}`);
    } catch (err) {
      console.error("Failed to create entity", err);
      alert("Failed to initialize workspace. Check backend connection.");
    } finally {
      setIsCreating(null);
    }
  };

  return (
    <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 mb-16">
      {frameTypes.map((frame) => (
        <button
          key={frame.frame_type}
          onClick={() => handleQuickCreate(frame.frame_type)}
          disabled={isCreating !== null}
          className="group flex flex-col justify-between rounded-xl border border-slate-800 bg-slate-900/40 p-4 text-left transition hover:border-sky-500 hover:bg-slate-900 disabled:opacity-50 disabled:cursor-wait"
        >
          <div className="space-y-2">
            <div className="flex items-start justify-between gap-3">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h2 className="text-sm font-medium tracking-tight text-slate-100">
                    {getLabelText(frame.title) || frame.frame_type}
                  </h2>
                </div>
                <p className="text-xs text-slate-400 line-clamp-3">
                  {getLabelText(frame.description) || "No description available."}
                </p>
              </div>
              <span className="text-[11px] font-medium uppercase tracking-[0.2em] text-slate-600 group-hover:text-sky-400">
                {isCreating === frame.frame_type ? "Creating..." : "New"}
              </span>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-slate-800/80 px-2 py-0.5 text-[10px] font-mono uppercase tracking-wide text-slate-300">
              {frame.family}
            </span>
            <span className="rounded-full bg-slate-800/80 px-2 py-0.5 text-[10px] font-mono uppercase tracking-wide text-slate-300">
              lang: {normalizeLangCode(defaultLanguage, "en")}
            </span>
          </div>
        </button>
      ))}
    </section>
  );
}