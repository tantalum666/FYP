export interface HeldVersion {
  id: string;
  version: number;
  state: string;
  title: string;
  assumption: string;
  choice: string;
  reason: string;
}

export interface HeldLine {
  id: string;
  held: boolean;
  current: HeldVersion | null;
  pending: HeldVersion | null;
  previous: HeldVersion[];
}

/** The pending wording is not what the desk is holding. */
export function heldAssumption(line: {
  current: { assumption: string } | null;
  pending: { assumption: string } | null;
}): { held: string | null; waiting: string | null } {
  return {
    held: line.current ? line.current.assumption : null,
    waiting: line.pending ? line.pending.assumption : null,
  };
}
