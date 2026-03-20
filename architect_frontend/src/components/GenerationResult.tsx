// architect_frontend/src/components/GenerationResult.tsx

import type { FC } from "react";
import type { GenerationResult as GenerationResultData } from "@/lib/api";

type GenerationResultProps = {
  result: GenerationResultData | null;
  title?: string;
  className?: string;
};

const metaRowStyle: React.CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: "0.5rem",
  marginBottom: "0.75rem",
};

const metaPillStyle: React.CSSProperties = {
  display: "inline-block",
  padding: "0.25rem 0.5rem",
  borderRadius: "999px",
  background: "#f5f5f5",
  boxShadow: "0 0 0 1px #ddd",
  fontSize: "0.875rem",
};

const labelStyle: React.CSSProperties = {
  fontWeight: 600,
};

const GenerationResult: FC<GenerationResultProps> = ({
  result,
  title = "Generated text",
  className,
}) => {
  if (!result) return null;

  return (
    <section
      className={className}
      style={{
        marginTop: "1.5rem",
        padding: "1rem",
        background: "#fff",
        borderRadius: "4px",
        boxShadow: "0 0 0 1px #ddd",
        maxWidth: "640px",
      }}
    >
      <h2 style={{ marginTop: 0 }}>{title}</h2>

      <div style={metaRowStyle}>
        <span style={metaPillStyle}>
          <span style={labelStyle}>Lang:</span> {result.lang_code}
        </span>
        <span style={metaPillStyle}>
          <span style={labelStyle}>Construction:</span> {result.construction_id}
        </span>
        <span style={metaPillStyle}>
          <span style={labelStyle}>Backend:</span> {result.renderer_backend}
        </span>
        <span style={metaPillStyle}>
          <span style={labelStyle}>Fallback:</span>{" "}
          {result.fallback_used ? "yes" : "no"}
        </span>
        <span style={metaPillStyle}>
          <span style={labelStyle}>Time:</span>{" "}
          {result.generation_time_ms.toFixed(1)} ms
        </span>
      </div>

      <p style={{ whiteSpace: "pre-wrap", lineHeight: 1.5, marginBottom: "0.75rem" }}>
        {result.text}
      </p>

      <details>
        <summary style={{ cursor: "pointer" }}>Details</summary>

        <div style={{ marginTop: "0.75rem" }}>
          <div style={{ marginBottom: "0.5rem" }}>
            <span style={labelStyle}>Tokens:</span>{" "}
            {result.tokens.length > 0 ? result.tokens.join(" | ") : "—"}
          </div>

          <div>
            <span style={labelStyle}>Debug info:</span>
            <pre
              style={{
                marginTop: "0.5rem",
                padding: "0.75rem",
                background: "#f8f8f8",
                borderRadius: "4px",
                boxShadow: "0 0 0 1px #e0e0e0",
                overflowX: "auto",
                fontSize: "0.875rem",
                lineHeight: 1.4,
              }}
            >
              {JSON.stringify(result.debug_info, null, 2)}
            </pre>
          </div>
        </div>
      </details>
    </section>
  );
};

export default GenerationResult;