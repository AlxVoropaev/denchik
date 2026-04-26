import { useEffect, useRef, useState } from "react";
import { useCreateTask } from "../hooks/useTasks";

interface Props {
  epicId: number;
  defaultStatus?: "todo" | "in_progress" | "done";
}

export function QuickAddTask({ epicId, defaultStatus }: Props) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const { mutate, isPending } = useCreateTask();

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  function submit() {
    const t = title.trim();
    if (!t) {
      setOpen(false);
      return;
    }
    mutate(
      { epic_id: epicId, title: t, status: defaultStatus },
      {
        onSuccess: () => {
          setTitle("");
          inputRef.current?.focus();
        },
      },
    );
  }

  if (!open) {
    return (
      <button
        className="quick-add"
        onClick={() => setOpen(true)}
        aria-label="Add task"
      >
        + Add a task
      </button>
    );
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <input
        ref={inputRef}
        className="quick-add-input"
        placeholder="Task title — Enter to save, Esc to cancel"
        value={title}
        disabled={isPending}
        onChange={(e) => setTitle(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            setTitle("");
            setOpen(false);
          }
        }}
        onBlur={() => {
          if (!title.trim()) setOpen(false);
        }}
      />
      {/*
        Hidden submit button: ensures form-level submit fires on Enter,
        including when an IME is composing and React's synthetic keydown
        does not see key === "Enter".
      */}
      <button type="submit" hidden aria-hidden="true" tabIndex={-1}>
        Add
      </button>
    </form>
  );
}
