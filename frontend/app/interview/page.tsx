"use client";

import { useState } from "react";
import { fetchAPI } from "../../lib/api";
import { speak, createRecognition } from "../../lib/voice";
import Link from "next/link";

const CATEGORIES = ["behavioral", "technical", "domain", "case_study", "questions_to_ask"];

interface Session {
  id: number;
  category: string;
  question: string;
  user_answer?: string;
  ai_feedback?: string;
  score?: number;
}

export default function InterviewPage() {
  const [session, setSession] = useState<Session | null>(null);
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true);

  async function startQuestion(category: string) {
    setLoading(true);
    setAnswer("");
    const s = await fetchAPI<Session>("/interview/start", {
      method: "POST",
      body: JSON.stringify({ category }),
    });
    setSession(s);
    setLoading(false);
    if (voiceEnabled) speak(s.question);
  }

  async function submitAnswer() {
    if (!session || !answer.trim()) return;
    setLoading(true);
    const s = await fetchAPI<Session>("/interview/answer", {
      method: "POST",
      body: JSON.stringify({ session_id: session.id, user_answer: answer }),
    });
    setSession(s);
    setLoading(false);
    if (voiceEnabled && s.ai_feedback) speak(s.ai_feedback);
  }

  function startListening() {
    const recognition = createRecognition((text) => {
      setAnswer(text);
      setListening(false);
    }, () => setListening(false));
    if (recognition) {
      setListening(true);
      recognition.start();
    }
  }

  return (
    <main className="min-h-screen p-6 max-w-4xl mx-auto">
      <nav className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold">Interview <span className="text-[var(--color-accent)]">Practice</span></h1>
        <div className="flex gap-4 text-sm">
          <Link href="/dashboard" className="text-zinc-400 hover:text-white">Dashboard</Link>
          <button onClick={() => setVoiceEnabled(!voiceEnabled)} className={`px-3 py-1 rounded ${voiceEnabled ? "bg-[var(--color-accent)]" : "bg-zinc-700"} text-xs`}>
            {voiceEnabled ? "Voice On" : "Voice Off"}
          </button>
        </div>
      </nav>

      <div className="flex flex-wrap gap-2 mb-8">
        {CATEGORIES.map((cat) => (
          <button key={cat} onClick={() => startQuestion(cat)} disabled={loading}
            className="px-4 py-2 glass-card text-sm hover:border-[var(--color-accent)] transition capitalize disabled:opacity-50">
            {cat.replace("_", " ")}
          </button>
        ))}
      </div>

      {session && (
        <div className="space-y-6">
          <div className="glass-card p-6">
            <div className="text-xs text-[var(--color-accent)] uppercase mb-2">{session.category.replace("_", " ")}</div>
            <p className="text-lg">{session.question}</p>
          </div>

          {!session.ai_feedback && (
            <div className="glass-card p-6">
              <textarea
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="Type your answer or click the mic..."
                className="w-full bg-transparent border border-[var(--color-card-border)] rounded-lg p-3 text-sm min-h-[120px] focus:outline-none focus:border-[var(--color-accent)]"
              />
              <div className="flex gap-3 mt-3">
                <button onClick={submitAnswer} disabled={loading || !answer.trim()}
                  className="px-4 py-2 bg-[var(--color-accent)] rounded-lg text-sm font-medium disabled:opacity-50">
                  {loading ? "Scoring..." : "Submit Answer"}
                </button>
                <button onClick={startListening} disabled={listening}
                  className={`px-4 py-2 rounded-lg text-sm border ${listening ? "border-[var(--color-danger)] text-[var(--color-danger)]" : "border-[var(--color-card-border)]"}`}>
                  {listening ? "Listening..." : "Use Mic"}
                </button>
              </div>
            </div>
          )}

          {session.ai_feedback && (
            <div className="glass-card p-6">
              <div className="flex items-center gap-3 mb-3">
                <span className="text-3xl font-bold text-[var(--color-accent)]">{session.score}/10</span>
                <span className="text-sm text-zinc-400">Score</span>
              </div>
              <p className="text-sm text-zinc-300">{session.ai_feedback}</p>
            </div>
          )}
        </div>
      )}

      {!session && !loading && (
        <div className="text-center text-zinc-500 mt-20">
          <p className="text-lg">Choose a category above to start practicing</p>
          <p className="text-sm mt-2">AI will generate a question, you answer by voice or text, and get scored with feedback</p>
        </div>
      )}
    </main>
  );
}
