// architect_frontend/src/__tests__/aiPanel.test.tsx

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";

import AIPanel from "../components/AIPanel";
import { architectApi } from "../lib/api";

// Mock the API module to intercept calls
jest.mock("../lib/api", () => ({
  architectApi: {
    processIntent: jest.fn(),
  },
}));

const mockProcessIntent = architectApi.processIntent as jest.Mock;

const baseProps = {
  entityType: "bio",
  entityId: "person",
  currentValues: { name: "Marie Curie" },
  onApplySuggestion: jest.fn(),
};

describe("AIPanel", () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it("renders basic AI controls", () => {
    render(<AIPanel {...baseProps} />);

    expect(screen.getByText(/Architect AI/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Suggest/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Explain/i })).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Type your instructions/i)).toBeInTheDocument();
  });

  it("sends a request and handles suggestions", async () => {
    mockProcessIntent.mockResolvedValueOnce({
      intent_label: "suggest_fields",
      assistant_messages: [{ role: "assistant", content: "I suggest setting the profession." }],
      patches: [{ path: "profession", value: "physicist", op: "add" }],
    });

    const onApplySuggestion = jest.fn();
    render(<AIPanel {...baseProps} onApplySuggestion={onApplySuggestion} />);

    // IMPORTANT: quick prompt buttons only fill the textarea; they do not auto-submit.
    fireEvent.click(screen.getByRole("button", { name: /Suggest/i }));
    fireEvent.click(screen.getByRole("button", { name: /^Send$/i }));

    await waitFor(() => expect(mockProcessIntent).toHaveBeenCalledTimes(1));

    expect(mockProcessIntent).toHaveBeenCalledWith(
      expect.objectContaining({
        message: expect.stringContaining("missing or underspecified"),
        context_frame: {
          frame_type: "bio",
          payload: { name: "Marie Curie" },
        },
      })
    );

    expect(await screen.findByText(/I suggest setting the profession/i)).toBeInTheDocument();
    expect(screen.getByText(/Suggestion Available/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Apply Changes/i }));

    expect(onApplySuggestion).toHaveBeenCalledWith({ profession: "physicist" });
  });
});
