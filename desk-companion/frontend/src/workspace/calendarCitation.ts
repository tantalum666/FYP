import { DateTime } from "luxon";
import { request } from "../api";
import type { Snapshot } from "../types";
import { findingSource } from "./findingNavigation";

export async function citedCalendarOccurrence(ref: string, zone: string) {
  if (!findingSource({kind:"calendar",ref})) return null;
  const value=ref.slice("calendar:".length);
  const cut=value.indexOf(":");
  const id=value.slice(0,cut), key=value.slice(cut+1);
  const hint=DateTime.fromISO(key.slice(0,10),{zone}).startOf("day");
  if(!hint.isValid) return null;
  // The series key uses the original event's zone; the desk can be a day ahead or behind.
  const start=hint.minus({days:1}).toUTC().toISO()!, end=hint.plus({days:2}).toUTC().toISO()!;
  const snap=await request<Snapshot>(`/calendar?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`);
  const event=snap.occurrences.find(row=>row.id===id && row.occurrence_key===key);
  if(!event || event.redacted) return null;
  const day=DateTime.fromISO(event.start,{zone}).toISODate();
  return day ? {event,day} : null;
}
