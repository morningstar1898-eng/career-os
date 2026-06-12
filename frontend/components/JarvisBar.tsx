"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { createRecognition, speak } from "../lib/voice";
import { fetchAPI } from "../lib/api";

export function JarvisBar() {
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [response, setResponse] = useState("");
  const router = useRouter();

  function handleVoiceCommand(text: string) {
    const lower = text.toLowerCase();
    setTranscript(text);

    if (lower.includes("briefing") || lower.includes("today")) {
      router.push("/dashboard");
      speak("Opening your daily briefing.");
      return;
    }
    if (lower.includes("interview") || lower.includes("practice")) {
      router.push("/interview");
      speak("Let's practice some interview questions.");
      return;
    }
    if (lower.includes("agents") || lower.includes("monitor") || lower.includes("status")) {
      router.push("/agents");
      speak("Showing agent monitor.");
      return;
    }
    if (lower.includes("home") || lower.includes("landing")) {
      router.push("/");
      speak("Going home.");
      return;
    }
    if (lower.includes("how many jobs") || lower.includes("jobs applied")) {
      fetchAPI<any>("/analytics/summary")
        .then((s) => {
          const msg = `You've applied to ${s.total_jobs_applied} jobs over ${s.days_active} active days. Your average interview score is ${s.avg_interview_score} out of 10.`;
          setResponse(msg);
          speak(msg);
        })
        .catch(() => speak("I can't reach the API right now."));
      return;
    }
    if (lower.includes("score") || lower.includes("interview score")) {
      fetchAPI<any>("/analytics/summary")
        .then((s) => {
          const msg = `Your average interview score is ${s.avg_interview_score} out of 10.`;
          setResponse(msg);
          speak(msg);
        })
        .catch(() => speak("I can't reach the API right now."));
      return;
    }

    speak("I can help with: briefing, interview practice, agent status, or job stats. Try again.");
  }

  function startListening() {
    const recognition = createRecognition(
      (text) => { handleVoiceCommand(text); setListening(false); },
      () => setListening(false)
    );
    if (recognition) {
      setListening(true);
      setTranscript("");
      setResponse("");
      recognition.start();
    } else {
      speak("Voice recognition is not supported in this browser. Try Chrome or Edge.");
    }
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-2">
      {(transcript || response) && (
        <div className="glass-card p-3 max-w-xs text-xs">
          {transcript && <p className="text-zinc-400">You: {transcript}</p>}
          {response && <p className="text-accent mt-1">{response}</p>}
        </div>
      )}
      <button
        onClick={startListening}
        className={`w-14 h-14 rounded-full flex items-center justify-center transition-all ${
          listening
            ? "bg-danger animate-pulse scale-110"
            : "bg-accent hover:scale-105 glow"
        }`}
        title="Talk to Jarvis"
      >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
          <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
          <line x1="12" y1="19" x2="12" y2="23" />
          <line x1="8" y1="23" x2="16" y2="23" />
        </svg>
      </button>
    </div>
  );
}
