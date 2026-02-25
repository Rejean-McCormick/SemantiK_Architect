// src/components/ui/select.tsx
import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Lightweight, dependency-free Select that mimics the shadcn/radix component API:
 *
 * <Select value={v} onValueChange={setV}>
 *   <SelectTrigger className="..." >
 *     <SelectValue placeholder="Pick one" />
 *   </SelectTrigger>
 *   <SelectContent>
 *     <SelectItem value="a">A</SelectItem>
 *     <SelectItem value="b">B</SelectItem>
 *   </SelectContent>
 * </Select>
 *
 * Internally renders a native <select>.
 */

type SelectContextValue = {
  value: string;
  setValue: (v: string) => void;
  disabled?: boolean;
};

const SelectContext = React.createContext<SelectContextValue | null>(null);

export type SelectProps = {
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  disabled?: boolean;
  name?: string;
  children?: React.ReactNode;
  className?: string;
};

function isElementWithDisplayName(
  node: React.ReactNode,
  displayName: string,
): node is React.ReactElement {
  return (
    React.isValidElement(node) &&
    typeof node.type !== "string" &&
    (node.type as any).displayName === displayName
  );
}

export function Select({
  value: controlledValue,
  defaultValue,
  onValueChange,
  disabled,
  name,
  children,
  className,
}: SelectProps) {
  // Parse children for Trigger/Content/Items/Value placeholder
  const nodes = React.Children.toArray(children);

  const triggerEl = nodes.find((n) => isElementWithDisplayName(n, "SelectTrigger"));
  const contentEl = nodes.find((n) => isElementWithDisplayName(n, "SelectContent"));

  let placeholder: string | undefined;
  if (triggerEl) {
    const triggerKids = React.Children.toArray((triggerEl as any).props?.children);
    const valueEl = triggerKids.find((n) => isElementWithDisplayName(n, "SelectValue"));
    placeholder = (valueEl as any)?.props?.placeholder;
  }

  const itemNodes = React.Children.toArray((contentEl as any)?.props?.children ?? []).filter(
    (n) => isElementWithDisplayName(n, "SelectItem"),
  ) as React.ReactElement[];

  const options = itemNodes.map((el) => ({
    value: String(el.props.value),
    label: el.props.children as React.ReactNode,
    disabled: Boolean(el.props.disabled),
  }));

  const initial =
    controlledValue ??
    defaultValue ??
    (options.length > 0 ? options[0].value : "");

  const [uncontrolledValue, setUncontrolledValue] = React.useState<string>(initial);

  // Keep uncontrolled in sync if defaultValue changes (rare, but safe)
  React.useEffect(() => {
    if (controlledValue === undefined && defaultValue !== undefined) {
      setUncontrolledValue(defaultValue);
    }
  }, [controlledValue, defaultValue]);

  const currentValue = controlledValue !== undefined ? controlledValue : uncontrolledValue;

  const setValue = React.useCallback(
    (v: string) => {
      if (controlledValue === undefined) setUncontrolledValue(v);
      onValueChange?.(v);
    },
    [controlledValue, onValueChange],
  );

  const triggerClassName = cn(
    // Tailwind-ish defaults similar to other ui components in this repo
    "flex h-10 w-full appearance-none items-center rounded-md border border-slate-200 bg-white px-3 pr-10 text-sm text-slate-950 shadow-sm",
    "focus:outline-none focus:ring-2 focus:ring-slate-950 focus:ring-offset-2",
    "disabled:cursor-not-allowed disabled:opacity-50",
    "dark:border-slate-800 dark:bg-slate-950 dark:text-slate-50 dark:focus:ring-slate-300",
    (triggerEl as any)?.props?.className,
    className,
  );

  return (
    <SelectContext.Provider value={{ value: currentValue, setValue, disabled }}>
      <div className="relative w-full">
        <select
          name={name}
          disabled={disabled}
          className={triggerClassName}
          value={currentValue}
          onChange={(e) => setValue(e.target.value)}
        >
          {placeholder ? (
            <option value="" disabled hidden>
              {placeholder}
            </option>
          ) : null}

          {options.map((opt) => (
            <option key={opt.value} value={opt.value} disabled={opt.disabled}>
              {opt.label as any}
            </option>
          ))}
        </select>

        {/* dropdown chevron */}
        <svg
          aria-hidden="true"
          viewBox="0 0 20 20"
          className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 opacity-60"
        >
          <path
            fill="currentColor"
            d="M5.3 7.3a1 1 0 0 1 1.4 0L10 10.6l3.3-3.3a1 1 0 1 1 1.4 1.4l-4 4a1 1 0 0 1-1.4 0l-4-4a1 1 0 0 1 0-1.4z"
          />
        </svg>
      </div>
    </SelectContext.Provider>
  );
}

// Marker components (parsed by <Select/>)
export function SelectTrigger(_props: { className?: string; children?: React.ReactNode }) {
  return null;
}
SelectTrigger.displayName = "SelectTrigger";

export function SelectValue(_props: { placeholder?: string }) {
  return null;
}
SelectValue.displayName = "SelectValue";

export function SelectContent(_props: { children?: React.ReactNode }) {
  return null;
}
SelectContent.displayName = "SelectContent";

export function SelectItem(_props: { value: string; disabled?: boolean; children?: React.ReactNode }) {
  return null;
}
SelectItem.displayName = "SelectItem";
