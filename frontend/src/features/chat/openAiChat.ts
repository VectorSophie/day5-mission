import { Message } from "../messages/messages";
import { getApiBase } from "@/utils/apiBase";

export type BackendViseme = {
  phoneme: "a" | "i" | "u" | "e" | "o";
  start: number;
  end: number;
};

export type BackendChatResponse = {
  message: string;
  text: string;
  emotion: "neutral" | "happy" | "sad" | "angry";
  audio_url: string | null;
  visemes: BackendViseme[];
  tool_used?: string | null;
};

export async function getBackendChatResponse(messages: Message[]): Promise<BackendChatResponse> {
  const apiBase = getApiBase();
  const userMessages = messages.filter((msg) => msg.role === "user");
  const lastUserMessage = userMessages[userMessages.length - 1];

  if (!lastUserMessage) {
    throw new Error("No user message found");
  }

  const response = await fetch(`${apiBase}/api/v1/chat/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message: lastUserMessage.content,
      session_id: "chatvrm-web",
      user_id: "web-user",
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Backend chat failed: ${response.status} ${text}`);
  }

  return (await response.json()) as BackendChatResponse;
}

export async function getAudioArrayBuffer(audioUrl: string): Promise<ArrayBuffer> {
  const apiBase = getApiBase();
  const resolved = audioUrl.startsWith("http") ? audioUrl : `${apiBase}${audioUrl}`;
  const response = await fetch(resolved);
  if (!response.ok) {
    throw new Error(`Audio fetch failed: ${response.status}`);
  }
  return await response.arrayBuffer();
}
