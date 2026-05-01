import type { ModelMessage, UIMessage } from 'ai';
import { convertToModelMessages } from 'ai';

export function compactMessages(messages: UIMessage[]): ModelMessage[] {
  const modelMessages = convertToModelMessages(messages);
  if (modelMessages.length <= 14) return modelMessages;

  const older = modelMessages.slice(0, -10);
  const recent = modelMessages.slice(-10);
  const summary = older
    .map((message) => `${message.role}: ${JSON.stringify(message.content).slice(0, 500)}`)
    .join('\n')
    .slice(-3000);

  return [
    {
      role: 'system',
      content: `Resumen compacto de turnos anteriores:\n${summary}`,
    },
    ...recent,
  ];
}
