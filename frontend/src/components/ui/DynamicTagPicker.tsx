"use client";

import React, { useState, useRef, useEffect, useId } from "react";

export interface StandardTagOption {
  id: string;
  label: string;
  desc?: string;
}

export interface DynamicTagPickerProps {
  id?: string;
  label?: string;
  description?: string;
  standardOptions: StandardTagOption[];
  selected: string[];
  onChange: (selected: string[]) => void;
  customPlaceholder?: string;
  useCustomNamespace?: boolean;
  categoryName?: string;
  className?: string;
}

export function DynamicTagPicker({
  id: customId,
  label,
  description,
  standardOptions,
  selected,
  onChange,
  customPlaceholder = "e.g. SEC Digital Asset VASP",
  useCustomNamespace = false,
  categoryName = "tag",
  className = "",
}: DynamicTagPickerProps) {
  const generatedId = useId();
  const componentId = customId || generatedId;

  // Track user-added custom items internally so they persist in the list even if deselected
  const [customOptions, setCustomOptions] = useState<string[]>(() => {
    // Extract any existing selected items that are not in standardOptions
    const standardIds = new Set(standardOptions.map((o) => o.id.toLowerCase()));
    return selected.filter((item) => {
      const clean = item.replace(/^CUSTOM:\s*/i, "").trim().toLowerCase();
      return !standardIds.has(clean) && !standardIds.has(item.toLowerCase());
    });
  });

  const [isAdding, setIsAdding] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [inputError, setInputError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isAdding) {
      inputRef.current?.focus();
    }
  }, [isAdding]);

  function isOptionSelected(optionId: string): boolean {
    return (
      selected.includes(optionId) ||
      (useCustomNamespace && selected.includes(`CUSTOM: ${optionId}`))
    );
  }

  function toggleStandard(optionId: string) {
    if (selected.includes(optionId)) {
      onChange(selected.filter((item) => item !== optionId));
    } else {
      onChange([...selected, optionId]);
    }
  }

  function handleAddCustom() {
    const raw = inputValue.trim();
    if (!raw) {
      setIsAdding(false);
      setInputError(null);
      return;
    }

    if (raw.length > 100) {
      setInputError("Custom item name must be 100 characters or fewer.");
      return;
    }

    const cleanInput = raw.replace(/^CUSTOM:\s*/i, "").trim();
    const normalizedInput = cleanInput.toLowerCase();

    // Check duplicate against standard options
    const existsInStandard = standardOptions.some(
      (opt) =>
        opt.id.toLowerCase() === normalizedInput ||
        opt.label.toLowerCase() === normalizedInput
    );

    // Check duplicate against existing custom options
    const existsInCustom = customOptions.some(
      (opt) => opt.replace(/^CUSTOM:\s*/i, "").trim().toLowerCase() === normalizedInput
    );

    if (existsInStandard || existsInCustom) {
      setInputError(`"${cleanInput}" is already an available option.`);
      return;
    }

    const valueToStore = useCustomNamespace ? `CUSTOM: ${cleanInput}` : cleanInput;

    setCustomOptions((prev) => [...prev, valueToStore]);
    if (!selected.includes(valueToStore)) {
      onChange([...selected, valueToStore]);
    }

    setInputValue("");
    setInputError(null);
    setIsAdding(false);
  }

  function removeCustomTag(tagToRemove: string, e?: React.MouseEvent) {
    e?.stopPropagation();
    setCustomOptions((prev) => prev.filter((t) => t !== tagToRemove));
    onChange(selected.filter((t) => t !== tagToRemove));
  }

  function toggleCustomTag(tag: string) {
    if (selected.includes(tag)) {
      onChange(selected.filter((t) => t !== tag));
    } else {
      onChange([...selected, tag]);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddCustom();
    } else if (e.key === "Escape") {
      e.preventDefault();
      setIsAdding(false);
      setInputError(null);
      setInputValue("");
    }
  }

  return (
    <div className={`space-y-3 ${className}`} id={componentId}>
      {label && (
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
          <label
            htmlFor={`${componentId}-add-input`}
            className="block text-xs font-bold uppercase tracking-wider text-slate-800"
          >
            {label}
          </label>
          {description && (
            <span className="text-[11px] text-slate-500 font-medium">
              {description}
            </span>
          )}
        </div>
      )}

      {/* Pill Selection Area */}
      <div className="flex flex-wrap gap-2.5 items-center">
        {/* Standard Options */}
        {standardOptions.map((opt) => {
          const active = isOptionSelected(opt.id);
          return (
            <button
              key={opt.id}
              type="button"
              onClick={() => toggleStandard(opt.id)}
              aria-pressed={active}
              className={`group inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all duration-150 text-left border ${
                active
                  ? "bg-blue-50/80 text-blue-900 border-blue-600 shadow-xs ring-1 ring-blue-600/20"
                  : "bg-white text-slate-700 border-slate-300 hover:border-slate-400 hover:bg-slate-50"
              }`}
            >
              <span
                className={`flex h-4 w-4 shrink-0 items-center justify-center rounded transition-colors ${
                  active
                    ? "bg-blue-600 text-white"
                    : "border border-slate-300 bg-white group-hover:border-slate-400"
                }`}
              >
                {active && (
                  <svg
                    className="h-3 w-3 stroke-current"
                    viewBox="0 0 12 12"
                    fill="none"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <polyline points="2.5 6 4.5 8 9.5 3" />
                  </svg>
                )}
              </span>
              <div className="flex flex-col">
                <span className="leading-snug">{opt.label}</span>
                {opt.desc && (
                  <span
                    className={`text-[10px] font-normal leading-tight ${
                      active ? "text-blue-700/80" : "text-slate-500"
                    }`}
                  >
                    {opt.desc}
                  </span>
                )}
              </div>
            </button>
          );
        })}

        {/* Custom Added Options */}
        {customOptions.map((customTag) => {
          const active = selected.includes(customTag);
          const displayLabel = customTag.replace(/^CUSTOM:\s*/i, "");
          return (
            <div
              key={customTag}
              onClick={() => toggleCustomTag(customTag)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  toggleCustomTag(customTag);
                }
              }}
              aria-pressed={active}
              className={`group inline-flex items-center gap-2 pl-3 pr-2 py-2 rounded-lg text-xs font-semibold transition-all duration-150 border cursor-pointer ${
                active
                  ? "bg-blue-50/80 text-blue-900 border-blue-600 shadow-xs ring-1 ring-blue-600/20"
                  : "bg-white text-slate-600 border-dashed border-slate-300 hover:border-slate-400 hover:bg-slate-50"
              }`}
            >
              <span
                className={`flex h-4 w-4 shrink-0 items-center justify-center rounded transition-colors ${
                  active
                    ? "bg-blue-600 text-white"
                    : "border border-slate-300 bg-white group-hover:border-slate-400"
                }`}
              >
                {active && (
                  <svg
                    className="h-3 w-3 stroke-current"
                    viewBox="0 0 12 12"
                    fill="none"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <polyline points="2.5 6 4.5 8 9.5 3" />
                  </svg>
                )}
              </span>

              <span className="leading-snug flex items-center gap-1.5">
                <span>{displayLabel}</span>
                <span className="text-[9px] uppercase tracking-wider font-mono font-bold bg-blue-100 text-blue-800 px-1.5 py-0.2 rounded">
                  Custom
                </span>
              </span>

              <button
                type="button"
                onClick={(e) => removeCustomTag(customTag, e)}
                title={`Remove custom ${categoryName} "${displayLabel}"`}
                aria-label={`Remove custom ${categoryName} ${displayLabel}`}
                className="ml-1 p-0.5 rounded text-slate-400 hover:text-red-600 hover:bg-red-50 focus:outline-none transition-colors"
              >
                <svg
                  className="w-3.5 h-3.5 stroke-current"
                  viewBox="0 0 14 14"
                  fill="none"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <line x1="3" y1="3" x2="11" y2="11" />
                  <line x1="11" y1="3" x2="3" y2="11" />
                </svg>
              </button>
            </div>
          );
        })}

        {/* Dynamic User Addition: Button or Inline Input Box */}
        {!isAdding ? (
          <button
            type="button"
            onClick={() => {
              setIsAdding(true);
              setInputError(null);
            }}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold text-blue-700 bg-blue-50/50 hover:bg-blue-100 border border-blue-200 border-dashed transition-colors"
          >
            <svg
              className="w-3.5 h-3.5 stroke-current"
              viewBox="0 0 14 14"
              fill="none"
              strokeWidth="2.2"
              strokeLinecap="round"
            >
              <line x1="7" y1="2" x2="7" y2="12" />
              <line x1="2" y1="7" x2="12" y2="7" />
            </svg>
            <span>Add Custom</span>
          </button>
        ) : (
          <div className="inline-flex items-center gap-1.5 p-1 rounded-lg border border-blue-400 bg-white shadow-xs animate-in fade-in duration-150">
            <input
              ref={inputRef}
              id={`${componentId}-add-input`}
              type="text"
              value={inputValue}
              onChange={(e) => {
                setInputValue(e.target.value);
                if (inputError) setInputError(null);
              }}
              onKeyDown={handleKeyDown}
              placeholder={customPlaceholder}
              maxLength={100}
              className="px-2.5 py-1 text-xs text-slate-900 placeholder-slate-400 outline-none w-48 sm:w-56 font-medium"
            />
            <button
              type="button"
              onClick={handleAddCustom}
              className="px-2.5 py-1 rounded bg-blue-600 hover:bg-blue-700 text-white text-[11px] font-bold shadow-2xs transition-colors"
            >
              Add
            </button>
            <button
              type="button"
              onClick={() => {
                setIsAdding(false);
                setInputError(null);
                setInputValue("");
              }}
              className="px-2 py-1 rounded text-slate-500 hover:text-slate-800 text-[11px] font-medium transition-colors"
            >
              Cancel
            </button>
          </div>
        )}
      </div>

      {inputError && (
        <p className="text-[11px] text-red-600 font-medium animate-in fade-in">
          {inputError}
        </p>
      )}
    </div>
  );
}
