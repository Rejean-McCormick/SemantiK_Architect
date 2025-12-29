// src/lib/test-payloads.ts

export type TestScenario = {
  id: string;
  label: string;
  description: string;
  endpoint: string;
  headers: Record<string, string>;
  payload: any;
};

export const SMOKE_TESTS: TestScenario[] = [
  {
    id: "bio-douglas-adams",
    label: "Bio: Douglas Adams (Simple)",
    description: "Standard biographical frame using strict schema.",
    endpoint: "http://localhost:8000/api/v1/generate/WikiEng",
    headers: {
      "Content-Type": "application/json",
      "X-Session-ID": "dev-session-001"
    },
    payload: {
      frame_type: "bio",
      context_id: "Q42",
      gender: "m",
      subject: {
        name: "Douglas Adams",
        qid: "Q42",
        type: "Person"
      },
      attributes: { born: "1952" }
    }
  },
  {
    id: "bio-pronominalization",
    label: "Bio: Pronominalization Check",
    description: "Sends the SAME context ID to trigger 'He' instead of the name.",
    endpoint: "http://localhost:8000/api/v1/generate/WikiEng",
    headers: {
      "Content-Type": "application/json",
      "X-Session-ID": "dev-session-001"
    },
    payload: {
      frame_type: "bio",
      context_id: "Q42",
      gender: "m",
      subject: {
        name: "Douglas Adams",
        qid: "Q42",
        type: "Person"
      },
      attributes: { occupation: "Writer" }
    }
  },
  {
    id: "ninai-protocol",
    label: "Protocol: Ninai (UniversalNode)",
    description: "Tests the recursive Ninai adapter path (Prototype Mode).",
    endpoint: "http://localhost:8000/api/v1/generate/WikiEng",
    headers: {
      "Content-Type": "application/json",
      "X-Session-ID": "dev-session-ninai"
    },
    payload: {
      function: "ninai.constructors.Statement",
      args: [
        { function: "ninai.types.Bio" },
        { 
          function: "ninai.constructors.List", 
          args: ["physicist", "chemist"] 
        },
        { function: "ninai.constructors.Entity", args: ["Q42"] }
      ]
    }
  }
];