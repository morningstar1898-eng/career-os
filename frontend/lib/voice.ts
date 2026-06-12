"use client";

export function speak(text: string, onEnd?: () => void) {
  if (typeof window === "undefined") return;
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1.0;
  utterance.pitch = 0.9;
  utterance.lang = "en-US";
  if (onEnd) utterance.onend = onEnd;
  speechSynthesis.speak(utterance);
}

export function stopSpeaking() {
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
