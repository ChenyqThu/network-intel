/* Shared admin-editor vocabularies. Runtime arrays (TS unions can't be
   enumerated at runtime) but typed against the contract unions in types.ts,
   so a contract change breaks the build here instead of drifting silently. */
import type { Impact, Subject } from '../../types';

export const SUBJECTS: Subject[] = ['omada_self', 'competitor', 'industry'];

export const IMPACTS: Record<Subject, Impact[]> = {
  omada_self: ['needs_fix', 'feature_input', 'strength_confirm', 'unknown'],
  competitor: ['threat', 'opportunity', 'neutral', 'unknown'],
  industry: ['opportunity', 'neutral', 'unknown'],
};

export const SUBJECT_LABEL: Record<Subject, string> = {
  omada_self: 'Omada 自身',
  competitor: '竞品',
  industry: '行业',
};
