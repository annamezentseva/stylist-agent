import ActionBadge from "./ActionBadge";
import ItemCard from "./ItemCard";
import { SLOT_ORDER, type LookOut } from "../types";

// Результат работы агента. Три возможных вида — по одному на каждое решение:
//   look      — сетка вещей + итоговая цена
//   advice    — текст совета + источники из базы знаний
//   need_info — чего не хватило, чтобы собрать образ
export default function LookResult({ look }: { look: LookOut }) {
  const items = [...look.items].sort(
    (a, b) => SLOT_ORDER.indexOf(a.category) - SLOT_ORDER.indexOf(b.category),
  );

  return (
    <div className="result">
      <div className="result__head">
        <ActionBadge action={look.action} />
        {look.action === "look" && (
          <span className="result__total">
            Итого {look.total_price.toLocaleString("ru-RU")} ₽
          </span>
        )}
      </div>

      {look.action === "look" && (
        <div className="items">
          {items.map((item) => (
            <ItemCard key={item.id} item={item} />
          ))}
        </div>
      )}

      {look.action === "advice" && <div className="answer">{look.answer}</div>}

      {look.action === "need_info" && (
        <div className="alert alert--soft">
          <strong>{look.rationale}</strong>
          {look.missing.length > 0 && (
            <ul className="missing">
              {look.missing.map((m) => (
                <li key={m}>{m}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {look.action === "look" && look.rationale && (
        <p className="result__rationale">{look.rationale}</p>
      )}

      {look.sources.length > 0 && (
        <div className="result__sources">
          Источники: {[...new Set(look.sources)].join(", ")}
        </div>
      )}
    </div>
  );
}
