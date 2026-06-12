"use client";

import { useState, useEffect } from "react";
import { fetchAPI } from "../../lib/api";
import { speak, createRecognition, stopSpeaking } from "../../lib/voice";
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
  const [history, setHistory] = useState<Session[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => {
    fetchAPI<Session[]>("/interview/history?limit=10").then(setHistory).catch(() => {});
  }, [session]);

  async function startQuestion(category: string) {
    setLoading(true);
    setAnswer("");
    try {
      const s = await fetchAPI<Session>("/interview/start", {
        method: "POST",
        body: JSON.stringify({ category }),
      });
      setSession(s);
      if (voiceEnabled) speak(s.question);
    } catch {
      alert("Start the backend API to use interview practice.");
    }
    setLoading(false);
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

  function nextQuestion() {
    stopSpeaking();
    setSession(null);
    setAnswer("");
  }

  const avgScore = history.filter((h) => h.score).length > 0
    ? (history.filter((h) => h.score).reduce((sum, h) => sum + (h.score || 0), 0) / history.filter((h) => h.score).length).toFixed(1)
    : null;

  return (
    <main className="min-h-screen p-6 max-w-4xl mx-auto pb-24">
      <nav className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold">Interview <span className="text-accent">Practice</span></h1>
        <div className="flex gap-3 text-sm items-center">
          <Link href="/dashboard" className="text-zinc-400 hover:text-white">Dashboard</Link>
          <button onClick={() => setShowHistory(!showHistory)} className="text-zinc-400 hover:text-white">
            {showHistory ? "Hide History" : "History"}
          </button>
          <button onClick={() => setVoiceEnabled(!voiceEnabled)} className={`px-3 py-1 rounded ${voiceEnabled ? "bg-accent" : "bg-zinc-700"} text-xs`}>
            {voiceEnabled ? "Voice On" : "Voice Off"}
          </button>
        </div>
      </nav>

      {avgScore && (
        <div className="glass-card p-4 mb-6 flex items-center justify-between">
          <span className="text-sm text-zinc-400">Your average score</span>
          <span className="text-xl font-bold text-accent">{avgScore}/10</span>
        </div>
      )}

      <div className="flex flex-wrap gap-2 mb-8">
        {CATEGORIES.map((cat) => (
          <button key={cat} onClick={() => startQuestion(cat)} disabled={loading}
            className="px-4 py-2 glass-card text-sm hover:border-accent/50 transition capitalize disabled:opacity-50">
            {cat.replace(/_/g, " ")}
          </button>
        ))}
      </div>

      {loading && !session && (
        <div className="text-center text-zinc-500 mt-20">
          <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin mb-3" />
          <p>Generating question...</p>
        </div>
      )}

      {session && (
        <div className="space-y-6">
          <div className="glass-card p-6">
            <div className="text-xs text-accent uppercase mb-2">{session.category.replace(/_/g, " ")}</div>
            <p className="text-lg">{session.question}</p>
          </div>

          {!session.ai_feedback && (
            <div className="glass-card p-6">
              <textarea
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="Type your answer or click the mic..."
                className="w-full bg-transparent border border-card-border rounded-lg p-3 text-sm min-h-[120px] focus:outline-none focus:border-accent resize-y"
              />
              <div className="flex gap-3 mt-3">
                <button onClick={submitAnswer} disabled={loading || !answer.trim()}
                  className="px-4 py-2 bg-accent rounded-lg text-sm font-medium disabled:opacity-50">
                  {loading ? "Scoring..." : "Submit Answer"}
                </button>
                <button onClick={startListening} disabled={listening}
                  className={`px-4 py-2 rounded-lg text-sm border ${listening ? "border-danger text-danger animate-pulse" : "border-card-border hover:border-accent/50"}`}>
                  {listening ? "Listening..." : "Use Mic"}
                </button>
              </div>
            </div>
          )}

          {session.ai_feedback && (() => {
            let fb: any;
            try {
              const parsed = JSON.parse(session.ai_feedback);
              fb = typeof parsed === "string" ? JSON.parse(parsed) : parsed;
            } catch {
              fb = { how_to_improve: session.ai_feedback };
            }
            const s = session.score || 0;
            const scoreColor = s >= 7 ? "text-success" : s >= 5 ? "text-warning" : "text-danger";
            const barColor = s >= 7 ? "bg-success" : s >= 5 ? "bg-warning" : "bg-danger";
            const scoreLabel = s >= 8 ? "Strong" : s >= 6 ? "Good" : s >= 4 ? "Getting There" : "Needs Work";
            return (
              <>
                <div className="glass-card p-6">
                  <div className="flex items-center gap-4">
                    <div className="text-center">
                      <div className={`text-4xl font-bold ${scoreColor}`}>{s}</div>
                      <div className={`text-xs font-medium mt-1 ${scoreColor}`}>{scoreLabel}</div>
                    </div>
                    <div className="flex-1">
                      <div className="h-3 bg-zinc-800 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full transition-all duration-500 ${barColor}`}
                          style={{ width: `${s * 10}%` }} />
                      </div>
                    </div>
                  </div>
                </div>

                {fb.whats_good && (
                  <div className="glass-card p-5 border-l-4 border-l-success">
                    <h3 className="text-xs uppercase text-success font-semibold tracking-wider mb-2">What You Did Well</h3>
                    <p className="text-sm text-zinc-300 leading-relaxed">{fb.whats_good}</p>
                  </div>
                )}

                {fb.how_to_improve && (
                  <div className="glass-card p-5 border-l-4 border-l-warning">
                    <h3 className="text-xs uppercase text-warning font-semibold tracking-wider mb-2">How to Improve</h3>
                    <p className="text-sm text-zinc-300 leading-relaxed">{fb.how_to_improve}</p>
                  </div>
                )}

                {fb.model_answer && (
                  <details className="glass-card overflow-hidden">
                    <summary className="p-5 cursor-pointer hover:bg-zinc-800/30 transition flex items-center justify-between">
                      <h3 className="text-xs uppercase text-accent font-semibold tracking-wider">Model Answer</h3>
                      <span className="text-xs text-zinc-500">Click to reveal</span>
                    </summary>
                    <div className="px-5 pb-5 border-t border-card-border">
                      <div className="mt-4 pl-4 border-l-2 border-accent/40">
                        <p className="text-sm text-zinc-300 leading-relaxed italic whitespace-pre-wrap">{fb.model_answer}</p>
                      </div>
                    </div>
                  </details>
                )}

                {fb.key_takeaway && (
                  <div className="p-4 rounded-xl bg-accent/10 border border-accent/30 flex items-start gap-3">
                    <span className="text-accent text-lg mt-0.5">*</span>
                    <div>
                      <h3 className="text-xs uppercase text-accent font-semibold tracking-wider mb-1">Remember This</h3>
                      <p className="text-sm text-zinc-200 font-medium leading-relaxed">{fb.key_takeaway}</p>
                    </div>
                  </div>
                )}

                <button onClick={nextQuestion} className="px-4 py-2 bg-accent rounded-lg text-sm font-medium glow">
                  Next Question
                </button>
              </>
            );
          })()}
        </div>
      )}

      {!session && !loading && (
        <div className="text-center text-zinc-500 mt-20">
          <p className="text-lg">Choose a category above to start practicing</p>
          <p className="text-sm mt-2">AI generates a question, you answer by voice or text, and get scored with feedback</p>
        </div>
      )}

      {showHistory && history.length > 0 && (
        <div className="mt-8">
          <h2 className="text-lg font-semibold mb-4">Recent Sessions</h2>
          <div className="space-y-2">
            {history.map((h) => (
              <div key={h.id} className="glass-card p-4 flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <span className="text-xs text-accent uppercase">{h.category.replace(/_/g, " ")}</span>
                  <p className="text-sm text-zinc-300 truncate">{h.question}</p>
                </div>
                {h.score !== null && h.score !== undefined && (
                  <span className={`text-lg font-bold ml-4 ${h.score >= 7 ? "text-success" : h.score >= 5 ? "text-warning" : "text-danger"}`}>
                    {h.score}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </main>
  );
}
