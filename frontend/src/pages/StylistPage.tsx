import { useEffect, useState } from "react";

import { api } from "../api";
import LookResult from "../components/LookResult";
import { getUserId } from "../user";
import { ACTION_LABELS, type LookOut, type LookSummary } from "../types";

// Примеры запросов — чтобы было понятно, что вообще можно спросить.
const EXAMPLES = [
  "собери образ на свидание до 12000",
  "образ в офис",
  "какие цвета идут цветотипу зима?",
  "что подойдёт фигуре груша?",
];

// Главная страница: пользователь пишет запрос, агент отвечает образом или советом.
export default function StylistPage() {
  const userId = getUserId();
  const [text, setText] = useState("");
  const [result, setResult] = useState<LookOut | null>(null);
  const [history, setHistory] = useState<LookSummary[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    void refreshHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function refreshHistory() {
    try {
      setHistory(await api.listLooks(userId));
    } catch (err) {
      setError(String(err));
    }
  }

  async function handleAsk(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    setError("");
    try {
      setResult(await api.ask(userId, text));
      setText("");
      await refreshHistory();
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  async function openLook(id: number) {
    setError("");
    try {
      setResult(await api.getLook(id));
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <div className="layout">
      {/* Левая колонка: запрос и история */}
      <section className="card">
        <h2>Что подобрать?</h2>
        <form onSubmit={handleAsk} className="form">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Например: собери образ на свидание до 12000"
            rows={3}
            required
          />
          <button className="btn btn--primary" disabled={busy}>
            {busy ? "Подбираю…" : "Спросить стилиста"}
          </button>
        </form>

        <h3 className="mt">Примеры</h3>
        <div className="chips">
          {EXAMPLES.map((ex) => (
            <button key={ex} className="chip" onClick={() => setText(ex)} type="button">
              {ex}
            </button>
          ))}
        </div>

        {history.length > 0 && (
          <>
            <h3 className="mt">История</h3>
            <ul className="list">
              {history.map((h) => (
                <li key={h.id}>
                  <button
                    className="list__item list__item--wide"
                    onClick={() => openLook(h.id)}
                  >
                    <span className="list__text">{h.request_text}</span>
                    <span className="list__tag">{ACTION_LABELS[h.action]}</span>
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      {/* Правая колонка: результат */}
      <section className="card">
        {error && <div className="alert">{error}</div>}
        {!result && !error && (
          <p className="muted">
            Напишите запрос слева — стилист соберёт образ из каталога или ответит
            советом по базе знаний.
          </p>
        )}
        {result && <LookResult look={result} />}
      </section>
    </div>
  );
}
