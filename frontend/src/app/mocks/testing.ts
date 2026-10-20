import { MockScript, ServerMessage } from '../contracts/contracts';

/** The server messages of a scripted run, without delays or await steps. */
export const sendsOf = (script: MockScript): ServerMessage[] =>
  script.steps.flatMap((step) => ('send' in step ? [step.send] : []));
