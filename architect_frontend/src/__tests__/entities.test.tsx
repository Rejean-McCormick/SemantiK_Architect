// architect_frontend/src/__tests__/entities.test.tsx

import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";

import EntityList from "../components/EntityList";
import EntityDetail from "../components/EntityDetail";
import { architectApi, type Entity } from "../lib/api";

// --- Setup Mocks for Next.js and API ---

// 1. Mock Next.js Router for navigation/redirection logic
const mockPush = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  useSearchParams: () => ({
    get: jest.fn(),
  }),
  usePathname: () => "/",
}));

// 2. Mock the central API calls
jest.mock("../lib/api", () => {
  const actual = jest.requireActual("../lib/api");
  return {
    __esModule: true,
    ...actual,
    architectApi: {
      ...(actual as any).architectApi,
      listEntities: jest.fn(),
      getEntity: jest.fn(),
      updateEntity: jest.fn(),
      deleteEntity: jest.fn(),
      // include anything EntityDetail might touch
      generate: jest.fn(),
      processIntent: jest.fn(),
    },
  };
});

// Helper to access the mock functions
const mockListEntities = architectApi.listEntities as jest.Mock;
const mockGetEntity = architectApi.getEntity as jest.Mock;
const mockUpdateEntity = architectApi.updateEntity as jest.Mock;

const MOCK_ENTITIES: Entity[] = [
  {
    id: 42,
    name: "Douglas Adams",
    frame_type: "entity.person",
    lang: "en",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    short_description: "English writer and humorist.",
  } as Entity,
  {
    id: 64,
    name: "Berlin",
    frame_type: "entity.place.city",
    lang: "de",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    short_description: "Capital of Germany.",
  } as Entity,
];

// --- EntityList Tests ---

describe("EntityList (Smart Component)", () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  test("fetches and renders all entities on mount", async () => {
    mockListEntities.mockResolvedValueOnce(MOCK_ENTITIES);

    render(<EntityList />);

    expect(screen.getByText(/Loading library/i)).toBeInTheDocument();

    await waitFor(() => expect(mockListEntities).toHaveBeenCalledTimes(1));

    expect(await screen.findByText("Douglas Adams")).toBeInTheDocument();
    expect(await screen.findByText("Berlin")).toBeInTheDocument();
    expect(screen.queryByText(/Loading library/i)).not.toBeInTheDocument();
  });

  test("navigates to entity detail on click", async () => {
    const user = userEvent.setup();
    mockListEntities.mockResolvedValueOnce(MOCK_ENTITIES);

    render(<EntityList />);

    await waitFor(() => expect(mockListEntities).toHaveBeenCalledTimes(1));

    const targetRow = screen.getByRole("row", { name: /Douglas Adams/i });
    await user.click(targetRow);

    expect(mockPush).toHaveBeenCalledWith("/semantik_architect/entities/42");
  });
});

// --- EntityDetail Tests ---

describe("EntityDetail (Smart Component)", () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  test("fetches and renders details for the given ID", async () => {
    mockGetEntity.mockResolvedValueOnce(MOCK_ENTITIES[0]);

    render(<EntityDetail id="42" />);

    expect(screen.getByText(/Loading entity editor/i)).toBeInTheDocument();

    await waitFor(() => expect(mockGetEntity).toHaveBeenCalledWith("42"));

    expect(
      await screen.findByRole("heading", { name: MOCK_ENTITIES[0].name })
    ).toBeInTheDocument();
    expect(screen.getByText(/English writer and humorist/i)).toBeInTheDocument();
  });

  test("allows saving and mocks the API update", async () => {
    const user = userEvent.setup();
    const updatedEntity = { ...MOCK_ENTITIES[0], name: "Douglas Adams II" };

    mockGetEntity.mockResolvedValueOnce(MOCK_ENTITIES[0]);
    mockUpdateEntity.mockResolvedValueOnce(updatedEntity);

    render(<EntityDetail id="42" />);
    await waitFor(() => expect(mockGetEntity).toHaveBeenCalled());

    const jsonEditor = screen.getByRole("textbox", { name: /Frame Payload/i });
    fireEvent.change(jsonEditor, { target: { value: '{"name": "Douglas Adams II"}' } });

    const saveButton = screen.getByRole("button", { name: /Save Changes/i });
    await user.click(saveButton);

    await waitFor(() => expect(mockUpdateEntity).toHaveBeenCalledTimes(1));

    expect(mockUpdateEntity).toHaveBeenCalledWith("42", {
      frame_payload: { name: "Douglas Adams II" },
    });

    expect(
      await screen.findByRole("heading", { name: /Douglas Adams II/i })
    ).toBeInTheDocument();
  });

  test("renders an error on fetch failure", async () => {
    mockGetEntity.mockRejectedValueOnce(new Error("Network Error"));

    render(<EntityDetail id="999" />);

    await waitFor(() => expect(mockGetEntity).toHaveBeenCalled());

    expect(
      screen.getByText(/Could not load entity\. It may not exist or the backend is down\./i)
    ).toBeInTheDocument();
  });
});
