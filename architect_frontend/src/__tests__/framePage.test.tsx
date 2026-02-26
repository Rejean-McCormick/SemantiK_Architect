// architect_frontend/src/__tests__/framePage.test.tsx

import "@testing-library/jest-dom";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

import EditorPage from "@/app/editor/page";
import { architectApi } from "@/lib/api";

// Mock de l'API utilisée par EditorPage
jest.mock("@/lib/api", () => ({
  __esModule: true,
  architectApi: {
    listLanguages: jest.fn(),
    generate: jest.fn(),
  },
}));

describe("EditorPage", () => {
  const mockListLanguages = architectApi.listLanguages as unknown as jest.Mock;
  const mockGenerate = architectApi.generate as unknown as jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders the editor shell and loads languages", async () => {
    mockListLanguages.mockResolvedValueOnce([{ code: "en", name: "English" }]);

    render(<EditorPage />);

    // UI de base
    expect(screen.getByText(/Frame Input/i)).toBeInTheDocument();
    expect(screen.getByText(/Output/i)).toBeInTheDocument();

    // Langues chargées
    await waitFor(() => expect(mockListLanguages).toHaveBeenCalledTimes(1));
    expect(
      screen.getByRole("option", { name: /English \(en\)/i })
    ).toBeInTheDocument();
  });

  it("runs generation and displays the result", async () => {
    mockListLanguages.mockResolvedValueOnce([{ code: "en", name: "English" }]);
    mockGenerate.mockResolvedValueOnce({
      surface_text: "Generated biography text",
    });

    render(<EditorPage />);

    await waitFor(() => expect(mockListLanguages).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: /Realize Text/i }));

    await waitFor(() => expect(mockGenerate).toHaveBeenCalledTimes(1));
    expect(mockGenerate).toHaveBeenCalledWith(
      expect.objectContaining({
        lang: "en",
        frame_type: "bio",
        frame_payload: expect.objectContaining({
          name: "Marie Curie",
        }),
      })
    );

    expect(await screen.findByText("Generated biography text")).toBeInTheDocument();
  });

  it("shows an error when generation fails", async () => {
    mockListLanguages.mockResolvedValueOnce([{ code: "en", name: "English" }]);
    mockGenerate.mockRejectedValueOnce(new Error("Generation failed"));

    render(<EditorPage />);

    await waitFor(() => expect(mockListLanguages).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: /Realize Text/i }));

    expect(await screen.findByText(/Error:\s*Generation failed/i)).toBeInTheDocument();
  });
});