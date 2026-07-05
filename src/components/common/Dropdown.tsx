/**
 * Dropdown
 * ========
 * Accessible dropdown menu with option grouping, search filtering,
 * and full keyboard navigation.
 *
 * Features:
 * - Click to toggle
 * - Keyboard navigation (Arrow up/down, Enter, Escape)
 * - Search filter (optional)
 * - Option groups with group labels
 * - Click outside to close
 * - Animated open/close
 *
 * Design: Dark panel (slate-900), border, hover highlight (amber tint).
 */

import React, {
  useState,
  useRef,
  useEffect,
  useCallback,
  type KeyboardEvent,
} from "react";

// ---------------------------------------------------------------------------
// Icons
// ---------------------------------------------------------------------------

const ChevronDown: React.FC<{ className?: string }> = ({ className = "" }) => (
  <svg className={className} viewBox="0 0 20 20" fill="currentColor">
    <path
      fillRule="evenodd"
      d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
      clipRule="evenodd"
    />
  </svg>
);

const SearchIcon: React.FC<{ className?: string }> = ({ className = "" }) => (
  <svg className={className} viewBox="0 0 20 20" fill="currentColor">
    <path
      fillRule="evenodd"
      d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z"
      clipRule="evenodd"
    />
  </svg>
);

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** A single dropdown option */
export interface DropdownOption {
  /** Unique identifier */
  value: string;
  /** Display label */
  label: string;
  /** Optional description shown below label */
  description?: string;
  /** Whether the option is disabled */
  disabled?: boolean;
}

/** A labeled group of options */
export interface DropdownGroup {
  /** Group label */
  label: string;
  /** Options in this group */
  options: DropdownOption[];
}

interface DropdownProps {
  /** Options (flat list, or grouped) */
  items: DropdownOption[] | DropdownGroup[];
  /** Trigger button text */
  triggerLabel: string;
  /** Currently selected value */
  value?: string;
  /** Change handler */
  onChange: (value: string) => void;
  /** Placeholder when no value selected */
  placeholder?: string;
  /** Enable search filter */
  searchable?: boolean;
  /** Disabled state */
  disabled?: boolean;
  /** Optional className for the trigger */
  className?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isGrouped(
  items: DropdownOption[] | DropdownGroup[]
): items is DropdownGroup[] {
  return items.length > 0 && "options" in items[0];
}

function flattenOptions(
  items: DropdownOption[] | DropdownGroup[]
): DropdownOption[] {
  if (isGrouped(items)) {
    return items.flatMap((g) => g.options);
  }
  return items;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Dropdown select component.
 *
 * @example
 * ```tsx
 * <Dropdown
 *   items={[{value: "1", label: "Option 1"}]}
 *   triggerLabel="Select..."
 *   onChange={(v) => console.log(v)}
 * />
 * ```
 */
const Dropdown: React.FC<DropdownProps> = ({
  items,
  triggerLabel,
  value,
  onChange,
  placeholder = "Select...",
  searchable = false,
  disabled = false,
  className = "",
}) => {
  const [open, setOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  const flat = flattenOptions(items);

  // Find selected label
  const selectedOption = flat.find((o) => o.value === value);
  const displayText = selectedOption?.label || placeholder;

  // Filter options by search
  const filteredItems = (() => {
    if (!searchQuery.trim()) return items;

    const query = searchQuery.toLowerCase();
    if (isGrouped(items)) {
      return items
        .map((group) => ({
          ...group,
          options: group.options.filter(
            (o) =>
              o.label.toLowerCase().includes(query) ||
              (o.description && o.description.toLowerCase().includes(query))
          ),
        }))
        .filter((group) => group.options.length > 0);
    }
    return items.filter(
      (o) =>
        o.label.toLowerCase().includes(query) ||
        (o.description && o.description.toLowerCase().includes(query))
    );
  })();

  const filteredFlat = flattenOptions(filteredItems);

  // ---- Close on outside click ----
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  // ---- Focus search input on open ----
  useEffect(() => {
    if (open && searchable && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [open, searchable]);

  // ---- Reset state on close ----
  const close = useCallback(() => {
    setOpen(false);
    setSearchQuery("");
    setActiveIndex(-1);
  }, []);

  // ---- Keyboard navigation ----
  const handleKeyDown = (e: KeyboardEvent) => {
    if (!open) {
      if (e.key === "Enter" || e.key === " " || e.key === "ArrowDown") {
        e.preventDefault();
        setOpen(true);
      }
      return;
    }

    switch (e.key) {
      case "Escape":
        e.preventDefault();
        close();
        break;
      case "ArrowDown":
        e.preventDefault();
        setActiveIndex((prev) =>
          prev < filteredFlat.length - 1 ? prev + 1 : 0
        );
        break;
      case "ArrowUp":
        e.preventDefault();
        setActiveIndex((prev) =>
          prev > 0 ? prev - 1 : filteredFlat.length - 1
        );
        break;
      case "Enter":
        e.preventDefault();
        if (activeIndex >= 0 && activeIndex < filteredFlat.length) {
          const option = filteredFlat[activeIndex];
          if (!option.disabled) {
            onChange(option.value);
            close();
          }
        }
        break;
    }
  };

  // Scroll active option into view
  useEffect(() => {
    if (activeIndex < 0 || !listRef.current) return;
    const item = listRef.current.children[activeIndex] as HTMLElement;
    item?.scrollIntoView({ block: "nearest" });
  }, [activeIndex]);

  // Render single option
  const renderOption = (option: DropdownOption, index: number) => {
    const isSelected = option.value === value;
    const isActive = index === activeIndex;

    return (
      <li key={option.value}>
        <button
          type="button"
          disabled={option.disabled}
          onClick={() => {
            if (!option.disabled) {
              onChange(option.value);
              close();
            }
          }}
          onMouseEnter={() => setActiveIndex(index)}
          className={`flex w-full flex-col items-start rounded-md px-3 py-2 text-left transition-colors ${
            isActive
              ? "bg-amber-500/10 text-amber-400"
              : "text-slate-300 hover:bg-slate-800"
          } ${
            option.disabled
              ? "cursor-not-allowed opacity-40"
              : "cursor-pointer"
          }`}
          role="option"
          aria-selected={isSelected}
        >
          <span className="text-xs font-medium">{option.label}</span>
          {option.description && (
            <span className="mt-0.5 text-[10px] text-slate-500">
              {option.description}
            </span>
          )}
        </button>
      </li>
    );
  };

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      {/* ---- Trigger ---- */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => !disabled && setOpen((prev) => !prev)}
        onKeyDown={handleKeyDown}
        className={`flex w-full items-center justify-between gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3.5 py-2 text-left text-xs text-slate-300 transition-colors hover:border-slate-600 ${
          open ? "border-amber-500/50 ring-1 ring-amber-500/20" : ""
        } ${disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer"}`}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className={value ? "text-slate-200" : "text-slate-500"}>
          {displayText}
        </span>
        <ChevronDown
          className={`h-4 w-4 text-slate-500 transition-transform duration-200 ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>

      {/* ---- Dropdown Panel ---- */}
      {open && (
        <div className="absolute left-0 z-50 mt-1.5 w-full min-w-[200px] overflow-hidden rounded-xl border border-slate-700 bg-slate-900 shadow-2xl shadow-black/50 animate-in fade-in zoom-in-95 duration-150">
          {/* Search Input */}
          {searchable && (
            <div className="border-b border-slate-800 px-3 py-2">
              <div className="relative">
                <SearchIcon className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-600" />
                <input
                  ref={searchInputRef}
                  type="text"
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setActiveIndex(-1);
                  }}
                  placeholder="Filter..."
                  className="w-full rounded-md border border-slate-700 bg-slate-950 py-1.5 pl-8 pr-3 text-[11px] text-slate-200 placeholder:text-slate-600 focus:border-amber-500/50 focus:outline-none"
                />
              </div>
            </div>
          )}

          {/* Options List */}
          <ul
            ref={listRef}
            role="listbox"
            className="max-h-56 overflow-y-auto p-1.5"
          >
            {filteredItems.length === 0 ? (
              <li className="px-3 py-4 text-center text-[11px] text-slate-600">
                No results
              </li>
            ) : isGrouped(filteredItems) ? (
              filteredItems.map((group) => (
                <li key={group.label}>
                  <span className="block px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-600">
                    {group.label}
                  </span>
                  <ul>
                    {group.options.map((option) =>
                      renderOption(option, flat.indexOf(option))
                    )}
                  </ul>
                </li>
              ))
            ) : (
              (filteredItems as DropdownOption[]).map((option) =>
                renderOption(option, flat.indexOf(option))
              )
            )}
          </ul>
        </div>
      )}
    </div>
  );
};

export default Dropdown;
