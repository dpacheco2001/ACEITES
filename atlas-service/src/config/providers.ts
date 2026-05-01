import { createGoogleGenerativeAI } from '@ai-sdk/google';
import { env, requireGoogleKey } from './env.js';

export function atlasModel() {
  requireGoogleKey();
  const google = createGoogleGenerativeAI({ apiKey: env.googleApiKey });
  return google(env.model);
}

export const googleProviderOptions = {
  google: {
    thinkingConfig: {
      thinkingLevel: 'medium',
    },
  },
};
