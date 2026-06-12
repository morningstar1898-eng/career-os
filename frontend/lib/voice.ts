"use client";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
let currentAudio: HTMLAudioElement | null = null;

export async function speak(text: string, onEnd?: () => void) {
  if (typeof window === "undefined") return;
  stopSpeaking();

  try {
    const res = await fetch(`${API_BASE}/tts/speak`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });

    if (!res.ok) throw new Error("TTS failed");

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    currentAudio = new Audio(url);
    currentAudio.onended = () => {
      URL.revokeObjectURL(url);
      currentAudio = null;
      onEnd?.();
    };
    currentAudio.play();
  } catch {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 0.9;
    utterance.lang = "en-US";
    if (onEnd) utterance.onend = onEnd;
    speechSynthesis.speak(utterance);
  }
}

export function stopSpeaking() {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }
  speechSynthesis.cancel();
}

export function createRecognition(
  onResult: (text: string) => void,
  onEnd?: () => void
): any | null {
  if (typeof window === "undefined") return null;
  const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
  if (!SpeechRecognition) return null;

  const recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = "en-US";

  recognition.onresult = (event: SpeechRecognitionEvent) => {
    const text = event.results[0][0].transcript;
    onResult(text);
  };
  if (onEnd) recognition.onend = onEnd;
  return recognition;
}
