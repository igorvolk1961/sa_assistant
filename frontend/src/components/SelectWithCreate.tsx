import { useState } from "react";
import type { ReactNode } from "react";

/**
 * A generic <select> over a NON-reference table's options, with a separate
 * «+ Создать …» button next to it. Clicking the button opens a modal; the modal
 * body is rendered by `renderCreateForm`, which owns the actual create form and
 * must POST to the corresponding create endpointainthen call `onCreated(item)`.
 *
 * `onCreated` closes the modal, reloads the options via a caller-provided
 * `reload` callbackainthen auto-selects the newly created itemaid sets
 * `value` to it.
 *
 * This is the reusable piece that gives any <select> over a non-reference table
 * the ability to create a new row on the fly — used for stakeholders,
 * employees/assignees, etc.
 */
export interface SelectWithCreateCreateContext<T extends { id: string }> {
  onCreated: (item: T) => void;
  onClose: () => void;
}

export interface SelectWithCreateProps<T extends { id: string }> {
  options: T[];
  value: string;
  onChange: (id: string) => void;
  getLabel: (item: T) => string;
  /** Reloads the full option list (e.g. re-fetch stakeholders). Called after create. */
  reload: () => Promise<void>;
  /** Text on the «+ Создать» button, e.g. «Создать стейкхолдера». */
  createLabel: string;
  /** Renders the create form inside the modal (fields + submit). Returns the created item. */
  renderCreateForm: (ctx: SelectWithCreateCreateContext<T>) => ReactNode;
  placeholder?: string;
}

export function SelectWithCreate<T extends { id: string }>({
  options,
  value,
  onChange,
  getLabel,
  reload,
  createLabel,
  renderCreateForm,
  placeholder = "— выберите —",
}: SelectWithCreateProps<T>) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <div className="select-with-create">
        <select value={value} onChange={(e) => onChange(e.target.value)} required>
          <option value="">{placeholder}</option>
          {options.map((opt) => (
            <option key={opt.id} value={opt.id}>
              {getLabel(opt)}
            </option>
          ))}
        </select>
        <button type="button" className="create" onClick={() => setOpen(true)}>
          {createLabel}
        </button>
      </div>

      {open && (
        <div className="modal-overlay" onClick={() => setOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h4>Новый стейкхолдер</h4>
              <button type="button" className="modal-close" onClick={() => setOpen(false)}>
                ×
              </button>
            </div>
            {renderCreateForm({
              onCreated: (item) => {
                setOpen(false);
                void reload().then(() => {
                  onChange(item.id);
                });
              },
              onClose: () => setOpen(false),
            })}
          </div>
        </div>
      )}
    </>
  );
}
