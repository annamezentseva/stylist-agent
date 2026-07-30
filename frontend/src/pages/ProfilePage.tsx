import { useEffect, useState } from "react";

import { api } from "../api";
import { getUserId } from "../user";
import type { Profile } from "../types";

const COLOR_TYPES = ["", "весна", "лето", "осень", "зима"];
const UNDERTONES = ["", "тёплый", "холодный", "нейтральный"];
const CONTRASTS = ["", "низкий", "средний", "высокий"];

// Страница профиля: то, что агент знает о пользователе. Эти данные влияют на
// подбор — цветотип задаёт палитру, вкус и ограничения фильтруют каталог.
// Поля можно заполнить руками; иначе их заполнит анализ фото.
export default function ProfilePage() {
  const userId = getUserId();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  // Поля формы держим строками — так проще редактировать списки через запятую.
  const [colorType, setColorType] = useState("");
  const [undertone, setUndertone] = useState("");
  const [contrast, setContrast] = useState("");
  const [bodyShape, setBodyShape] = useState("");
  const [styles, setStyles] = useState("");
  const [palette, setPalette] = useState("");
  const [dislikes, setDislikes] = useState("");
  const [budget, setBudget] = useState("");
  const [sizeTop, setSizeTop] = useState("");
  const [sizeBottom, setSizeBottom] = useState("");
  const [sizeShoes, setSizeShoes] = useState("");

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function load() {
    try {
      const p = await api.getProfile(userId);
      setProfile(p);
      setColorType(p.appearance?.color_type ?? "");
      setUndertone(p.appearance?.undertone ?? "");
      setContrast(p.appearance?.contrast ?? "");
      setBodyShape(p.appearance?.body_shape ?? "");
      setStyles((p.style_profile?.styles ?? []).join(", "));
      setPalette((p.style_profile?.palette ?? []).join(", "));
      setDislikes((p.style_profile?.dislikes ?? []).join(", "));
      setBudget(p.constraints?.budget_rub ? String(p.constraints.budget_rub) : "");
      const sizes = p.constraints?.sizes ?? {};
      setSizeTop(sizes["верх"] ?? "");
      setSizeBottom(sizes["низ"] ?? "");
      setSizeShoes(sizes["обувь"] ?? "");
    } catch (err) {
      setError(String(err));
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setSaved(false);

    // Размеры собираем только из заполненных полей — пустые не ограничивают подбор.
    const sizes: Record<string, string> = {};
    if (sizeTop) sizes["верх"] = sizeTop;
    if (sizeBottom) sizes["низ"] = sizeBottom;
    if (sizeShoes) sizes["обувь"] = sizeShoes;

    try {
      const updated = await api.saveProfile(userId, {
        appearance: {
          color_type: colorType || null,
          undertone: undertone || null,
          contrast: contrast || null,
          body_shape: bodyShape || null,
          face_shape: null,
        },
        style_profile: {
          styles: splitList(styles),
          palette: splitList(palette),
          silhouettes: profile?.style_profile?.silhouettes ?? [],
          likes: profile?.style_profile?.likes ?? [],
          dislikes: splitList(dislikes),
        },
        constraints: {
          occasion: null,
          budget_rub: budget ? Number(budget) : null,
          season: null,
          sizes,
          avoid: [],
        },
      });
      setProfile(updated);
      setSaved(true);
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="layout">
      <section className="card">
        <h2>Профиль</h2>
        <p className="muted">
          Эти данные агент использует при подборе: цветотип задаёт палитру,
          размеры и бюджет отсекают неподходящие вещи.
        </p>

        <form onSubmit={handleSave} className="form mt">
          <h3>Внешность</h3>
          <label className="field">
            <span>Цветотип</span>
            <select value={colorType} onChange={(e) => setColorType(e.target.value)}>
              {COLOR_TYPES.map((c) => (
                <option key={c} value={c}>
                  {c || "— не задан —"}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Подтон кожи</span>
            <select value={undertone} onChange={(e) => setUndertone(e.target.value)}>
              {UNDERTONES.map((c) => (
                <option key={c} value={c}>
                  {c || "— не задан —"}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Контраст внешности</span>
            <select value={contrast} onChange={(e) => setContrast(e.target.value)}>
              {CONTRASTS.map((c) => (
                <option key={c} value={c}>
                  {c || "— не задан —"}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Тип фигуры</span>
            <input
              value={bodyShape}
              onChange={(e) => setBodyShape(e.target.value)}
              placeholder="песочные часы, груша, прямоугольник…"
            />
          </label>

          <h3 className="mt">Вкус</h3>
          <label className="field">
            <span>Стили (через запятую)</span>
            <input
              value={styles}
              onChange={(e) => setStyles(e.target.value)}
              placeholder="минимализм, smart-casual"
            />
          </label>
          <label className="field">
            <span>Любимые цвета</span>
            <input
              value={palette}
              onChange={(e) => setPalette(e.target.value)}
              placeholder="чёрный, серый, белый"
            />
          </label>
          <label className="field">
            <span>Не нравится</span>
            <input
              value={dislikes}
              onChange={(e) => setDislikes(e.target.value)}
              placeholder="принты, рюши"
            />
          </label>

          <h3 className="mt">Ограничения</h3>
          <label className="field">
            <span>Обычный бюджет на образ, ₽</span>
            <input
              type="number"
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              placeholder="15000"
              min={0}
            />
          </label>
          <div className="row">
            <label className="field">
              <span>Размер верха</span>
              <input value={sizeTop} onChange={(e) => setSizeTop(e.target.value)} placeholder="M" />
            </label>
            <label className="field">
              <span>Размер низа</span>
              <input
                value={sizeBottom}
                onChange={(e) => setSizeBottom(e.target.value)}
                placeholder="46"
              />
            </label>
            <label className="field">
              <span>Обувь</span>
              <input
                value={sizeShoes}
                onChange={(e) => setSizeShoes(e.target.value)}
                placeholder="41"
              />
            </label>
          </div>

          <button className="btn btn--primary" disabled={busy}>
            {busy ? "Сохраняю…" : "Сохранить профиль"}
          </button>
        </form>
      </section>

      <section className="card">
        {error && <div className="alert">{error}</div>}
        {saved && <div className="alert alert--ok">Профиль сохранён.</div>}
        <h2>Как это влияет на подбор</h2>
        <ul className="hints">
          <li>
            <strong>Цветотип</strong> — вещи «своих» цветов получают более высокий
            балл, конфликтующие по подтону штрафуются.
          </li>
          <li>
            <strong>Любимые цвета</strong> весят больше цветотипа: устойчивый вкус
            важнее общего правила.
          </li>
          <li>
            <strong>Стили</strong> сопоставляются с тегами вещей в каталоге.
          </li>
          <li>
            <strong>Размеры</strong> и <strong>бюджет</strong> — жёсткий фильтр:
            то, что не подходит, в образ не попадёт.
          </li>
        </ul>
        <p className="muted mt">
          Ваш идентификатор: <code>{userId}</code>
        </p>
      </section>
    </div>
  );
}

function splitList(value: string): string[] {
  return value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}
