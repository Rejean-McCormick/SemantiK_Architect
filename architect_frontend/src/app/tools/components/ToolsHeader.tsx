// architect_frontend/src/app/tools/components/ToolsHeader.tsx
"use client";

import React, { memo } from "react";
import { Terminal } from "lucide-react";

export type ToolsHeaderProps = {
  version?: string;
  generatedOn?: string;
};

export const ToolsHeader = memo(function ToolsHeader({ version, generatedOn }: ToolsHeaderProps) {
  return (
    <div className="mb-2 flex items-end justify-between gap-4">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Tools</h1>
        <p className="text-sm text-muted-foreground">
          Browse installed tools and run them with sample arguments.
        </p>
      </div>

      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Terminal className="h-4 w-4" />
        {version ? <span className="hidden sm:inline">inventory v{version}</span> : null}
        {generatedOn ? <span className="hidden md:inline">• {generatedOn}</span> : null}
      </div>
    </div>
  );
});
