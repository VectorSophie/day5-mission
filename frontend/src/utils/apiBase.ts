export function getApiBase(): string {
  if (typeof window !== "undefined") {
    const protocol = window.location.protocol === "https:" ? "https:" : "http:";
    return `${protocol}//${window.location.hostname}:8000`;
  }

  return process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";
}
