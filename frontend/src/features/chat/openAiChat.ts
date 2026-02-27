import { Message } from "../messages/messages";

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

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

export async function getBackendChatResponse(messages: Message[]): Promise<BackendChatResponse> {
  const userMessages = messages.filter((msg) => msg.role === "user");
  const lastUserMessage = userMessages[userMessages.length - 1];

  if (!lastUserMessage) {
    throw new Error("No user message found");
  }

  const response = await fetch(`${API_BASE}/api/v1/chat/`, {
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
  const resolved = audioUrl.startsWith("http") ? audioUrl : `${API_BASE}${audioUrl}`;
  const response = await fetch(resolved);
  if (!response.ok) {
    throw new Error(`Audio fetch failed: ${response.status}`);
  }
  return await response.arrayBuffer();
}
